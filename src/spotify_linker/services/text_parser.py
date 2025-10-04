"""Utilities for extracting track queries from Telegram messages."""

import re
from dataclasses import dataclass
from typing import Optional, Tuple


def extract_track_query(content: Optional[str]) -> Optional[str]:
    """Return a cleaned search query candidate from raw message content."""

    if content is None:
        return None

    cleaned = content.strip()
    if not cleaned:
        return None

    normalized = re.sub(r"\s+", " ", cleaned)
    return normalized or None


_ARTIST_TITLE_PATTERN = re.compile(r"\s*[-–—]\s*")


def split_artist_title(query: Optional[str]) -> Optional[Tuple[str, str]]:
    """Split a query like 'Artist - Title' into its components if possible."""

    if not query:
        return None

    parts = _ARTIST_TITLE_PATTERN.split(query, maxsplit=1)
    if len(parts) != 2:
        return None

    artist, title = parts[0].strip(), parts[1].strip()
    if not artist or not title:
        return None

    return artist, title


@dataclass(slots=True)
class TrackCandidate:
    raw_content: str
    query: Optional[str]
    artist: Optional[str]
    title: Optional[str]


def build_track_candidate(content: Optional[str]) -> Optional[TrackCandidate]:
    """Produce a structured representation of the parsed track information."""

    if content is None:
        return None

    query = extract_track_query(content)
    if query is None:
        return None

    artist_title = split_artist_title(query)
    artist, title = artist_title if artist_title else (None, None)

    return TrackCandidate(
        raw_content=content,
        query=query,
        artist=artist,
        title=title,
    )
