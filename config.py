"""
Application configuration using environment variables.
"""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database settings
    database_url: str = Field(default="sqlite:///./chef_agent.db", alias="DATABASE_URL")
    sqlite_db: str = Field(default="chef_agent.db", alias="SQLITE_DB")
    
    # AI/LLM settings
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    model_name: str = Field(default="llama-3.1-8b-instant", alias="MODEL_NAME")
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1", alias="GROQ_BASE_URL")
    
    # MCP Server settings
    mcp_server_host: str = Field(default="localhost", alias="MCP_SERVER_HOST")
    mcp_server_port: int = Field(default=8002, alias="MCP_SERVER_PORT")
    mcp_server_url: str = Field(default="http://localhost:8002", alias="MCP_SERVER_URL")
    
    # FastAPI settings
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_reload: bool = Field(default=False, alias="API_RELOAD")
    
    # Redis settings
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    
    # Security settings
    secret_key: str = Field(default="change-me-in-production", alias="SECRET_KEY")
    csrf_secret: str = Field(default="csrf-secret-change-me", alias="CSRF_SECRET")
    
    # Rate limiting
    rate_limit_per_minute: int = Field(default=10, alias="RATE_LIMIT_PER_MINUTE")
    
    # Internationalization
    default_language: str = Field(default="en", alias="DEFAULT_LANGUAGE")
    supported_languages: list = Field(default=["en", "de", "fr"], alias="SUPPORTED_LANGUAGES")
    
    # File paths
    data_dir: Path = Field(default=Path("data"), alias="DATA_DIR")
    migrations_dir: Path = Field(default=Path("migrations"), alias="MIGRATIONS_DIR")
    locales_dir: Path = Field(default=Path("locales"), alias="LOCALES_DIR")
    
    # Development settings
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# Global settings instance
settings = Settings()