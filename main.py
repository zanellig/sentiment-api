from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pysentimiento import create_analyzer
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

# uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --limit-concurrency 100

# Global variables
analyzer = None
executor = ThreadPoolExecutor(max_workers=4)

class TextInput(BaseModel):
    text: str

class AnalysisResponse(BaseModel):
    sentiment: dict
    emotion: dict
    hate_speech: dict

@asynccontextmanager
async def lifespan(app: FastAPI):
    global analyzer
    print("Loading models...")
    analyzer = {
        "sentiment": create_analyzer(task="sentiment", lang="es"),
        "emotion": create_analyzer(task="emotion", lang="es"),
        "hate_speech": create_analyzer(task="hate_speech", lang="es")
    }
    print("Models loaded successfully!")
    yield
    print("Shutting down...")
    executor.shutdown(wait=True)

app = FastAPI(lifespan=lifespan)

def _run_analysis(text: str) -> dict:
    """CPU-bound inference in thread pool"""
    # Get predictions
    sent_pred = analyzer["sentiment"].predict(text)
    emot_pred = analyzer["emotion"].predict(text)
    hate_pred = analyzer["hate_speech"].predict(text)
    
    # Convert to dict with proper structure
    return {
        "sentiment": {
            "label": sent_pred.output,
            "probas": sent_pred.probas
        },
        "emotion": {
            "label": emot_pred.output,
            "probas": emot_pred.probas
        },
        "hate_speech": {
            "label": hate_pred.output,
            "probas": hate_pred.probas
        }
    }

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(input_data: TextInput):
    """Async endpoint that offloads inference to thread pool"""
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, _run_analysis, input_data.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "models_loaded": analyzer is not None}