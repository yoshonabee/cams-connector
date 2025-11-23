"""Configuration for Pi Client using pydantic-settings."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pi Client settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Device identification
    DEVICE_ID: str = "cam1"
    DEVICE_TOKEN: str = "default-insecure-token"

    # Proxy connection
    PROXY_URL: str = "ws://localhost:8000/ws/device/cam1"

    # Local storage
    RECORDINGS_DIR: Path = Path.home() / "recordings"

    # WebSocket settings
    RECONNECT_DELAY: int = 5  # seconds
    PING_INTERVAL: int = 30
    PING_TIMEOUT: int = 10

    # File reading
    CHUNK_SIZE: int = 256 * 1024  # 256KB chunks


settings = Settings()
