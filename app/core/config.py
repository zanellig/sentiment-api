from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor

class Settings(BaseModel):
    LANG: str = "es"
    DEFAULT_MODELS: list[str] = ["sentiment", "emotion", "hate_speech"]
    
    class Config:
        arbitrary_types_allowed = True

settings = Settings()

# Global executor
executor = ThreadPoolExecutor(max_workers=4)
