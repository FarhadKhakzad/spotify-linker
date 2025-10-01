"""Logging utilities for the Spotify Linker bot."""

import logging
from typing import Optional

_LOGGING_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    """Configure the root logger once with a consistent format."""

    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    _LOGGING_CONFIGURED = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a logger with the default configuration applied."""

    configure_logging()
    return logging.getLogger(name or "spotify_linker")
