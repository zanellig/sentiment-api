import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pysentimiento import create_analyzer
from app.config import settings
from app.routes.api import router

# uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --limit-concurrency 100

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading models...")
    settings.analyzer = {
        "sentiment": create_analyzer(task="sentiment", lang="es"),
        "emotion": create_analyzer(task="emotion", lang="es"),
        "hate_speech": create_analyzer(task="hate_speech", lang="es")
    }
    print("Models loaded successfully!")
    yield
    print("Shutting down...")
    settings.executor.shutdown(wait=True)

app = FastAPI(lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)