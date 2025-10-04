import logging
from pathlib import Path

import pytest
from fastapi import FastAPI
from pytest import LogCaptureFixture, MonkeyPatch

from spotify_linker.clients import SpotifyClient, TelegramClient
from spotify_linker.config.settings import AppSettings, get_settings
from spotify_linker.main import lifespan, validate_critical_settings


@pytest.mark.asyncio
async def test_lifespan_initializes_spotify_client(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SPOTIFY_LINKER_IGNORE_DOTENV", "1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-token")
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "channel")
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "client-secret")

    get_settings.cache_clear()  # type: ignore[attr-defined]

    app_instance = FastAPI()

    async with lifespan(app_instance):
        assert isinstance(app_instance.state.spotify_client, SpotifyClient)
        assert isinstance(app_instance.state.telegram_client, TelegramClient)

    get_settings.cache_clear()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_lifespan_handles_missing_credentials(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SPOTIFY_LINKER_IGNORE_DOTENV", "1")
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "channel")

    get_settings.cache_clear()  # type: ignore[attr-defined]

    app = FastAPI()

    async with lifespan(app):
        assert getattr(app.state, "spotify_client", None) is None

    get_settings.cache_clear()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_lifespan_handles_missing_telegram_credentials(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SPOTIFY_LINKER_IGNORE_DOTENV", "1")
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "client-secret")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHANNEL_ID", raising=False)

    get_settings.cache_clear()  # type: ignore[attr-defined]

    app = FastAPI()

    async with lifespan(app):
        assert getattr(app.state, "telegram_client", None) is None

    get_settings.cache_clear()  # type: ignore[attr-defined]


def test_validate_critical_settings_logs_missing(
    caplog: LogCaptureFixture, monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    for env_var in [
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHANNEL_ID",
        "SPOTIFY_CLIENT_ID",
        "SPOTIFY_CLIENT_SECRET",
        "SPOTIFY_REDIRECT_URI",
    ]:
        monkeypatch.delenv(env_var, raising=False)

    monkeypatch.chdir(tmp_path)

    settings = AppSettings(_env_file=None)  # type: ignore[call-arg]

    assert settings.telegram_bot_token is None
    assert settings.spotify_client_id is None
    assert settings.spotify_client_secret is None

    caplog.set_level(logging.WARNING, logger="spotify_linker.main")

    validate_critical_settings(settings)

    assert any(
        "Missing recommended environment variables" in message
        for message in caplog.messages
    )


def test_validate_critical_settings_logs_all_present(caplog: LogCaptureFixture) -> None:
    settings = AppSettings.model_validate(
        {
            "TELEGRAM_BOT_TOKEN": "token",
            "TELEGRAM_CHANNEL_ID": "channel",
            "SPOTIFY_CLIENT_ID": "id",
            "SPOTIFY_CLIENT_SECRET": "secret",
        }
    )

    caplog.set_level(logging.INFO, logger="spotify_linker.main")

    validate_critical_settings(settings)

    assert any(
        "All critical environment variables are present" in message
        for message in caplog.messages
    )
