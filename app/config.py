from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    app_name: str = "Data Scraper & IM Pusher"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    
    # Security settings for code execution
    parser_timeout: int = 10  # seconds
    
    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
