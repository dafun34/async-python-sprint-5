import sys
from typing import Annotated

import loguru
from fastapi import Depends
from loguru import logger


def get_logger() -> "loguru.Logger":
    """Получить логгер."""
    logger.add(
        sys.stdout,
        colorize=True,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
    return logger


LoggerDependency = Annotated["loguru.Logger", Depends(get_logger)]
