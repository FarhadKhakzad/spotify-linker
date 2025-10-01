"""Thin wrapper around the Spotify Web API."""

from dataclasses import dataclass

from spotify_linker.config.settings import AppSettings


class SpotifyClientConfigError(ValueError):
    """Raised when Spotify credentials are missing or invalid."""


@dataclass(slots=True)
class SpotifyClient:
    """Minimal Spotify client to be expanded step by step."""

    client_id: str
    client_secret: str
    base_url: str = "https://api.spotify.com/v1"

    async def search_track(self, query: str) -> None:
        """Placeholder for track search; real implementation will come later."""

        raise NotImplementedError("search_track will be implemented in a later step")


def build_spotify_client(settings: AppSettings) -> SpotifyClient:
    """Create a SpotifyClient instance from application settings."""

    if not settings.spotify_client_id or not settings.spotify_client_secret:
        raise SpotifyClientConfigError(
            "Spotify client credentials are required to instantiate SpotifyClient"
        )

    return SpotifyClient(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
    )
