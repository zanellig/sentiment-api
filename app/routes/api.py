import asyncio
from fastapi import APIRouter, HTTPException
from app.models.schemas import TextInput, AnalysisResponse
from app.core.config import executor
from app.helpers.analysis import _run_analysis
from app.services.analyzer import analyzer_service

router = APIRouter()

@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    tags=["Analysis"],
    summary="Analyze text with NLP models",
    description="""
    Perform comprehensive text analysis using various NLP models.
    
    **Features:**
    - Sentiment analysis (positive/negative/neutral)
    - Emotion detection
    - Hate speech detection
    - Irony/sarcasm detection  
    - Named Entity Recognition (NER)
    - Part-of-Speech (POS) tagging
    - Targeted sentiment analysis
    
    **Note:** Models are loaded on-demand if not already loaded. 
    The analysis is performed asynchronously using a thread pool for optimal performance.
    
    **Example Request:**
    ```json
    {
      "text": "Me encanta este producto, es increíble!",
      "config": {
        "lang": "es",
        "sentiment": true,
        "emotion": true
      }
    }
    ```
    """,
    responses={
        200: {
            "description": "Successful analysis",
            "content": {
                "application/json": {
                    "example": {
                        "sentiment": {"label": "positive", "score": 0.98},
                        "emotion": {"label": "joy", "score": 0.95},
                        "hate_speech": None,
                        "irony": None,
                        "ner": None,
                        "pos": None,
                        "targeted_sentiment": None,
                        "warnings": []
                    }
                }
            }
        },
        500: {
            "description": "Internal server error during analysis",
            "content": {
                "application/json": {
                    "example": {"detail": "Model inference failed"}
                }
            }
        }
    }
)
async def analyze_text(input_data: TextInput):
    """
    Analyze text using configured NLP models.
    
    This endpoint processes text through the requested analysis models and returns
    comprehensive results. The inference is offloaded to a thread pool to keep the
    async event loop responsive.
    """
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, _run_analysis, input_data.text, input_data.config)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get(
    "/health",
    tags=["Health"],
    summary="Health check endpoint",
    description="""
    Check the health status of the API service.
    
    This endpoint returns:
    - Service status (healthy/unhealthy)
    - Number of models currently loaded in memory
    
    Use this endpoint for monitoring and health checks in production deployments.
    """,
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "models_loaded": 3
                    }
                }
            }
        }
    }
)
async def health_check():
    """
    Check API health and model status.
    
    Returns the current health status and the count of loaded models.
    """
    loaded_models = list(analyzer_service.models.keys())
    return {
        "status": "healthy", 
        "models_loaded": len(loaded_models),
        "models": loaded_models
    }
