import pytest

from spotify_linker.services import (
    TrackCandidate,
    build_track_candidate,
    extract_track_query,
    split_artist_title,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("   Song Title - Artist   ", "Song Title - Artist"),
        ("\n\tAnother Track\n", "Another Track"),
        ("   ", None),
        (None, None),
    ],
)
def test_extract_track_query_cleans_whitespace(
    raw: str | None, expected: str | None
) -> None:
    assert extract_track_query(raw) == expected


@pytest.mark.parametrize(
    "query, expected",
    [
        ("Artist - Title", ("Artist", "Title")),
        ("Artist-Title", ("Artist", "Title")),
        ("Artist - ", None),
        ("SingleValue", None),
        (None, None),
    ],
)
def test_split_artist_title(
    query: str | None, expected: tuple[str, str] | None
) -> None:
    assert split_artist_title(query) == expected


def test_build_track_candidate_full_data() -> None:
    candidate = build_track_candidate("Artist - Title")

    assert isinstance(candidate, TrackCandidate)
    assert candidate.raw_content == "Artist - Title"
    assert candidate.query == "Artist - Title"
    assert candidate.artist == "Artist"
    assert candidate.title == "Title"


def test_build_track_candidate_handles_none() -> None:
    assert build_track_candidate(None) is None


def test_build_track_candidate_skips_blank_messages() -> None:
    assert build_track_candidate("   ") is None
