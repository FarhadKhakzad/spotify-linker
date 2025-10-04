from collections.abc import Iterator
from pathlib import Path

import pytest

from spotify_linker.config.settings import AppSettings, IGNORE_DOTENV_ENV_VAR, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_load_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_CHANNEL_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-id")

    settings = get_settings(ignore_dotenv=True)

    assert isinstance(settings, AppSettings)
    assert settings.telegram_bot_token == "test-token"
    assert settings.spotify_client_id == "client-id"
    assert settings.telegram_channel_id is None


def test_get_settings_respects_ignore_flag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("TELEGRAM_BOT_TOKEN=from-dotenv\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(IGNORE_DOTENV_ENV_VAR, raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    settings = get_settings()

    assert settings.telegram_bot_token == "from-dotenv"


def test_get_settings_env_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("TELEGRAM_BOT_TOKEN=from-dotenv\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(IGNORE_DOTENV_ENV_VAR, "true")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    settings = get_settings()

    assert settings.telegram_bot_token is None

    monkeypatch.delenv(IGNORE_DOTENV_ENV_VAR, raising=False)


def test_get_settings_ignore_argument(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("TELEGRAM_BOT_TOKEN=from-dotenv\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(IGNORE_DOTENV_ENV_VAR, raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    settings = get_settings(ignore_dotenv=True)

    assert settings.telegram_bot_token is None
