"""Shared Pydantic models used across the application."""

from .telegram import TelegramMessage, TelegramUpdate

__all__ = ["TelegramMessage", "TelegramUpdate"]
