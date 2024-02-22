import os
from typing import List, Union

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import ORJSONResponse
from starlette import status

from src.api.v1.auth import login_manager
from src.core.log import LoggerDependency
from src.data_classes.files import DownloadResponse, FileItem
from src.db.db import SessionDependency
from src.models.user import User
from src.services.files import FilesService

router = APIRouter(tags=["Files"], prefix="/files")


def get_path(path, file) -> str:
    # Разбиваем абсолютный путь на каталоги
    directory_parts = path.split(os.path.sep)
    # Проверяем, что последний элемент не является именем файла
    if "." in directory_parts[-1]:
        # Если последний элемент содержит расширение файла,
        # считаем его частью пути к файлу собираем путь
        return str(os.path.join(*directory_parts))
    # в противном случае
    return str(os.path.join(*directory_parts, file.filename))


@router.post("/upload", response_model=FileItem, status_code=201)
async def upload_file(
    session: SessionDependency,
    logger: LoggerDependency,
    path: str = Form(
        "",
        description="<full-path-to-file>||<path-to-folder>",
    ),
    file: UploadFile = File(...),
    user=Depends(login_manager),
) -> Union[FileItem, HTTPException]:
    """Загрузить файл в хранилище"""
    path = get_path(path, file)
    data_bytes = await file.read()
    try:
        file_object = await FilesService.upload_file(
            path=path,
            data=data_bytes,
            email=user.email,
            session=session,
            filename=file.filename,
        )
        upload_file_response = FilesService.check_download_permissions(
            file_object, user
        )
        return upload_file_response

    except Exception as upload_error:
        logger.error(f"Произошла ошибка при загрузке файла: {upload_error}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(upload_error)
        )


@router.get("/files", response_model=List[FileItem], status_code=200)
async def get_files_list(
    session: SessionDependency,
    logger: LoggerDependency,
    user: User = Depends(login_manager),
) -> Union[List[FileItem], HTTPException]:
    """Получить список загруженных файлов."""
    result_files = []
    try:
        files = await FilesService.get_files(session)
        for file in files:
            result_files.append(
                FilesService.check_download_permissions(file, user)
            )
        return result_files
    except Exception as err:
        logger.error(
            f"Произошла ошибка при получении списка файлов: {str(err)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера",
        )


@router.get("/download", response_model=DownloadResponse)
async def download_file(
    path: str,
    session: SessionDependency,
    logger: LoggerDependency,
    user: User = Depends(login_manager),
) -> Union[DownloadResponse, HTTPException, ORJSONResponse]:
    """Получить ссылку для скачивания файла."""
    is_path: bool = FilesService.is_file_path(path)
    is_uuid: bool = FilesService.is_uuid(path)
    if is_path:
        file_object = await FilesService.get_file_by_path(
            path=path, session=session
        )
    elif is_uuid:
        file_object = await FilesService.get_file_by_id(
            id=path, session=session
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Не правильно указан путь или идентификатор файла",
        )
    if not file_object:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Не правильно указан путь или идентификатор файла",
        )
    file_object = FilesService.check_download_permissions(
        file_object=file_object, user=user
    )
    if file_object.is_downloadable:
        try:
            download_link = await FilesService.get_download_link(
                path=file_object.path
            )
            result = DownloadResponse(download_link=download_link)
            return result
        except Exception as err:
            logger.error(
                f"Не удалось получить ссылку из-за ошибки: {str(err)}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Внутренняя ошибка сервера",
            )
    else:
        return ORJSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content="У вас нет прав на скачивания этого файла",
        )
