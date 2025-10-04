from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Request
from httpx import ASGITransport, AsyncClient

from spotify_linker.api.webhook import (
    SPOTIFY_LINK_PREFIX,
    build_caption_with_spotify_link,
    build_spotify_link,
    extract_relevant_message,
    get_message_text,
    get_spotify_client_from_request,
    get_telegram_client_from_request,
    log_track_candidate,
    lookup_candidate_on_spotify,
    update_telegram_caption_with_spotify_link,
)
from spotify_linker.clients import (
    SpotifyClient,
    SpotifyTrackSummary,
    TelegramAPIError,
    TelegramClient,
)
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


@pytest.mark.asyncio
async def test_telegram_webhook_warns_when_no_spotify_client(
    caplog: pytest.LogCaptureFixture,
) -> None:
    original = getattr(app.state, "spotify_client", None)
    original_telegram = getattr(app.state, "telegram_client", None)
    try:
        if hasattr(app.state, "spotify_client"):
            delattr(app.state, "spotify_client")
        if hasattr(app.state, "telegram_client"):
            delattr(app.state, "telegram_client")

        transport = ASGITransport(app=app)
        with caplog.at_level("WARNING"):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                payload: dict[str, Any] = {
                    "update_id": 555,
                    "message": {
                        "message_id": 42,
                        "text": "Any text",
                        "chat": {"id": 1, "type": "private"},
                    },
                }
                response = await client.post("/webhook/telegram", json=payload)

        assert response.status_code == 204
        assert "Spotify client unavailable; webhook will skip Spotify lookups" in caplog.text
    finally:
        if original is None:
            if hasattr(app.state, "spotify_client"):
                delattr(app.state, "spotify_client")
        else:
            app.state.spotify_client = original
        if original_telegram is None:
            if hasattr(app.state, "telegram_client"):
                delattr(app.state, "telegram_client")
        else:
            app.state.telegram_client = original_telegram


