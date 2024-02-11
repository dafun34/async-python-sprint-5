import os
from typing import Annotated

from fastapi import Depends
from pydantic import Field, PostgresDsn
from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    """Класс настроек проекта."""

    host: str
    port: int
    db_name: str
    db_user: str
    db_pass: str
    db_host: str
    db_port: int
    db_driver: str
    auth_secret: str
    current_dir: str = os.path.dirname(os.path.abspath(__file__))
    base_dir: str = os.path.dirname(os.path.dirname(current_dir))
    tests_dir: str = os.path.join(base_dir, "tests")
    test_db: bool = Field(default=False)
    s3_protocol: str
    s3_host: str
    s3_access_key_id: str
    s3_bucket_name: str
    s3_secret_access_key: str
    s3_port: int
    default_url_lifetime: int = 86400

    class Config:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        env_file = os.path.join(
            os.path.dirname(os.path.dirname(current_dir)), ".env"
        )

    @property
    def db_url(self) -> PostgresDsn:
        """Получить ссылку для подключению к БД."""
        db_url = PostgresDsn.build(
            scheme=self.db_driver,
            username=self.db_user,
            password=self.db_pass,
            host=self.db_host,
            port=self.db_port,
            path=self.db_name,
        )
        return db_url


def get_settings() -> Settings:
    """Получить настройки проекта."""
    return Settings()


SettingsDependency = Annotated[BaseSettings, Depends(get_settings)]
