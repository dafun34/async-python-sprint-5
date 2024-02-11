from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig

from src.core.config import get_settings


def upgrade_head() -> None:
    """Выполнить миграции."""
    settings = get_settings()
    alembic_config = AlembicConfig(f"{settings.base_dir}/alembic.ini")
    alembic_config.set_main_option(
        "script_location", f"{(str(settings.base_dir))}/migrations"
    )
    alembic_config.set_main_option("sqlalchemy.url", str(settings.db_url))
    alembic_command.upgrade(alembic_config, "head")
