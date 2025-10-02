import base64
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from spotify_linker.clients import (
    SpotifyAccessToken,
    SpotifyAuthenticationError,
    SpotifyClient,
    SpotifyClientConfigError,
    SpotifyTrackSummary,
    build_spotify_client,
)
from spotify_linker.config.settings import AppSettings


def test_build_spotify_client_creates_instance() -> None:
    settings = AppSettings.model_validate(
        {
            "SPOTIFY_CLIENT_ID": "client-id",
            "SPOTIFY_CLIENT_SECRET": "client-secret",
        }
    )

    client = build_spotify_client(settings)

    assert isinstance(client, SpotifyClient)
    assert client.client_id == "client-id"
    assert client.client_secret == "client-secret"


def test_build_spotify_client_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)

    settings = AppSettings(_env_file=None)  # type: ignore[call-arg]

    with pytest.raises(SpotifyClientConfigError):
        build_spotify_client(settings)


@pytest.mark.asyncio
async def test_get_client_credentials_token_success() -> None:
    client = SpotifyClient(client_id="spotify-id", client_secret="spotify-secret")
    expected_auth = base64.b64encode(b"spotify-id:spotify-secret").decode("ascii")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == client.token_url
        assert request.headers.get("Authorization") == f"Basic {expected_auth}"
        assert request.content.decode("utf-8") == "grant_type=client_credentials"

        return httpx.Response(
            status_code=200,
            json={"access_token": "token123", "token_type": "Bearer", "expires_in": 3600},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        token = await client.get_client_credentials_token(http_client)

    assert isinstance(token, SpotifyAccessToken)
    assert token.access_token == "token123"
    assert token.token_type == "Bearer"
    assert token.expires_in == 3600
    assert not token.is_expired()


@pytest.mark.asyncio
async def test_get_client_credentials_token_error_response() -> None:
    client = SpotifyClient(client_id="bad-id", client_secret="bad-secret")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=400,
            json={"error": "invalid_client", "error_description": "Bad credentials"},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        with pytest.raises(SpotifyAuthenticationError) as exc:
            await client.get_client_credentials_token(http_client)

    assert "Bad credentials" in str(exc.value)


@pytest.mark.asyncio
async def test_access_token_expiration_check() -> None:
    token = SpotifyAccessToken(
        access_token="abc",
        token_type="Bearer",
        expires_in=30,
        acquired_at=datetime.now(timezone.utc) - timedelta(seconds=15),
    )

    assert not token.is_expired()
    assert token.is_expired(buffer_seconds=20)


@pytest.mark.asyncio
async def test_get_access_token_returns_cached_token() -> None:
    client = SpotifyClient(client_id="id", client_secret="secret")
    cached_token = SpotifyAccessToken(
        access_token="cached",
        token_type="Bearer",
        expires_in=3600,
        acquired_at=datetime.now(timezone.utc),
    )
    object.__setattr__(client, "_token_cache", cached_token)

    token = await client.get_access_token()

    assert token is cached_token


@pytest.mark.asyncio
async def test_get_access_token_refreshes_when_expired() -> None:
    client = SpotifyClient(client_id="id", client_secret="secret")
    expired_token = SpotifyAccessToken(
        access_token="old",
        token_type="Bearer",
        expires_in=1,
        acquired_at=datetime.now(timezone.utc) - timedelta(seconds=120),
    )
    object.__setattr__(client, "_token_cache", expired_token)
    call_count = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(
            status_code=200,
            json={"access_token": "fresh", "token_type": "Bearer", "expires_in": 1800},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        new_token = await client.get_access_token(http_client)

    assert call_count == 1
    assert new_token.access_token == "fresh"
    assert object.__getattribute__(client, "_token_cache") is new_token


@pytest.mark.asyncio
async def test_search_track_returns_summary() -> None:
    client = SpotifyClient(client_id="id", client_secret="secret")
    token = SpotifyAccessToken(
        access_token="token123",
        token_type="Bearer",
        expires_in=3600,
        acquired_at=datetime.now(timezone.utc),
    )
    object.__setattr__(client, "_token_cache", token)

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer token123"
        assert request.url.params["q"] == "test query"
        assert request.url.params["type"] == "track"
        assert request.url.params["limit"] == "1"

        return httpx.Response(
            status_code=200,
            json={
                "tracks": {
                    "items": [
                        {
                            "id": "track-id",
                            "name": "My Song",
                            "artists": [{"name": "Artist"}],
                            "external_urls": {"spotify": "https://open.spotify.com/track/track-id"},
                        }
                    ]
                }
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        result = await client.search_track("test query", http_client=http_client)

    assert isinstance(result, SpotifyTrackSummary)
    assert result.id == "track-id"
    assert result.name == "My Song"
    assert result.artists == ["Artist"]
    assert result.external_url == "https://open.spotify.com/track/track-id"


@pytest.mark.asyncio
async def test_search_track_handles_empty_results() -> None:
    client = SpotifyClient(client_id="id", client_secret="secret")
    token = SpotifyAccessToken(
        access_token="token123",
        token_type="Bearer",
        expires_in=3600,
        acquired_at=datetime.now(timezone.utc),
    )
    object.__setattr__(client, "_token_cache", token)

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json={"tracks": {"items": []}})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        result = await client.search_track("missing", http_client=http_client)

    assert result is None


