"""Thin wrapper around the Spotify Web API."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, cast

import httpx

from spotify_linker.config.settings import AppSettings


class SpotifyClientConfigError(ValueError):
    """Raised when Spotify credentials are missing or invalid."""


class SpotifyAuthenticationError(RuntimeError):
    """Raised when Spotify fails to issue an access token."""


class SpotifyAPIError(RuntimeError):
    """Raised when a Spotify Web API request fails."""


@dataclass(slots=True)
class SpotifyAccessToken:
    """Container for Spotify access token metadata."""

    access_token: str
    token_type: str
    expires_in: int
    acquired_at: datetime

    def expires_at(self) -> datetime:
        """Return the absolute UTC expiry timestamp."""

        return self.acquired_at + timedelta(seconds=self.expires_in)

    def is_expired(self, *, buffer_seconds: int = 0) -> bool:
        """Return True if the token is expired (optionally with a buffer)."""

        threshold = self.expires_at() - timedelta(seconds=buffer_seconds)
        return datetime.now(timezone.utc) >= threshold


@dataclass(slots=True)
class SpotifyTrackSummary:
    """Minimal representation of a Spotify track result."""

    id: str
    name: str
    artists: list[str]
    external_url: str = ""


@dataclass(slots=True)
class SpotifyClient:
    """Minimal Spotify client to be expanded step by step."""

    client_id: str
    client_secret: str
    base_url: str = "https://api.spotify.com/v1"
    token_url: str = "https://accounts.spotify.com/api/token"
    _token_cache: Optional[SpotifyAccessToken] = field(default=None, init=False, repr=False)

    _EMPTY_MAPPING: Mapping[str, Any] = MappingProxyType({})

    async def search_track(
        self,
        query: str,
    *,
        limit: int = 1,
    http_client: Optional[httpx.AsyncClient] = None,
    timeout: Optional[float] = 10.0,
    ) -> Optional[SpotifyTrackSummary]:
        """Look up a track by query and return the first match if available."""

        token = await self.get_access_token(
            http_client=http_client,
            timeout=timeout,
        )

        headers = {
            "Authorization": f"{token.token_type} {token.access_token}",
            "Accept": "application/json",
        }
        params: dict[str, str] = {
            "q": query,
            "type": "track",
            "limit": str(limit),
        }

        async def _perform_search(client: httpx.AsyncClient) -> Optional[SpotifyTrackSummary]:
            response = await client.get(
                f"{self.base_url}/search",
                params=params,
                headers=headers,
            )

            if response.status_code != HTTPStatus.OK:
                detail: str
                try:
                    payload_obj = response.json()
                except ValueError:
                    payload_obj = {}

                if isinstance(payload_obj, Mapping):
                    payload_map = cast(Mapping[str, Any], payload_obj)
                else:
                    payload_map = self._EMPTY_MAPPING

                error_obj: Any = payload_map.get("error") if payload_map else None
                if isinstance(error_obj, Mapping):
                    error_map = cast(Mapping[str, Any], error_obj)
                    message = error_map.get("message")
                    detail = str(message) if message is not None else str(dict(error_map))
                else:
                    detail = str(error_obj or response.text or "Unknown error")

                raise SpotifyAPIError(
                    "Spotify search request failed: "
                    f"status={response.status_code}, detail={detail}"
                )

            try:
                payload_obj = response.json()
            except ValueError as exc:  # pragma: no cover - unexpected payload format
                raise SpotifyAPIError("Spotify search response was not valid JSON") from exc

            if not isinstance(payload_obj, Mapping):
                raise SpotifyAPIError("Spotify search response had unexpected format")

            payload_map = cast(Mapping[str, Any], payload_obj)

            tracks_section_any = payload_map.get("tracks")
            if not isinstance(tracks_section_any, Mapping):
                return None
            tracks_section = cast(Mapping[str, Any], tracks_section_any)

            items_raw = tracks_section.get("items")
            if not isinstance(items_raw, Sequence):
                return None

            items_seq = cast(Sequence[Any], items_raw)

            item_mappings: list[Mapping[str, Any]] = []
            for item in items_seq:
                if isinstance(item, Mapping):
                    item_mappings.append(cast(Mapping[str, Any], item))

            if not item_mappings:
                return None

            first_raw = item_mappings[0]

            artists_raw = first_raw.get("artists")
            if isinstance(artists_raw, Sequence):
                artists: list[str] = []
                artists_seq = cast(Sequence[Any], artists_raw)
                for artist in artists_seq:
                    if not isinstance(artist, Mapping):
                        continue
                    artist_map = cast(Mapping[str, Any], artist)
                    name_value: Any = artist_map.get("name")
                    if isinstance(name_value, str):
                        artists.append(name_value)
            else:
                artists = []

            external_urls = first_raw.get("external_urls")
            if isinstance(external_urls, Mapping):
                external_urls_map = cast(Mapping[str, Any], external_urls)
                spotify_url: Any = external_urls_map.get("spotify")
                external_url = str(spotify_url) if spotify_url is not None else ""
            else:
                external_url = ""

            return SpotifyTrackSummary(
                id=str(first_raw.get("id", "")),
                name=str(first_raw.get("name", "")),
                artists=artists,
                external_url=external_url or "",
            )

        if http_client is not None:
            return await _perform_search(http_client)

        async with httpx.AsyncClient(timeout=timeout) as client:
            return await _perform_search(client)

    async def get_client_credentials_token(
        self,
        http_client: Optional[httpx.AsyncClient] = None,
        *,
        timeout: Optional[float] = 10.0,
    ) -> SpotifyAccessToken:
        """Fetch a client-credentials access token from Spotify."""

        authorization = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode("utf-8"))
        headers = {
            "Authorization": f"Basic {authorization.decode('ascii')}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        async def _request_token(client: httpx.AsyncClient) -> SpotifyAccessToken:
            response = await client.post(
                self.token_url,
                data={"grant_type": "client_credentials"},
                headers=headers,
            )

            if response.status_code != HTTPStatus.OK:
                message: str
                try:
                    body = response.json()
                    message = body.get("error_description") or body.get("error") or "Unknown error"
                except ValueError:
                    message = response.text or "Unknown error"

                raise SpotifyAuthenticationError(
                    "Failed to obtain Spotify access token: "
                    f"status={response.status_code}, detail={message}"
                )

            payload = response.json()

            return SpotifyAccessToken(
                access_token=payload["access_token"],
                token_type=payload.get("token_type", "Bearer"),
                expires_in=int(payload.get("expires_in", 3600)),
                acquired_at=datetime.now(timezone.utc),
            )

        if http_client is not None:
            return await _request_token(http_client)

        async with httpx.AsyncClient(timeout=timeout) as client:
            return await _request_token(client)

    async def get_access_token(
        self,
        http_client: Optional[httpx.AsyncClient] = None,
        *,
        force_refresh: bool = False,
        buffer_seconds: int = 5,
        timeout: Optional[float] = 10.0,
    ) -> SpotifyAccessToken:
        """Return a valid (cached) client-credentials access token."""

        token = self._token_cache
        if not force_refresh and token is not None and not token.is_expired(buffer_seconds=buffer_seconds):
            return token

        token = await self.get_client_credentials_token(http_client, timeout=timeout)
        self._token_cache = token
        return token


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
