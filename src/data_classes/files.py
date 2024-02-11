# from fastapi import File, UploadFile, Form
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FileItem(BaseModel):
    id: UUID = Field(description="Уникальный идентификатор файла")
    created_ad: datetime = Field(description="Дата создания")
    name: str = Field(description="Имя файла")
    path: str = Field(description="Полный путь до файла в хранилище")
    size: int = Field(description="Размер файла в байтах")
    is_downloadable: bool = Field(
        description="Доступен ли файл для скачивания"
    )

    class Config:
        ignore_extra = True


class DownloadResponse(BaseModel):
    download_link: str = Field(description="Ссылка для скачивания")
