"""Configuration management for Proxy Server using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Device authentication
    DEVICE_TOKEN: str = "default-insecure-token"

    # JWT settings for client authentication
    JWT_SECRET: str = "default-insecure-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",  # Vite default
        "http://localhost:3000",
    ]

    # WebSocket settings
    WS_TIMEOUT: int = 300  # 5 minutes
    WS_PING_INTERVAL: int = 30

    # Request timeout
    REQUEST_TIMEOUT: int = 60  # seconds


settings = Settings()
