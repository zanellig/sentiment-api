import asyncio
from fastapi import APIRouter, HTTPException
from app.models.schemas import TextInput, AnalysisResponse
from app.config.settings import executor
from app.helpers.analysis import _run_analysis

router = APIRouter()

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(input_data: TextInput):
    """Async endpoint that offloads inference to thread pool"""
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, _run_analysis, input_data.text, input_data.config)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get("/health")
async def health_check():
    from app.config.settings import analyzer
    return {"status": "healthy", "models_loaded": analyzer is not None}
