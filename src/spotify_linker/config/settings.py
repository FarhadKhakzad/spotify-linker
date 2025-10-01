"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Centralized configuration values for the application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_channel_id: Optional[str] = Field(default=None, alias="TELEGRAM_CHANNEL_ID")
    spotify_client_id: Optional[str] = Field(default=None, alias="SPOTIFY_CLIENT_ID")
    spotify_client_secret: Optional[str] = Field(default=None, alias="SPOTIFY_CLIENT_SECRET")
    spotify_redirect_uri: Optional[str] = Field(default=None, alias="SPOTIFY_REDIRECT_URI")


@lru_cache
def get_settings() -> AppSettings:
    """Return a cached instance of application settings."""

    return AppSettings()
