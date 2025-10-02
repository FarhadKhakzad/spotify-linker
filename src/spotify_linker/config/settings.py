"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


IGNORE_DOTENV_ENV_VAR = "SPOTIFY_LINKER_IGNORE_DOTENV"


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
def get_settings(*, ignore_dotenv: Optional[bool] = None) -> AppSettings:
    """Return a cached instance of application settings.

    Parameters
    ----------
    ignore_dotenv:
        Explicitly control whether the `.env` file should be ignored. When ``None``
        (the default), the environment variable ``SPOTIFY_LINKER_IGNORE_DOTENV``
        controls the behavior (case-insensitive truthy values disable the file).
    """

    if ignore_dotenv is None:
        env_override = os.getenv(IGNORE_DOTENV_ENV_VAR, "")
        ignore_dotenv = env_override.lower() in {"1", "true", "yes", "on"}

    if ignore_dotenv:
        return AppSettings(_env_file=None)  # type: ignore[call-arg]

    return AppSettings()
