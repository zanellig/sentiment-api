import logging
import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.core.config import executor, setup_logging, settings
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

app = FastAPI(
    title="Sentiment Analysis API",
    description="""
## Advanced NLP Sentiment Analysis API

This API provides comprehensive text analysis capabilities including:

* **Sentiment Analysis** - Detect positive, negative, or neutral sentiment
* **Emotion Detection** - Identify emotions like joy, sadness, anger, fear, etc.
* **Hate Speech Detection** - Flag potentially harmful or offensive content
* **Irony Detection** - Detect sarcastic or ironic statements
* **Named Entity Recognition (NER)** - Extract entities like persons, organizations, locations
* **Part-of-Speech (POS) Tagging** - Identify grammatical components
* **Targeted Sentiment Analysis** - Analyze sentiment towards specific entities

### Features

- 🚀 Fast and scalable inference using thread pool executors
- 🧠 Multiple pre-trained NLP models
- 🌍 Multi-language support (Spanish by default, configurable)
- ⚡ Async API with automatic model loading/unloading
- 📊 Comprehensive analysis results

### Usage

Send a POST request to `/analyze` with your text and configuration options.
Check `/health` endpoint to verify service status.
    """,
    version="1.0.0",
    contact={
        "name": "API Support",
        "email": "gonzalozanelli1+support@gmail.com",
    },
    license_info={
        "name": "GPLv3 License",
        "url": "https://opensource.org/licenses/GPL-3.0",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
app.include_router(router)

@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API documentation."""
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    workers = os.cpu_count() or 1
    logger.info("Starting uvicorn with %s workers", workers)
    uvicorn.run(
        "main:app", 
        host="0.0.0.0",
        port=8000,
        workers=1,
        reload=settings.ENVIRONMENT == "development"
    )