@pytest.mark.asyncio
async def test_telegram_webhook_skips_when_message_text_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    original = getattr(app.state, "spotify_client", None)
    original_telegram = getattr(app.state, "telegram_client", None)
    spotify_client = SpotifyClient(client_id="id", client_secret="secret")
    app.state.spotify_client = spotify_client
    if hasattr(app.state, "telegram_client"):
        delattr(app.state, "telegram_client")

    called: Dict[str, Any] = {}

    async def fake_lookup(
        client: SpotifyClient, _candidate: TrackCandidate
    ) -> SpotifyTrackSummary | None:
        called["client"] = client

    with caplog.at_level("INFO"):
        with patch(
            "spotify_linker.api.webhook.lookup_candidate_on_spotify",
            new=fake_lookup,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                payload: dict[str, Any] = {
                    "update_id": 777,
                    "message": {
                        "message_id": 3,
                        "text": "   ",
                        "chat": {"id": 2, "type": "private"},
                    },
                }
                response = await client.post("/webhook/telegram", json=payload)

    try:
        assert response.status_code == 204
        assert "Telegram message contains no textual content" in caplog.text
        assert "No track candidate could be built" in caplog.text
        assert not called
    finally:
        if original is None:
            if hasattr(app.state, "spotify_client"):
                delattr(app.state, "spotify_client")
        else:
            app.state.spotify_client = original
        if original_telegram is None:
            if hasattr(app.state, "telegram_client"):
                delattr(app.state, "telegram_client")
        else:
            app.state.telegram_client = original_telegram


@pytest.mark.asyncio
async def test_telegram_webhook_logs_when_no_message(caplog: pytest.LogCaptureFixture) -> None:
    transport = ASGITransport(app=app)
    with caplog.at_level("INFO"):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload: dict[str, Any] = {"update_id": 321}
            response = await client.post("/webhook/telegram", json=payload)

    assert response.status_code == 204
    assert "No Telegram message or channel post found in update" in caplog.text


@pytest.mark.asyncio
async def test_telegram_webhook_skips_when_caption_empty_after_normalization(
    caplog: pytest.LogCaptureFixture,
) -> None:
    original = getattr(app.state, "spotify_client", None)
    original_telegram = getattr(app.state, "telegram_client", None)
    spotify_client = SpotifyClient(client_id="id", client_secret="secret")
    app.state.spotify_client = spotify_client
    if hasattr(app.state, "telegram_client"):
        delattr(app.state, "telegram_client")

    called: Dict[str, Any] = {}

    async def fake_lookup(
        client: SpotifyClient, _candidate: TrackCandidate
    ) -> SpotifyTrackSummary | None:
        called["client"] = client

    with caplog.at_level("INFO"):
        with patch(
            "spotify_linker.api.webhook.lookup_candidate_on_spotify",
            new=fake_lookup,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                payload: dict[str, Any] = {
                    "update_id": 778,
                    "channel_post": {
                        "message_id": 4,
                        "caption": "\u3000\t ",
                        "chat": {"id": -200, "type": "channel"},
                    },
                }
                response = await client.post("/webhook/telegram", json=payload)

    try:
        assert response.status_code == 204
        assert "Telegram caption after normalization is empty" in caplog.text
        assert "No track candidate could be built" in caplog.text
        assert not called
    finally:
        if original is None:
            if hasattr(app.state, "spotify_client"):
                delattr(app.state, "spotify_client")
        else:
            app.state.spotify_client = original
        if original_telegram is None:
            if hasattr(app.state, "telegram_client"):
                delattr(app.state, "telegram_client")
        else:
            app.state.telegram_client = original_telegram


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


def test_extract_relevant_message_returns_none_when_no_message_or_channel() -> None:
    payload: dict[str, Any] = {"update_id": 3, "message": None, "channel_post": None}

    message = extract_relevant_message(TelegramUpdate.model_validate(payload))

    assert message is None


def test_get_message_text_prefers_caption_over_text() -> None:
    message = TelegramMessage.model_validate(
        {"message_id": 99, "text": "fallback", "caption": "caption"}
    )

    assert get_message_text(message) == "caption"


def test_get_message_text_returns_text_when_no_caption() -> None:
    message = TelegramMessage.model_validate({"message_id": 100, "text": "only text"})

    assert get_message_text(message) == "only text"


def test_get_message_text_returns_none_when_no_content() -> None:
    message = TelegramMessage.model_validate({"message_id": 101})

    assert get_message_text(message) is None


def test_get_message_text_uses_audio_metadata() -> None:
    message = TelegramMessage.model_validate(
        {
            "message_id": 102,
            "audio": {"performer": "Metallica", "title": "Nothing Else Matters"},
        }
    )

    assert get_message_text(message) == "Metallica - Nothing Else Matters"


def test_get_message_text_falls_back_to_audio_filename() -> None:
    message = TelegramMessage.model_validate(
        {
            "message_id": 103,
            "audio": {"file_name": "daft_punk-around_the_world.mp3"},
        }
    )

    assert get_message_text(message) == "daft punk-around the world"


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
    original_telegram = getattr(app.state, "telegram_client", None)
    try:
        spotify_client = SpotifyClient(client_id="id", client_secret="secret")
        app.state.spotify_client = spotify_client

        request = _build_request_for_app()

        assert get_spotify_client_from_request(request) is spotify_client
    finally:
        app.state.spotify_client = original
        if original_telegram is None:
            if hasattr(app.state, "telegram_client"):
                delattr(app.state, "telegram_client")
        else:
            app.state.telegram_client = original_telegram


def test_get_spotify_client_from_request_returns_none_when_missing() -> None:
    original = getattr(app.state, "spotify_client", None)
    original_telegram = getattr(app.state, "telegram_client", None)
    try:
        if hasattr(app.state, "spotify_client"):
            delattr(app.state, "spotify_client")
        if hasattr(app.state, "telegram_client"):
            delattr(app.state, "telegram_client")

        request = _build_request_for_app()

        assert get_spotify_client_from_request(request) is None
    finally:
        if original is not None:
            app.state.spotify_client = original
        else:
            if hasattr(app.state, "spotify_client"):
                delattr(app.state, "spotify_client")
        if original_telegram is not None:
            app.state.telegram_client = original_telegram
        else:
            if hasattr(app.state, "telegram_client"):
                delattr(app.state, "telegram_client")


@pytest.mark.asyncio
async def test_lookup_candidate_on_spotify_logs_match(caplog: pytest.LogCaptureFixture) -> None:
    client = AsyncMock(spec=SpotifyClient)
    candidate = TrackCandidate(raw_content="song", query="song", artist=None, title=None)
    summary = SpotifyTrackSummary(
        id="123",
        name="Song Title",
        artists=["Artist"],
        external_url="https://open.spotify.com/track/123",
    )

    client.search_track.return_value = summary
    with caplog.at_level("INFO"):
        result = await lookup_candidate_on_spotify(client, candidate)
    assert result is summary


@pytest.mark.asyncio
async def test_lookup_candidate_on_spotify_logs_no_match(caplog: pytest.LogCaptureFixture) -> None:
    client = AsyncMock(spec=SpotifyClient)
    candidate = TrackCandidate(raw_content="song", query="song", artist=None, title=None)

    client.search_track.return_value = None
    with caplog.at_level("INFO"):
        result = await lookup_candidate_on_spotify(client, candidate)
    assert result is None


@pytest.mark.asyncio
async def test_lookup_candidate_on_spotify_handles_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = AsyncMock(spec=SpotifyClient)
    candidate = TrackCandidate(raw_content="song", query="song", artist=None, title=None)

    client.search_track.side_effect = RuntimeError("boom")
    with caplog.at_level("ERROR"):
        result = await lookup_candidate_on_spotify(client, candidate)
    assert result is None


@pytest.mark.asyncio
async def test_handle_telegram_webhook_invokes_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    original = getattr(app.state, "spotify_client", None)
    original_telegram = getattr(app.state, "telegram_client", None)
    spotify_client = SpotifyClient(client_id="id", client_secret="secret")
    app.state.spotify_client = spotify_client
    app.state.telegram_client = TelegramClient(bot_token="token", channel_id="-100")

    called: Dict[str, Any] = {}

    async def fake_lookup(client: SpotifyClient, candidate: TrackCandidate) -> SpotifyTrackSummary:
        called["client"] = client
        called["query"] = candidate.query
        return SpotifyTrackSummary(
            id="123",
            name="Song Title",
            artists=["Artist"],
            external_url="https://example.com",
        )

    async def fake_post(
        telegram_client: TelegramClient,
        summary: SpotifyTrackSummary,
        *,
        source_message: TelegramMessage | None = None,
    ) -> None:
        called["telegram_client"] = telegram_client
        called["posted_summary"] = summary
        called["source_message"] = source_message

    monkeypatch.setattr("spotify_linker.api.webhook.lookup_candidate_on_spotify", fake_lookup)
    monkeypatch.setattr(
        "spotify_linker.api.webhook.update_telegram_caption_with_spotify_link",
        fake_post,
    )

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
        assert called["telegram_client"] is app.state.telegram_client
        assert called["posted_summary"].name == "Song Title"
        assert called["source_message"].message_id == 1
    finally:
        app.state.spotify_client = original
        if original_telegram is None:
            if hasattr(app.state, "telegram_client"):
                delattr(app.state, "telegram_client")
        else:
            app.state.telegram_client = original_telegram


@pytest.mark.asyncio
async def test_handle_telegram_webhook_uses_audio_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    original = getattr(app.state, "spotify_client", None)
    original_telegram = getattr(app.state, "telegram_client", None)
    spotify_client = SpotifyClient(client_id="id", client_secret="secret")
    app.state.spotify_client = spotify_client
    app.state.telegram_client = None

    called: Dict[str, Any] = {}

    async def fake_lookup(client: SpotifyClient, candidate: TrackCandidate) -> None:
        called["client"] = client
        called["query"] = candidate.query

    monkeypatch.setattr("spotify_linker.api.webhook.lookup_candidate_on_spotify", fake_lookup)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        payload: dict[str, Any] = {
            "update_id": 1001,
            "channel_post": {
                "message_id": 7,
                "audio": {"performer": "Artist", "title": "Song Title"},
                "chat": {"id": -600, "type": "channel"},
            },
        }
        response = await http_client.post("/webhook/telegram", json=payload)

    try:
        assert response.status_code == 204
        assert called["client"] is spotify_client
        assert called["query"] == "Artist - Song Title"
    finally:
        app.state.spotify_client = original
        if original_telegram is None:
            if hasattr(app.state, "telegram_client"):
                delattr(app.state, "telegram_client")
        else:
            app.state.telegram_client = original_telegram


def test_log_track_candidate_logs_none(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("INFO"):
        log_track_candidate(None)

    assert "No track candidate" in caplog.text


@pytest.mark.asyncio
async def test_lookup_candidate_on_spotify_skips_empty_query(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = SpotifyClient(client_id="id", client_secret="secret")
    candidate = TrackCandidate(raw_content="data", query=None, artist=None, title=None)

    with patch.object(SpotifyClient, "search_track", new_callable=AsyncMock) as mock_search:
        with caplog.at_level("INFO"):
            await lookup_candidate_on_spotify(client, candidate)

    mock_search.assert_not_called()
    assert "Spotify lookup skipped because normalized query is empty" in caplog.text


def test_get_spotify_client_from_request_warns_on_wrong_type(
    caplog: pytest.LogCaptureFixture,
) -> None:
    original = getattr(app.state, "spotify_client", None)
    original_telegram = getattr(app.state, "telegram_client", None)
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
        if original_telegram is None:
            if hasattr(app.state, "telegram_client"):
                delattr(app.state, "telegram_client")
        else:
            app.state.telegram_client = original_telegram

    assert result is None
    assert "Unexpected spotify_client type" in caplog.text


def test_build_spotify_link_prefers_external_url() -> None:
    summary = SpotifyTrackSummary(
        id="abc",
        name="Track",
        artists=["Artist 1", "Artist 2"],
        external_url="https://open.spotify.com/track/abc",
    )

    assert build_spotify_link(summary) == "https://open.spotify.com/track/abc"


def test_build_spotify_link_falls_back_to_track_id() -> None:
    summary = SpotifyTrackSummary(
        id="xyz",
        name="Unknown Track",
        artists=[],
        external_url="",
    )

    assert build_spotify_link(summary) == "https://open.spotify.com/track/xyz"


def test_build_spotify_link_returns_empty_when_id_missing() -> None:
    summary = SpotifyTrackSummary(
        id="",
        name="No Link",
        artists=[],
        external_url="",
    )

    assert build_spotify_link(summary) == ""


def test_build_caption_with_spotify_link_appends_when_missing() -> None:
    summary = SpotifyTrackSummary(
        id="123",
        name="Track",
        artists=["Artist"],
        external_url="https://open.spotify.com/track/123",
    )

    updated = build_caption_with_spotify_link("Great song", summary)

    assert updated == (
        "Great song\n"
        f"{SPOTIFY_LINK_PREFIX}https://open.spotify.com/track/123"
    )


def test_build_caption_with_spotify_link_skips_duplicate() -> None:
    link = "https://open.spotify.com/track/123"
    summary = SpotifyTrackSummary(
        id="123",
        name="Track",
        artists=["Artist"],
        external_url=link,
    )

    existing = f"Great song\n{SPOTIFY_LINK_PREFIX}{link}"
    assert build_caption_with_spotify_link(existing, summary) == existing


def test_build_caption_with_spotify_link_handles_empty_existing() -> None:
    summary = SpotifyTrackSummary(
        id="",
        name="Track",
        artists=["Artist"],
        external_url="https://example.com",
    )

    assert (
        build_caption_with_spotify_link("", summary)
        == f"{SPOTIFY_LINK_PREFIX}https://example.com"
    )


def test_build_caption_with_spotify_link_returns_none_when_link_unavailable() -> None:
    summary = SpotifyTrackSummary(
        id="",
        name="Track",
        artists=["Artist"],
        external_url="",
    )

    assert build_caption_with_spotify_link("Current caption", summary) is None


def test_build_caption_with_spotify_link_preserves_trailing_newline() -> None:
    summary = SpotifyTrackSummary(
        id="123",
        name="Track",
        artists=["Artist"],
        external_url="https://open.spotify.com/track/123",
    )

    caption = build_caption_with_spotify_link("Line one\n", summary)

    assert caption == (
        "Line one\n"
        f"{SPOTIFY_LINK_PREFIX}https://open.spotify.com/track/123"
    )


def test_get_telegram_client_from_request_returns_none_when_missing() -> None:
    original = getattr(app.state, "telegram_client", None)
    try:
        if hasattr(app.state, "telegram_client"):
            delattr(app.state, "telegram_client")

        request = _build_request_for_app()

        assert get_telegram_client_from_request(request) is None
    finally:
        if original is not None:
            app.state.telegram_client = original


def test_get_telegram_client_from_request_returns_instance() -> None:
    original = getattr(app.state, "telegram_client", None)
    client = TelegramClient(bot_token="token", channel_id="channel")
    app.state.telegram_client = client
    try:
        request = _build_request_for_app()

        assert get_telegram_client_from_request(request) is client
    finally:
        if original is not None:
            app.state.telegram_client = original
        else:
            if hasattr(app.state, "telegram_client"):
                delattr(app.state, "telegram_client")


def test_get_telegram_client_from_request_warns_on_invalid_type(
    caplog: pytest.LogCaptureFixture,
) -> None:
    original = getattr(app.state, "telegram_client", None)
    app.state.telegram_client = "invalid"  # type: ignore[assignment]
    try:
        request = _build_request_for_app()
        with caplog.at_level("WARNING"):
            client = get_telegram_client_from_request(request)
    finally:
        if original is None:
            if hasattr(app.state, "telegram_client"):
                delattr(app.state, "telegram_client")
        else:
            app.state.telegram_client = original

    assert client is None
    assert "Unexpected telegram_client type" in caplog.text


@pytest.mark.asyncio
async def test_update_caption_with_spotify_link_success(
    caplog: pytest.LogCaptureFixture,
) -> None:
    telegram_client = TelegramClient(bot_token="token", channel_id="channel")
    summary = SpotifyTrackSummary(
        id="123",
        name="Track",
        artists=["Artist"],
        external_url="https://open.spotify.com/track/123",
    )
    source_message = TelegramMessage.model_validate(
        {
            "message_id": 77,
            "caption": "Current caption",
            "chat": {"id": -200, "type": "channel"},
        }
    )

    fake_edit = AsyncMock(return_value={"ok": True})

    with caplog.at_level("INFO"):
        with patch.object(TelegramClient, "edit_message_caption", new=fake_edit):
            await update_telegram_caption_with_spotify_link(
                telegram_client,
                summary,
                source_message=source_message,
            )

    fake_edit.assert_awaited_once_with(
        message_id=77,
        caption=(
            "Current caption\n"
            f"{SPOTIFY_LINK_PREFIX}https://open.spotify.com/track/123"
        ),
        chat_id="-200",
    )
    assert "Updated Telegram caption with Spotify link" in caplog.text


@pytest.mark.asyncio
async def test_update_caption_with_spotify_link_skips_when_present(
    caplog: pytest.LogCaptureFixture,
) -> None:
    telegram_client = TelegramClient(bot_token="token", channel_id="channel")
    link = "https://open.spotify.com/track/123"
    summary = SpotifyTrackSummary(
        id="123",
        name="Track",
        artists=["Artist"],
        external_url=link,
    )
    source_message = TelegramMessage.model_validate(
        {
            "message_id": 88,
            "caption": f"Existing\n{SPOTIFY_LINK_PREFIX}{link}",
            "chat": {"id": -200, "type": "channel"},
        }
    )

    fake_edit = AsyncMock(return_value={"ok": True})

    with caplog.at_level("INFO"):
        with patch.object(TelegramClient, "edit_message_caption", new=fake_edit):
            await update_telegram_caption_with_spotify_link(
                telegram_client,
                summary,
                source_message=source_message,
            )

    fake_edit.assert_not_awaited()
    assert "Spotify link already present" in caplog.text


@pytest.mark.asyncio
async def test_update_caption_with_spotify_link_handles_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    telegram_client = TelegramClient(bot_token="token", channel_id="channel")
    summary = SpotifyTrackSummary(
        id="123",
        name="Track",
        artists=["Artist"],
        external_url="https://open.spotify.com/track/123",
    )
    source_message = TelegramMessage.model_validate(
        {
            "message_id": 90,
            "caption": "Caption",
            "chat": {"id": -200, "type": "channel"},
        }
    )

    fake_edit = AsyncMock(side_effect=TelegramAPIError("boom"))

    with caplog.at_level("ERROR"):
        with patch.object(TelegramClient, "edit_message_caption", new=fake_edit):
            await update_telegram_caption_with_spotify_link(
                telegram_client,
                summary,
                source_message=source_message,
            )

    fake_edit.assert_awaited_once()
    assert "Failed to edit Telegram message caption" in caplog.text


@pytest.mark.asyncio
async def test_update_caption_with_spotify_link_skips_when_link_unavailable(
    caplog: pytest.LogCaptureFixture,
) -> None:
    telegram_client = TelegramClient(bot_token="token", channel_id="channel")
    summary = SpotifyTrackSummary(
        id="",
        name="Track",
        artists=["Artist"],
        external_url="",
    )
    source_message = TelegramMessage.model_validate(
        {
            "message_id": 91,
            "caption": "Caption",
            "chat": {"id": -200, "type": "channel"},
        }
    )

    fake_edit = AsyncMock(return_value={"ok": True})

    with caplog.at_level("INFO"):
        with patch.object(TelegramClient, "edit_message_caption", new=fake_edit):
            await update_telegram_caption_with_spotify_link(
                telegram_client,
                summary,
                source_message=source_message,
            )

    fake_edit.assert_not_awaited()
    assert "Spotify link unavailable; skipping Telegram caption update" in caplog.text


@pytest.mark.asyncio
async def test_update_caption_with_spotify_link_warns_when_source_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    telegram_client = TelegramClient(bot_token="token", channel_id="channel")
    summary = SpotifyTrackSummary(
        id="123",
        name="Track",
        artists=["Artist"],
        external_url="https://open.spotify.com/track/123",
    )

    fake_edit = AsyncMock(return_value={"ok": True})

    with caplog.at_level("WARNING"):
        with patch.object(TelegramClient, "edit_message_caption", new=fake_edit):
            await update_telegram_caption_with_spotify_link(
                telegram_client,
                summary,
                source_message=None,
            )

    fake_edit.assert_not_awaited()
    assert "Cannot update Telegram caption because source message is missing" in caplog.text
