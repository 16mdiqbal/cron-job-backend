"""
Allow src to be run as a module: python -m src
"""
import os

import uvicorn

from .fastapi_app.config import get_settings

if __name__ == '__main__':
    settings = get_settings()
    port = int(os.getenv("FASTAPI_PORT") or settings.port)
    host = os.getenv("FASTAPI_HOST") or settings.host
    uvicorn.run("src.fastapi_app.main:app", host=host, port=port, log_level="info")
