from aiobotocore.session import AioSession
from botocore.exceptions import ClientError

from src.core.config import get_settings
from src.core.log import LoggerDependency

settings = get_settings()


class S3Client:
    def __init__(
        self,
        logger: LoggerDependency,
        endpoint: str,
        access_key: str = None,
        secret_key: str = None,
        session_token: str = None,
        secure: bool = True,
        region: str = None,
    ):

        self.logger = logger
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.session_token = session_token
        self.secure = secure
        self.region = region
        self.session = AioSession()

        self.client_config = {
            "aws_access_key_id": self.access_key,
            "aws_secret_access_key": self.secret_key,
            "aws_session_token": self.session_token,
            "region_name": self.region,
            "endpoint_url": self.endpoint,
            "verify": self.secure,
        }

    async def create_bucket(
        self, bucket_name: str, suppress_already_owned_error: bool = True
    ):
        """Создать бакет."""
        if self.logger:
            self.logger.info(
                f"Создание бакета: '{bucket_name}'.",
            )

        async with self.session.create_client(
            "s3",
            **self.client_config,
        ) as client:
            try:
                return await client.create_bucket(Bucket=bucket_name)

            except client.exceptions.BucketAlreadyOwnedByYou as e:
                if suppress_already_owned_error:
                    return None

                raise e

    async def put_object(
        self, bucket_name: str, object_name: str, data: bytes
    ):
        """Добавить файл в хранилище."""
        if self.logger:
            self.logger.info(
                f"Добавление файла в бакет: '{bucket_name}/{object_name}'.",
                body={"bucket": bucket_name, "object_name": object_name},
            )

        async with self.session.create_client(
            "s3", **self.client_config
        ) as client:
            try:
                await client.put_object(
                    Bucket=bucket_name,
                    Key=object_name,
                    Body=data,
                )

            except client.exceptions.NoSuchBucket:
                await self.create_bucket(bucket_name=bucket_name)
                self.logger.info(f"Новый бакет с именем {bucket_name} создан")
                return await client.put_object(
                    Bucket=bucket_name, Key=object_name, Body=data
                )

    async def get_download_url(
        self, bucket_name: str, object_name: str
    ) -> str:
        """Получить ссылку запрашиваемого объекта для скачивания."""
        async with self.session.create_client(
            "s3", **self.client_config
        ) as client:
            try:
                request_url = await client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": bucket_name, "Key": object_name},
                    ExpiresIn=settings.default_url_lifetime,
                )
                return request_url

            except client.exceptions as err:
                self.logger.info(f"Не удалось получить ссылку: {err}")

    async def delete_object(self, bucket_name: str, object_name: str) -> None:
        """Удалить объект из бакета."""
        try:
            async with self.session.create_client(
                "s3", **self.client_config
            ) as client:
                response = await client.delete_object(
                    Bucket=bucket_name, Key=object_name
                )
                self.logger.info(f"Файл {object_name} удален!")

        except client.exceptions as err:
            self.logger.error(
                f"Не удалось удалить файл {object_name} из-за ошибки: {err}"
            )
            raise

        return response

    async def object_exists(
        self, bucket_name: str, object_name: str
    ) -> tuple[bool, dict]:
        """
        Проверяет, существует ли объект с заданным именем в бакете.
        Возвращает True, если объект существует, и False в противном случае.
        """
        try:
            self.logger.info(f"Пытаюсь получить информацию по: {object_name}")
            async with self.session.create_client(
                "s3", **self.client_config
            ) as client:
                meta = await client.head_object(
                    Bucket=bucket_name, Key=object_name
                )
            return True, meta

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                # Код 404 означает, что объект не найден
                self.logger.error(f"Объект {object_name} не найден")
                return False, e.response["ResponseMetadata"]
            else:
                # Другие ошибки могут быть обработаны по необходимости
                raise
