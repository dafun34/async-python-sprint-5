import pytest
import sqlalchemy
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from sqlalchemy_utils import create_database, drop_database
from sqlalchemy_utils.functions import database_exists
from starlette.testclient import TestClient

from src.core.config import get_settings

settings = get_settings()

TEST_DB_HOST = "localhost"
SYNC_DB_DRIVER = "postgresql"


def get_sync_database_url():
    settings.db_host = TEST_DB_HOST
    settings.db_driver = SYNC_DB_DRIVER
    return str(settings.db_url)


@pytest.fixture(scope="session")
def sync_engine():
    database_url = get_sync_database_url()
    engine = sqlalchemy.create_engine(database_url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def sync_session(sync_engine):
    Session = sessionmaker(bind=sync_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def cleanup_after_test(sync_engine):
    yield
    session = sessionmaker(sync_engine)
    with session() as sync_session:
        # удаляя каскадно users мы удаляем и его файлы
        sync_session.execute(text("""TRUNCATE TABLE users CASCADE"""))
        sync_session.commit()


@pytest.fixture(autouse=True, scope="session")
def create_test_database(sync_engine):
    from src.db.db import metadata

    database_url = get_sync_database_url()
    if database_exists(database_url):
        drop_database(database_url)
    try:
        create_database(database_url)
        metadata.create_all(sync_engine)

        alembic_cfg = Config(f"{settings.base_dir}/alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        alembic_cfg.set_main_option(
            "script_location", f"{(str(settings.base_dir))}/migrations"
        )
        command.upgrade(alembic_cfg, "head")
        yield
        metadata.drop_all(sync_engine)
    finally:
        drop_database(database_url)


@pytest.fixture(scope="module")
def client():
    from src.main import app

    client = TestClient(app)

    yield client
