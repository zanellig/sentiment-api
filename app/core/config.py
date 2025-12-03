import logging
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor

class Settings(BaseModel):
    LANG: str = "es"
    DEFAULT_MODELS: list[str] = ["sentiment", "emotion", "hate_speech"]
    LOG_LEVEL: str = "INFO"
    
    class Config:
        arbitrary_types_allowed = True

settings = Settings()

# Global executor
executor = ThreadPoolExecutor(max_workers=4)

def setup_logging():
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
