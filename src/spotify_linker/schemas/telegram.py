"""Pydantic models representing Telegram webhook payloads."""

from typing import Optional

from pydantic import BaseModel


class TelegramChat(BaseModel):
    """Basic information about a Telegram chat or channel."""

    id: int
    title: Optional[str] = None
    username: Optional[str] = None
    type: Optional[str] = None


class TelegramAudio(BaseModel):
    """Subset of Telegram audio metadata used for track extraction."""

    performer: Optional[str] = None
    title: Optional[str] = None
    file_name: Optional[str] = None


class TelegramMessage(BaseModel):
    """Subset of Telegram message fields needed for the project."""

    message_id: int
    text: Optional[str] = None
    caption: Optional[str] = None
    date: Optional[int] = None
    chat: Optional[TelegramChat] = None
    audio: Optional[TelegramAudio] = None


class TelegramUpdate(BaseModel):
    """Top-level Telegram update payload."""

    update_id: int
    message: Optional[TelegramMessage] = None
    channel_post: Optional[TelegramMessage] = None
