import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings, executor, setup_logging
from app.services.analyzer import analyzer_service
from app.routes.api import router

# uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --limit-concurrency 100

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Loading models...")
    analyzer_service.load_models()
    logger.info("Models loaded successfully!")
    yield
    logger.info("Shutting down...")
    executor.shutdown(wait=True)

app = FastAPI(lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)