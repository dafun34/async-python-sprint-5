import time

import aiohttp
import asyncpg
from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from src.core.config import get_settings

settings = get_settings()


def seconds_to_milliseconds(seconds):
    ms = str(round(seconds * 1000, 2))
    return f"{ms} milliseconds"


async def check_minio():
    """Проверить отклик от хранилища minio."""
    start_time = time.time()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://minio:9001/") as response:
                if response.status == 200:
                    return seconds_to_milliseconds(time.time() - start_time)
                else:
                    return None
    except aiohttp.ClientError:
        return None


async def check_db():
    """Проверить есть ли отклик от БД."""
    start_time = time.time()
    try:
        conn = await asyncpg.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_pass,
            database=settings.db_name,
        )
        await conn.close()
        return seconds_to_milliseconds(time.time() - start_time)
    except asyncpg.exceptions.ConnectionFailureError:
        return None


router = APIRouter(tags=["Check health"])


@router.get("/ping")
async def ping() -> ORJSONResponse:
    services = {"db": await check_db(), "minio": await check_minio()}
    return ORJSONResponse(content=services, status_code=200)
