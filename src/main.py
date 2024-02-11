from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from migrations.utils import upgrade_head
from src.api.v1 import auth, files, statuses, users
from src.core.log import get_logger

app = FastAPI(default_response_class=ORJSONResponse)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(statuses.router)
app.include_router(files.router)


@app.on_event("startup")
def start():
    logger = get_logger()
    logger.info("Сервер запущен")
    upgrade_head()
