import os

import pytest

from spotify_linker.config.settings import AppSettings, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()  # type: ignore[attr-defined]


def test_settings_load_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_CHANNEL_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-id")

    settings = get_settings()

    assert isinstance(settings, AppSettings)
    assert settings.telegram_bot_token == "test-token"
    assert settings.spotify_client_id == "client-id"
    assert settings.telegram_channel_id is None
