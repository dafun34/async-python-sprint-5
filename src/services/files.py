import datetime
import os
import urllib.parse
import uuid
from typing import Union

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.s3 import S3Client
from src.core.config import get_settings
from src.core.log import get_logger
from src.data_classes.files import FileItem
from src.models.file import File

settings = get_settings()
logger = get_logger()


class S3UploadFileExceptiom(Exception):
    pass


class FilesService:
    s3_client = S3Client(
        logger=logger,
        endpoint=f"{settings.s3_protocol}://{settings.s3_host}:{settings.s3_port}",
        access_key=settings.s3_access_key_id,
        secret_key=settings.s3_secret_access_key,
    )
    s3_bucket_name = settings.s3_bucket_name

    @staticmethod
    def is_uuid(input_string):
        try:
            uuid.UUID(input_string)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_file_path(input_string):
        _, file_extension = os.path.splitext(input_string)
        return bool(file_extension)

    @staticmethod
    def prepare_path_by_user(path: str, email: str) -> str:
        """
        Подготовить url по пользователю.

        Добавляя префикс с уникальным идентификатором к пути,
        получаем папку в хранилище для каждого пользователя.
        """
        return f"{email}/{path}"

    @classmethod
    async def get_files(cls, session: AsyncSession):
        """Получить все файлы хранилища."""
        query = select(File)
        result = await session.execute(query)
        return result.scalars().all()

    @classmethod
    async def insert_file_info(
        cls,
        session: AsyncSession,
        path: str,
        account_id: str,
        name: str,
        s3_data: dict,
    ) -> File:
        """Добавить информацию о загруженном файле в БД."""
        file_object = File(
            path=path,
            account_id=account_id,
            name=name,
            size=s3_data["ContentLength"],
        )
        session.add(file_object)
        await session.commit()
        return file_object

    @classmethod
    async def get_file_by_path(
        cls, session: AsyncSession, path: str
    ) -> Union[File, None]:
        """Получить из БД объект файла по пути."""
        query = select(File).where(File.path == path)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def get_file_by_id(
        cls, session: AsyncSession, id: str
    ) -> Union[File, None]:
        """Получить из БД объект файла по идентификатору."""
        query = select(File).where(File.id == id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def update_file_info(
        cls, session: AsyncSession, path: str, s3_data: dict
    ) -> File:
        """Обновить информацию о файле."""
        query = (
            update(File)
            .where(File.path == path)
            .values(
                size=s3_data["ContentLength"],
                created_ad=datetime.datetime.utcnow(),
            )
        )
        await session.execute(query)
        await session.commit()

        return await cls.get_file_by_path(session=session, path=path)

    @classmethod
    def check_download_permissions(cls, file_object, user):
        """
        Установить параметр is_downloadable в соответствии с правами.

        Не знал, что делать с этим полем и решил сделать так:
        Только автор загрузки имеет право скачать файл.
        """
        file_item = FileItem.model_validate(file_object.__dict__)
        file_item.is_downloadable = bool(user.email == file_object.account_id)
        return file_item

    @classmethod
    async def upload_file(
        cls, path: str, data, email: str, session: AsyncSession, filename
    ):
        """Загрузить файл в хранилище.

        Если файла не существует, то записываем файл в хранилище
        и записываем данные о нем в БД.
        Если файл существует, то файл в хранилище перезаписывается
        и данные о нем обновляются в БД.
        """
        try:
            path = cls.prepare_path_by_user(path, email)
            is_object_exists, response_data = (
                await cls.s3_client.object_exists(cls.s3_bucket_name, path)
            )
            if not is_object_exists:
                await cls.s3_client.put_object(cls.s3_bucket_name, path, data)
                is_object_exists, response_data = (
                    await cls.s3_client.object_exists(cls.s3_bucket_name, path)
                )
                file_object = await cls.insert_file_info(
                    session=session,
                    path=path,
                    account_id=email,
                    name=filename,
                    s3_data=response_data,
                )
            else:
                await cls.s3_client.put_object(cls.s3_bucket_name, path, data)
                is_object_exists, response_data = (
                    await cls.s3_client.object_exists(cls.s3_bucket_name, path)
                )
                file_object = await cls.update_file_info(
                    session=session, path=path, s3_data=response_data
                )
            return file_object

        except Exception as err:
            logger.error("Не удалось загрузить файл в хранилище")
            raise S3UploadFileExceptiom(err)

    @classmethod
    async def get_download_link(cls, path: str) -> str:
        """Получить ссылку для скачивания поменяв в ней хост наружу."""

        download_link = await cls.s3_client.get_download_url(
            cls.s3_bucket_name, path
        )

        parsed_link = urllib.parse.urlparse(download_link)
        new_parsed_url = parsed_link._replace(
            netloc=f"{settings.host}:{settings.s3_port}"
        )
        return urllib.parse.urlunparse(new_parsed_url)
