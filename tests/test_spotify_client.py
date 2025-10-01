import pytest

from spotify_linker.clients import SpotifyClient, SpotifyClientConfigError, build_spotify_client
from spotify_linker.config.settings import AppSettings


def test_build_spotify_client_creates_instance() -> None:
    settings = AppSettings.model_validate(
        {"SPOTIFY_CLIENT_ID": "client-id", "SPOTIFY_CLIENT_SECRET": "client-secret"}
    )

    client = build_spotify_client(settings)

    assert isinstance(client, SpotifyClient)
    assert client.client_id == "client-id"
    assert client.client_secret == "client-secret"
def test_build_spotify_client_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)

    settings = AppSettings()

    with pytest.raises(SpotifyClientConfigError):
        build_spotify_client(settings)
