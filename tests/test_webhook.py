from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Request
from httpx import ASGITransport, AsyncClient

from spotify_linker.api.webhook import (
    extract_relevant_message,
    get_message_text,
    get_spotify_client_from_request,
    log_track_candidate,
    lookup_candidate_on_spotify,
)
from spotify_linker.clients import SpotifyClient, SpotifyTrackSummary
from spotify_linker.main import app
from spotify_linker.schemas import TelegramMessage, TelegramUpdate
from spotify_linker.services import TrackCandidate


@pytest.mark.asyncio
async def test_telegram_webhook_returns_no_content() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload: dict[str, Any] = {
            "update_id": 123,
            "channel_post": {
                "message_id": 456,
                "caption": "Sample track caption",
                "chat": {"id": -1001234567890, "title": "Music is life", "type": "channel"},
            },
        }
        response = await client.post("/webhook/telegram", json=payload)

    assert response.status_code == 204
    assert response.content == b""


def test_extract_relevant_message_prefers_channel_post() -> None:
    payload: dict[str, Any] = {
        "update_id": 1,
        "message": {"message_id": 10, "text": "ignored"},
        "channel_post": {"message_id": 20, "caption": "channel"},
    }

    message = extract_relevant_message(TelegramUpdate.model_validate(payload))

    assert message is not None
    assert message.message_id == 20


def test_extract_relevant_message_returns_message_when_no_channel_post() -> None:
    payload: dict[str, Any] = {
        "update_id": 2,
        "message": {"message_id": 30, "text": "only message"},
        "channel_post": None,
    }

    message = extract_relevant_message(TelegramUpdate.model_validate(payload))

    assert message is not None
    assert message.message_id == 30


def test_get_message_text_prefers_caption_over_text() -> None:
    message = TelegramMessage.model_validate(
        {"message_id": 99, "text": "fallback", "caption": "caption"}
    )

    assert get_message_text(message) == "caption"


def test_get_message_text_returns_text_when_no_caption() -> None:
    message = TelegramMessage.model_validate({"message_id": 100, "text": "only text"})

    assert get_message_text(message) == "only text"


def _build_request_for_app() -> Request:
    scope: dict[str, Any] = {
        "type": "http",
        "app": app,
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("client", 50000),
        "scheme": "http",
    }
    return Request(scope)


def test_get_spotify_client_from_request_returns_instance() -> None:
    original = getattr(app.state, "spotify_client", None)
    try:
        spotify_client = SpotifyClient(client_id="id", client_secret="secret")
        app.state.spotify_client = spotify_client

        request = _build_request_for_app()

        assert get_spotify_client_from_request(request) is spotify_client
    finally:
        app.state.spotify_client = original


def test_get_spotify_client_from_request_returns_none_when_missing() -> None:
    original = getattr(app.state, "spotify_client", None)
    try:
        if hasattr(app.state, "spotify_client"):
            delattr(app.state, "spotify_client")

        request = _build_request_for_app()

        assert get_spotify_client_from_request(request) is None
    finally:
        if original is not None:
            app.state.spotify_client = original
        else:
            if hasattr(app.state, "spotify_client"):
                delattr(app.state, "spotify_client")


@pytest.mark.asyncio
async def test_lookup_candidate_on_spotify_logs_match(caplog: pytest.LogCaptureFixture) -> None:
    client = SpotifyClient(client_id="id", client_secret="secret")
    candidate = TrackCandidate(raw_content="song", query="song", artist=None, title=None)
    summary = SpotifyTrackSummary(
        id="123",
        name="Song Title",
        artists=["Artist"],
        external_url="https://open.spotify.com/track/123",
    )

    with patch.object(SpotifyClient, "search_track", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = summary
        with caplog.at_level("INFO"):
            await lookup_candidate_on_spotify(client, candidate)

    mock_search.assert_awaited_once()
    call_args = mock_search.await_args.args if mock_search.await_args else ()
    assert call_args == ("song",)
    assert "Spotify match found" in caplog.text


@pytest.mark.asyncio
async def test_lookup_candidate_on_spotify_logs_no_match(caplog: pytest.LogCaptureFixture) -> None:
    client = SpotifyClient(client_id="id", client_secret="secret")
    candidate = TrackCandidate(raw_content="song", query="song", artist=None, title=None)

    with patch.object(SpotifyClient, "search_track", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = None
        with caplog.at_level("INFO"):
            await lookup_candidate_on_spotify(client, candidate)

    mock_search.assert_awaited_once()
    call_args = mock_search.await_args.args if mock_search.await_args else ()
    assert call_args == ("song",)
    assert "No Spotify match found" in caplog.text


@pytest.mark.asyncio
async def test_lookup_candidate_on_spotify_handles_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = SpotifyClient(client_id="id", client_secret="secret")
    candidate = TrackCandidate(raw_content="song", query="song", artist=None, title=None)

    with patch.object(SpotifyClient, "search_track", new_callable=AsyncMock) as mock_search:
        mock_search.side_effect = RuntimeError("boom")
        with caplog.at_level("ERROR"):
            await lookup_candidate_on_spotify(client, candidate)

    mock_search.assert_awaited_once()
    call_args = mock_search.await_args.args if mock_search.await_args else ()
    assert call_args == ("song",)
    assert "Spotify lookup failed" in caplog.text


@pytest.mark.asyncio
async def test_handle_telegram_webhook_invokes_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    original = getattr(app.state, "spotify_client", None)
    spotify_client = SpotifyClient(client_id="id", client_secret="secret")
    app.state.spotify_client = spotify_client

    called: Dict[str, Any] = {}

    async def fake_lookup(client: SpotifyClient, candidate: TrackCandidate) -> None:
        called["client"] = client
        called["query"] = candidate.query

    monkeypatch.setattr("spotify_linker.api.webhook.lookup_candidate_on_spotify", fake_lookup)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        payload: dict[str, Any] = {
            "update_id": 999,
            "channel_post": {
                "message_id": 1,
                "caption": "Artist - Song",
                "chat": {"id": -1001, "title": "Music", "type": "channel"},
            },
        }
        response = await http_client.post("/webhook/telegram", json=payload)

    try:
        assert response.status_code == 204
        assert called["client"] is spotify_client
        assert called["query"] == "Artist - Song"
    finally:
        app.state.spotify_client = original


def test_log_track_candidate_logs_none(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("INFO"):
        log_track_candidate(None)

    assert "No track candidate" in caplog.text


@pytest.mark.asyncio
async def test_lookup_candidate_on_spotify_skips_empty_query() -> None:
    client = SpotifyClient(client_id="id", client_secret="secret")
    candidate = TrackCandidate(raw_content="data", query=None, artist=None, title=None)

    with patch.object(SpotifyClient, "search_track", new_callable=AsyncMock) as mock_search:
        await lookup_candidate_on_spotify(client, candidate)

    mock_search.assert_not_called()


def test_get_spotify_client_from_request_warns_on_wrong_type(
    caplog: pytest.LogCaptureFixture,
) -> None:
    original = getattr(app.state, "spotify_client", None)
    app.state.spotify_client = "not-a-client"  # type: ignore[assignment]
    try:
        request = _build_request_for_app()
        with caplog.at_level("WARNING"):
            result = get_spotify_client_from_request(request)
    finally:
        if original is None:
            if hasattr(app.state, "spotify_client"):
                delattr(app.state, "spotify_client")
        else:
            app.state.spotify_client = original

    assert result is None
    assert "Unexpected spotify_client type" in caplog.text
