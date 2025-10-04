"""Telegram webhook endpoints."""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request, Response, status

from spotify_linker.clients import (
    SpotifyClient,
    SpotifyTrackSummary,
    TelegramAPIError,
    TelegramClient,
)
from spotify_linker.logger import get_logger
from spotify_linker.schemas import TelegramMessage, TelegramUpdate
from spotify_linker.services import (
    TrackCandidate,
    build_track_candidate,
)

router = APIRouter(prefix="/webhook", tags=["webhook"])
logger = get_logger(__name__)

SPOTIFY_LINK_PREFIX = "🎧 "


@router.post("/telegram", status_code=status.HTTP_204_NO_CONTENT)
async def handle_telegram_webhook(request: Request, payload: TelegramUpdate) -> Response:
    """Receive Telegram updates. Implementation will be filled in future steps."""

    message = extract_relevant_message(payload)
    logger.info(
        "Received Telegram webhook payload: update_id=%s, message_id=%s",
        payload.update_id,
        message.message_id if message else "<none>",
    )
    client = get_spotify_client_from_request(request)
    if client:
        logger.debug("Spotify client available for webhook processing")
    else:
        logger.warning("Spotify client unavailable; webhook will skip Spotify lookups")

    telegram_client = get_telegram_client_from_request(request)
    if telegram_client:
        logger.debug("Telegram client available for outbound notifications")
    else:
        logger.debug("Telegram client unavailable; outbound notifications disabled")

    if message:
        raw_content = get_message_text(message)
        logger.info("Extracted message content: %s", raw_content or "")

        if raw_content is None or not raw_content.strip():
            if message.caption is None:
                logger.warning("Telegram message contains no textual content; skipping processing")
            else:
                logger.warning(
                    "Telegram caption after normalization is empty; skipping processing"
                )
            log_track_candidate(None)
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        candidate = build_track_candidate(raw_content)
        if candidate and candidate.query:
            logger.info("Normalized track query: %s", candidate.query)
            if candidate.artist and candidate.title:
                logger.info("Parsed artist/title: %s — %s", candidate.artist, candidate.title)

        log_track_candidate(candidate)

        summary: SpotifyTrackSummary | None = None
        if client and candidate and candidate.query:
            summary = await lookup_candidate_on_spotify(client, candidate)

        if summary and telegram_client:
            await update_telegram_caption_with_spotify_link(
                telegram_client,
                summary,
                source_message=message,
            )
    else:
        logger.info("No Telegram message or channel post found in update; skipping processing")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def extract_relevant_message(payload: TelegramUpdate) -> TelegramMessage | None:
    """Return the channel post or regular message contained in the update."""

    if payload.channel_post is not None:
        return payload.channel_post
    return payload.message


def get_message_text(message: TelegramMessage) -> str | None:
    """Return the best textual content from a Telegram message."""

    if message.caption:
        return message.caption

    if message.text:
        return message.text

    audio = getattr(message, "audio", None)
    if audio:
        performer = (audio.performer or "").strip()
        title = (audio.title or "").strip()

        if performer and title:
            candidate = f"{performer} - {title}"
        else:
            candidate = performer or title or ""

        if not candidate and audio.file_name:
            stem = Path(audio.file_name).stem
            candidate = stem.replace("_", " ").strip()

        candidate = candidate.strip()
        if candidate:
            logger.debug("Derived message text from audio metadata: %s", candidate)
            return candidate

    return None


def log_track_candidate(candidate: TrackCandidate | None) -> None:
    """Log the structured track candidate for debugging purposes."""

    if candidate is None:
        logger.info("No track candidate could be built from the message")
        return

    logger.info(
        "Track candidate — query: %s | artist: %s | title: %s",
        candidate.query,
        candidate.artist,
        candidate.title,
    )


async def lookup_candidate_on_spotify(
    client: SpotifyClient, candidate: TrackCandidate
) -> SpotifyTrackSummary | None:
    """Execute a search against Spotify for the provided candidate and log the outcome."""

    query = candidate.query
    if not query:
        logger.info("Spotify lookup skipped because normalized query is empty")
        return None

    try:
        summary = await client.search_track(query)
    except Exception:  # pragma: no cover - defensive guard for unexpected API errors
        logger.exception("Spotify lookup failed for query: %s", query)
        return None

    if summary is None:
        logger.info("No Spotify match found for query: %s", query)
        return None

    artists_display = ", ".join(summary.artists) if summary.artists else "<unknown artist>"
    logger.info(
        "Spotify match found: %s — %s (%s)",
        artists_display,
        summary.name,
        summary.external_url or "<no url>",
    )
    return summary


def get_spotify_client_from_request(request: Request) -> SpotifyClient | None:
    """Return the configured Spotify client from the FastAPI application state."""

    spotify_client = getattr(request.app.state, "spotify_client", None)
    if spotify_client is None:
        return None
    if not isinstance(spotify_client, SpotifyClient):
        type_name = type(spotify_client).__name__
        logger.warning("Unexpected spotify_client type on app state: %s", type_name)
        return None
    return spotify_client


def get_telegram_client_from_request(request: Request) -> TelegramClient | None:
    """Return the configured Telegram client from the FastAPI application state."""

    telegram_client = getattr(request.app.state, "telegram_client", None)
    if telegram_client is None:
        return None
    if not isinstance(telegram_client, TelegramClient):
        type_name = type(telegram_client).__name__
        logger.warning("Unexpected telegram_client type on app state: %s", type_name)
        return None
    return telegram_client


def build_spotify_link(summary: SpotifyTrackSummary) -> str:
    """Return the preferred Spotify URL for the summary if available."""

    if summary.external_url:
        return summary.external_url
    if summary.id:
        return f"https://open.spotify.com/track/{summary.id}"
    return ""


def build_caption_with_spotify_link(
    existing_caption: str | None, summary: SpotifyTrackSummary
) -> str | None:
    """Append the Spotify link to the existing caption when missing."""

    link = build_spotify_link(summary).strip()
    if not link:
        return None

    current = existing_caption or ""
    link_line = f"{SPOTIFY_LINK_PREFIX}{link}"

    if link_line in current or link in current:
        return current

    if current.strip():
        if current.endswith(("\n", "\r")):
            return f"{current}{link_line}"
        return f"{current.rstrip()}\n{link_line}"

    return link_line


async def update_telegram_caption_with_spotify_link(
    telegram_client: TelegramClient,
    summary: SpotifyTrackSummary,
    *,
    source_message: TelegramMessage | None = None,
) -> None:
    """Edit the source message caption to include the Spotify link."""

    if source_message is None:
        logger.warning("Cannot update Telegram caption because source message is missing")
        return

    new_caption = build_caption_with_spotify_link(source_message.caption, summary)
    if new_caption is None:
        logger.info("Spotify link unavailable; skipping Telegram caption update")
        return

    current_caption = source_message.caption or ""
    if new_caption == current_caption:
        logger.info("Spotify link already present in caption; skipping Telegram edit")
        return

    chat_id = None
    if source_message.chat:
        chat_id = str(source_message.chat.id)

    try:
        response: dict[str, Any] = await telegram_client.edit_message_caption(
            message_id=source_message.message_id,
            caption=new_caption,
            chat_id=chat_id,
        )
    except TelegramAPIError:
        logger.exception("Failed to edit Telegram message caption with Spotify link")
        return

    logger.info(
        "Updated Telegram caption with Spotify link: message_id=%s, result_ok=%s",
        source_message.message_id,
        bool(response.get("ok")),
    )
