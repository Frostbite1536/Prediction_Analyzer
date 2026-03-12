# prediction_analyzer/api/config.py
"""
API configuration settings
"""

from typing import Optional

from pydantic_settings import BaseSettings
import logging
import os
import secrets
import threading

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # JWT Configuration — MUST be overridden via SECRET_KEY env var in production
    SECRET_KEY: str = "change-this-secret-key-in-production"
    _DEFAULT_SECRET: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour (override via env var)

    # Database
    DATABASE_URL: str = "sqlite:///./data/prediction_analyzer.db"

    # CORS - comma-separated origins, e.g. "http://localhost:3000,https://myapp.com"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080"

    # App info
    APP_NAME: str = "Prediction Analyzer API"
    APP_VERSION: str = "1.0.0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


_settings_lock = threading.Lock()
_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Get cached settings instance (thread-safe)."""
    global _settings_instance
    if _settings_instance is not None:
        return _settings_instance
    with _settings_lock:
        # Double-checked locking
        if _settings_instance is not None:
            return _settings_instance
        settings = Settings()
        if settings.SECRET_KEY == settings._DEFAULT_SECRET:
            env = os.environ.get("ENVIRONMENT", os.environ.get("ENV", "development")).lower()
            if env in ("production", "prod", "staging"):
                raise RuntimeError(
                    "SECRET_KEY must be set to a secure random string in production. "
                    "Set the SECRET_KEY environment variable before starting the server."
                )
            # Generate a random key for dev so the hardcoded default is never used
            settings.SECRET_KEY = secrets.token_urlsafe(64)
            logger.warning(
                "SECRET_KEY was not set — generated a random ephemeral key for development. "
                "Set the SECRET_KEY environment variable to a stable value in production."
            )
        _settings_instance = settings
        return settings
