"""Logging utilities for the Spotify Linker bot."""

import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Configure the root logger with a consistent format if unset."""

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )

    root_logger.setLevel(level)


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a logger with the default configuration applied."""

    configure_logging()
    return logging.getLogger(name or "spotify_linker")
