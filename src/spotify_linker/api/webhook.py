"""Telegram webhook endpoints."""

from fastapi import APIRouter, Response, status

from spotify_linker.logger import get_logger
from spotify_linker.schemas import TelegramMessage, TelegramUpdate
from spotify_linker.services import (
    TrackCandidate,
    build_track_candidate,
    extract_track_query,
    split_artist_title,
)

router = APIRouter(prefix="/webhook", tags=["webhook"])
logger = get_logger(__name__)


@router.post("/telegram", status_code=status.HTTP_204_NO_CONTENT)
async def handle_telegram_webhook(payload: TelegramUpdate) -> Response:
    """Receive Telegram updates. Implementation will be filled in future steps."""

    message = extract_relevant_message(payload)
    logger.debug(
        "Received Telegram webhook payload: update_id=%s, message_id=%s",
        payload.update_id,
        message.message_id if message else "<none>",
    )
    if message:
        content = get_message_text(message) or ""
        logger.info("Extracted message content: %s", content)
        query = extract_track_query(content)
        if query:
            logger.info("Normalized track query: %s", query)
            split = split_artist_title(query)
            if split:
                artist, title = split
                logger.info("Parsed artist/title: %s — %s", artist, title)
        candidate = build_track_candidate(content)
        log_track_candidate(candidate)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def extract_relevant_message(payload: TelegramUpdate):
    """Return the channel post or regular message contained in the update."""

    if payload.channel_post is not None:
        return payload.channel_post
    return payload.message


def get_message_text(message: TelegramMessage) -> str | None:
    """Return the best textual content from a Telegram message."""

    if message.caption:
        return message.caption
    return message.text


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
