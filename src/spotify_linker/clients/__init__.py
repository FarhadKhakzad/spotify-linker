"""Client integrations for external services."""

from .spotify import SpotifyClient, SpotifyClientConfigError, build_spotify_client

__all__ = ["SpotifyClient", "SpotifyClientConfigError", "build_spotify_client"]
