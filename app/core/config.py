import logging
from concurrent.futures import ThreadPoolExecutor
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    LANG: str = "es"
    DEFAULT_MODELS: list[str] = ["sentiment", "emotion", "hate_speech"]
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "production"  # "development" or "production"

    class Config:
        arbitrary_types_allowed = True
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# Global executor
executor = ThreadPoolExecutor(max_workers=4)

def setup_logging():
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
