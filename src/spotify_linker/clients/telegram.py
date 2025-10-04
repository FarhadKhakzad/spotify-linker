"""Async client for interacting with the Telegram Bot API."""

from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Optional, cast

import httpx


class TelegramAPIError(RuntimeError):
    """Raised when a Telegram Bot API request fails."""


@dataclass(slots=True)
class TelegramClient:
    """Minimal Telegram client used for posting messages to a channel."""

    bot_token: str
    channel_id: str
    base_url: str = "https://api.telegram.org"

    async def send_message(
        self,
        text: str,
        *,
        disable_web_page_preview: bool = False,
        http_client: Optional[httpx.AsyncClient] = None,
        timeout: Optional[float] = 10.0,
    ) -> dict[str, Any]:
        """Send a message to the configured channel and return the Telegram response.

        Parameters
        ----------
        text:
            Message body to post to the channel.
        disable_web_page_preview:
            Whether to suppress link previews in Telegram.
        http_client:
            Optional existing :class:`httpx.AsyncClient` to reuse. When ``None``, a temporary
            client is created.
        timeout:
            Timeout, in seconds, for the Telegram HTTP request.
        """

        if not text.strip():
            raise ValueError("Telegram messages must contain non-empty text")

        url = f"{self.base_url}/bot{self.bot_token}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": self.channel_id,
            "text": text,
            "disable_web_page_preview": disable_web_page_preview,
        }

        async def _post(client: httpx.AsyncClient) -> dict[str, Any]:
            response = await client.post(url, json=payload)

            if response.status_code != HTTPStatus.OK:
                raise TelegramAPIError(
                    "Telegram sendMessage request failed: "
                    f"status={response.status_code}, body={response.text}"
                )

            try:
                payload_raw = response.json()
            except ValueError as exc:  # pragma: no cover - defensive guard
                raise TelegramAPIError("Telegram sendMessage response was not valid JSON") from exc

            if not isinstance(payload_raw, dict):
                raise TelegramAPIError(
                    "Telegram sendMessage response had unexpected structure"
                )

            payload_obj = cast(dict[str, Any], payload_raw)

            if not bool(payload_obj.get("ok", False)):
                description_raw = payload_obj.get("description", "Unknown error")
                description = str(description_raw)
                raise TelegramAPIError(f"Telegram sendMessage failed: {description}")

            return payload_obj

        if http_client is not None:
            return await _post(http_client)

        async with httpx.AsyncClient(timeout=timeout) as client:
            return await _post(client)

    async def edit_message_caption(
        self,
        *,
        message_id: int,
        caption: str,
        chat_id: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        timeout: Optional[float] = 10.0,
    ) -> dict[str, Any]:
        """Edit the caption of an existing message and return the Telegram response."""

        caption_to_use = caption.strip()
        if not caption_to_use:
            raise ValueError("Telegram captions must contain non-empty text")

        target_chat = chat_id or self.channel_id
        if not target_chat:
            raise ValueError("A chat_id is required to edit a Telegram message caption")

        url = f"{self.base_url}/bot{self.bot_token}/editMessageCaption"
        payload: dict[str, Any] = {
            "chat_id": target_chat,
            "message_id": message_id,
            "caption": caption_to_use,
        }

        async def _post(client: httpx.AsyncClient) -> dict[str, Any]:
            response = await client.post(url, json=payload)

            if response.status_code != HTTPStatus.OK:
                raise TelegramAPIError(
                    "Telegram editMessageCaption request failed: "
                    f"status={response.status_code}, body={response.text}"
                )

            try:
                payload_raw = response.json()
            except ValueError as exc:  # pragma: no cover - defensive guard
                raise TelegramAPIError(
                    "Telegram editMessageCaption response was not valid JSON"
                ) from exc

            if not isinstance(payload_raw, dict):
                raise TelegramAPIError(
                    "Telegram editMessageCaption response had unexpected structure"
                )

            payload_obj = cast(dict[str, Any], payload_raw)

            if not bool(payload_obj.get("ok", False)):
                description_raw = payload_obj.get("description", "Unknown error")
                description = str(description_raw)
                raise TelegramAPIError(f"Telegram editMessageCaption failed: {description}")

            return payload_obj

        if http_client is not None:
            return await _post(http_client)

        async with httpx.AsyncClient(timeout=timeout) as client:
            return await _post(client)
