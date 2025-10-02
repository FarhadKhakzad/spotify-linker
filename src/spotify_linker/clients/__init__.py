"""Client integrations for external services."""

from .spotify import (
	SpotifyAPIError,
	SpotifyAccessToken,
	SpotifyAuthenticationError,
	SpotifyClient,
	SpotifyClientConfigError,
	SpotifyTrackSummary,
	build_spotify_client,
)

__all__ = [
	"SpotifyAPIError",
	"SpotifyAccessToken",
	"SpotifyAuthenticationError",
	"SpotifyClient",
	"SpotifyClientConfigError",
	"SpotifyTrackSummary",
	"build_spotify_client",
]
