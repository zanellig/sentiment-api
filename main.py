import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings, executor
from app.services.analyzer import analyzer_service
from app.routes.api import router

# uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --limit-concurrency 100

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading models...")
    analyzer_service.load_models()
    print("Models loaded successfully!")
    yield
    print("Shutting down...")
    executor.shutdown(wait=True)

app = FastAPI(lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)