"""
Configuration management for the application.
Keeps environment-specific settings in one place.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Provides sensible defaults for development.
    """
    # Database
    database_url: str = "sqlite:///./meetings.db"
    
    # AI Service (OpenAI/Anthropic)
    ai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")  # or ANTHROPIC_API_KEY
    ai_provider: str = "openai"  # or "anthropic"
    ai_model: str = "gpt-4o-mini"  # or "claude-3-5-sonnet-20241022"
    ai_max_tokens: int = 2000
    ai_temperature: float = 0.1  # Low temperature for consistent extraction
    
    # API
    api_title: str = "Meeting Actions AI Service"
    api_version: str = "1.0.0"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Cache settings to avoid re-reading environment on every access.
    Use dependency injection in FastAPI routes.
    """
    return Settings()