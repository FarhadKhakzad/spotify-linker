"""Client integrations for external services."""

from .spotify import (
    SpotifyAccessToken,
    SpotifyAPIError,
    SpotifyAuthenticationError,
    SpotifyClient,
    SpotifyClientConfigError,
    SpotifyTrackSummary,
    build_spotify_client,
)
from .telegram import TelegramAPIError, TelegramClient

__all__ = [
    "SpotifyAPIError",
    "SpotifyAccessToken",
    "SpotifyAuthenticationError",
    "SpotifyClient",
    "SpotifyClientConfigError",
    "SpotifyTrackSummary",
    "build_spotify_client",
    "TelegramAPIError",
    "TelegramClient",
]
