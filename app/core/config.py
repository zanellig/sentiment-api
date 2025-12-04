import sys
from functools import lru_cache
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
import torch

from app.models.schemas import Device

load_dotenv()

class PysentimientoSettings(BaseSettings): 
    LANG: str = "es"
    DEFAULT_MODELS: list[str] = ["sentiment", "emotion", "hate_speech"]
    PREPROCESS_TWEETS: bool = False
    
    model_config = SettingsConfigDict(
        env_prefix="PYSENTIMIENTO__",
    )

    @field_validator("LANG", mode="before")
    @classmethod
    def normalize_lang(cls, v: str) -> str:
        if not v:
            return "es"
        v_lower = v.lower()
        supported = ['es', 'en', 'it', 'pt']
        for lang in supported:
            if v_lower == lang or v_lower.startswith(f"{lang}_") or v_lower.startswith(f"{lang}."):
                return lang
        return "es"

class Settings(BaseSettings):
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ENVIRONMENT: str = Field(default="production")

    DEVICE: Device = Field(
        default_factory=lambda: Device.cuda
        if torch.cuda.is_available()
        else Device.cpu,
        description="Device to use for computation (cuda or cpu)",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Nested settings
    pysentimiento: PysentimientoSettings = Field(default_factory=PysentimientoSettings)

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def normalize_environment(cls, v: str) -> str:
        return str(v).lower() if v else "production"

# Global executor
executor = ThreadPoolExecutor(max_workers=4)

@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance (singleton pattern).

    Returns:
        Settings: The application settings instance.
    """
    return Settings()

settings = get_settings()
