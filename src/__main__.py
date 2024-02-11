import uvicorn

from src.core.config import get_settings

config = get_settings()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=True,
        loop="asyncio",
    )
