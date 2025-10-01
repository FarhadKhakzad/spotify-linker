import pytest
from httpx import ASGITransport, AsyncClient

from spotify_linker.api.webhook import extract_relevant_message, get_message_text
from spotify_linker.main import app
from spotify_linker.schemas import TelegramMessage, TelegramUpdate


@pytest.mark.asyncio
async def test_telegram_webhook_returns_no_content() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
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
    payload = {
        "update_id": 1,
        "message": {"message_id": 10, "text": "ignored"},
        "channel_post": {"message_id": 20, "caption": "channel"},
    }

    message = extract_relevant_message(TelegramUpdate.model_validate(payload))

    assert message is not None
    assert message.message_id == 20


def test_get_message_text_prefers_caption_over_text() -> None:
    message = TelegramMessage.model_validate(
        {"message_id": 99, "text": "fallback", "caption": "caption"}
    )

    assert get_message_text(message) == "caption"


def test_get_message_text_returns_text_when_no_caption() -> None:
    message = TelegramMessage.model_validate({"message_id": 100, "text": "only text"})

    assert get_message_text(message) == "only text"
