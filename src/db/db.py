from typing import Annotated

import sqlalchemy
from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.core.config import get_settings

config = get_settings()

engine = create_async_engine(
    str(config.db_url), echo=True, future=True, poolclass=NullPool
)
async_session = async_sessionmaker(engine, expire_on_commit=False)

metadata = sqlalchemy.MetaData()


async def get_session() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


SessionDependency = Annotated[AsyncSession, Depends(get_session)]
