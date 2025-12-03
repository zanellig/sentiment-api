import logging
import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import executor, setup_logging
from app.services.analyzer import analyzer_service
from app.routes.api import router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to handle startup and shutdown events."""
    setup_logging()
    logger.info("Loading models...")
    analyzer_service.load_models()
    logger.info("Models loaded successfully!")
    yield
    logger.info("Shutting down...")
    analyzer_service.unload_models()
    executor.shutdown(wait=True)

app = FastAPI(lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    workers = os.cpu_count() or 1
    logger.info("Starting uvicorn with %s workers", workers)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, workers=workers)
