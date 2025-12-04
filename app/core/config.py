from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class PysentimientoSettings(BaseSettings):
    LANG: str = "es"
    DEFAULT_MODELS: list[str] = ["sentiment", "emotion", "hate_speech"]

class Settings(BaseSettings):
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format: text or json",
    )

    ENVIRONMENT: str = Field(
        default="production",
        description="Environment: development, testing, production",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_nested_delimiter="__",
    )

    # Nested settings
    pysentimiento: PysentimientoSettings = Field(default_factory=lambda: PysentimientoSettings())
    
    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def normalize_environment(cls, v: str) -> str:
        """Normalize environment to lowercase."""
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
