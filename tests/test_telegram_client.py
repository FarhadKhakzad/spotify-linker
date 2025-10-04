import json
from http import HTTPStatus
from typing import Any

import httpx
import pytest

from spotify_linker.clients import TelegramAPIError, TelegramClient


@pytest.mark.asyncio
async def test_send_message_success() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/botTOKEN/sendMessage")
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["chat_id"] == "CHANNEL"
        assert payload["text"] == "Hello"
        return httpx.Response(
            status_code=HTTPStatus.OK,
            json={"ok": True, "result": {"message_id": 1}},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        telegram_client = TelegramClient(bot_token="TOKEN", channel_id="CHANNEL")
        response = await telegram_client.send_message("Hello", http_client=client)

    assert response["ok"] is True


@pytest.mark.asyncio
async def test_send_message_raises_on_error_response() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=HTTPStatus.OK,
            json={"ok": False, "description": "error"},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        telegram_client = TelegramClient(bot_token="TOKEN", channel_id="CHANNEL")
        with pytest.raises(TelegramAPIError):
            await telegram_client.send_message("Hello", http_client=client)


@pytest.mark.asyncio
async def test_send_message_validates_text() -> None:
    telegram_client = TelegramClient(bot_token="TOKEN", channel_id="CHANNEL")

    with pytest.raises(ValueError):
        await telegram_client.send_message("   ")


@pytest.mark.asyncio
async def test_send_message_uses_async_client(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class DummyClient:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

        async def __aenter__(self) -> "DummyClient":
            return self

        async def __aexit__(
            self,
            exc_type: Any,
            exc: Any,
            tb: Any,
        ) -> None:
            captured["closed"] = True

        async def post(self, url: str, json: dict[str, Any]) -> httpx.Response:
            captured["url"] = url
            captured["payload"] = json
            return httpx.Response(status_code=HTTPStatus.OK, json={"ok": True})

    def factory(**kwargs: Any) -> DummyClient:
        return DummyClient(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)

    telegram_client = TelegramClient(bot_token="TOKEN", channel_id="CHANNEL")
    response = await telegram_client.send_message("Hello")

    assert response["ok"] is True
    assert captured["payload"]["text"] == "Hello"
    assert captured.get("closed") is True


@pytest.mark.asyncio
async def test_send_message_raises_on_http_error() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, text="boom")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        telegram_client = TelegramClient(bot_token="TOKEN", channel_id="CHANNEL")
        with pytest.raises(TelegramAPIError):
            await telegram_client.send_message("Hello", http_client=client)


@pytest.mark.asyncio
async def test_send_message_raises_on_unexpected_structure() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=HTTPStatus.OK, json=[{"ok": True}])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        telegram_client = TelegramClient(bot_token="TOKEN", channel_id="CHANNEL")
        with pytest.raises(TelegramAPIError):
            await telegram_client.send_message("Hello", http_client=client)


@pytest.mark.asyncio
async def test_edit_message_caption_success() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/botTOKEN/editMessageCaption")
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["chat_id"] == "CHANNEL"
        assert payload["message_id"] == 5
        assert payload["caption"] == "Updated"
        return httpx.Response(status_code=HTTPStatus.OK, json={"ok": True})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        telegram_client = TelegramClient(bot_token="TOKEN", channel_id="CHANNEL")
        response = await telegram_client.edit_message_caption(
            message_id=5,
            caption="  Updated  ",
            http_client=client,
        )

    assert response["ok"] is True


@pytest.mark.asyncio
async def test_edit_message_caption_uses_explicit_chat_id() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["chat_id"] == "@other"
        return httpx.Response(status_code=HTTPStatus.OK, json={"ok": True})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        telegram_client = TelegramClient(bot_token="TOKEN", channel_id="CHANNEL")
        await telegram_client.edit_message_caption(
            message_id=7,
            caption="Caption",
            chat_id="@other",
            http_client=client,
        )


@pytest.mark.asyncio
async def test_edit_message_caption_raises_on_error_response() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=HTTPStatus.BAD_REQUEST, text="oops")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        telegram_client = TelegramClient(bot_token="TOKEN", channel_id="CHANNEL")
        with pytest.raises(TelegramAPIError):
            await telegram_client.edit_message_caption(
                message_id=6,
                caption="Caption",
                http_client=client,
            )


@pytest.mark.asyncio
async def test_edit_message_caption_raises_when_ok_false() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=HTTPStatus.OK, json={"ok": False, "description": "err"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        telegram_client = TelegramClient(bot_token="TOKEN", channel_id="CHANNEL")
        with pytest.raises(TelegramAPIError):
            await telegram_client.edit_message_caption(
                message_id=8,
                caption="Caption",
                http_client=client,
            )


@pytest.mark.asyncio
async def test_edit_message_caption_raises_on_unexpected_structure() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=HTTPStatus.OK, json=[{"ok": True}])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        telegram_client = TelegramClient(bot_token="TOKEN", channel_id="CHANNEL")
        with pytest.raises(TelegramAPIError):
            await telegram_client.edit_message_caption(
                message_id=12,
                caption="Caption",
                http_client=client,
            )


@pytest.mark.asyncio
async def test_edit_message_caption_validates_caption() -> None:
    telegram_client = TelegramClient(bot_token="TOKEN", channel_id="CHANNEL")

    with pytest.raises(ValueError):
        await telegram_client.edit_message_caption(message_id=1, caption="   ")


@pytest.mark.asyncio
async def test_edit_message_caption_requires_target_chat() -> None:
    telegram_client = TelegramClient(bot_token="TOKEN", channel_id="")

    with pytest.raises(ValueError):
        await telegram_client.edit_message_caption(message_id=1, caption="Caption")


@pytest.mark.asyncio
async def test_edit_message_caption_opens_async_client(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class DummyClient:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

        async def __aenter__(self) -> "DummyClient":
            return self

        async def __aexit__(
            self,
            exc_type: Any,
            exc: Any,
            tb: Any,
        ) -> None:
            captured["closed"] = True

        async def post(self, url: str, json: dict[str, Any]) -> httpx.Response:
            captured["url"] = url
            captured["payload"] = json
            return httpx.Response(status_code=HTTPStatus.OK, json={"ok": True})

    def factory(**kwargs: Any) -> DummyClient:
        return DummyClient(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)

    telegram_client = TelegramClient(bot_token="TOKEN", channel_id="CHANNEL")
    response = await telegram_client.edit_message_caption(message_id=9, caption="Caption")

    assert response["ok"] is True
    assert captured["url"].endswith("/botTOKEN/editMessageCaption")
    assert captured["payload"]["chat_id"] == "CHANNEL"
    assert captured.get("closed") is True
