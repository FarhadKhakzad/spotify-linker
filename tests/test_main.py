from fastapi.testclient import TestClient

from spotify_linker.clients import SpotifyClient
from spotify_linker.config.settings import get_settings


def test_lifespan_initializes_spotify_client(monkeypatch):
    monkeypatch.setenv("SPOTIFY_LINKER_IGNORE_DOTENV", "1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-token")
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "client-secret")

    get_settings.cache_clear()  # type: ignore[attr-defined]

    # Import here so settings read the monkeypatched environment.
    from spotify_linker.main import app

    with TestClient(app) as client:
        assert isinstance(client.app.state.spotify_client, SpotifyClient)

    get_settings.cache_clear()  # type: ignore[attr-defined]
