"""Extract movie title and year from file paths and filenames."""

import re
from pathlib import Path

from .models import ParsedMovie

# Year: (1999), [1999], or 1999 with word boundaries
YEAR_PATTERN = re.compile(
    r"(?:^|[^\d])"
    r"((?:19|20)\d{2})"
    r"(?:[^\d]|$)",
    re.IGNORECASE,
)
YEAR_BRACKETS = re.compile(r"[([]\s*((?:19|20)\d{2})\s*[])]", re.IGNORECASE)

# Tokens to strip (case-insensitive); order can matter for edge cases
RESOLUTION = re.compile(
    r"\b(720p|1080p|2160p|4k|uhd|480p|576p)\b",
    re.IGNORECASE,
)
CODECS = re.compile(
    r"\b(x264|x265|h264|h265|hevc|avc|xvid|divx)\b",
    re.IGNORECASE,
)
SOURCE = re.compile(
    r"\b(bluray|blu-ray|web-dl|webrip|hdrip|brrip|hdtv|dvdrip|dvdscr|screener)\b",
    re.IGNORECASE,
)
AUDIO = re.compile(
    r"\b(dts|aac|ac3|5\.1|7\.1|dts-hd|dolby|truehd|flac)\b",
    re.IGNORECASE,
)
OTHER = re.compile(
    r"\b(repack|proper|extended|unrated|directors?\s*cut|remastered)\b",
    re.IGNORECASE,
)
# Group names: -RARBG, -YIFY, etc. (hyphen + word at end)
RELEASE_GROUP = re.compile(r"-\s*[a-z0-9]+\s*$", re.IGNORECASE)

ALL_STRIP_PATTERNS = [
    YEAR_BRACKETS,  # remove (1999) / [1999] from stem for title cleaning
    RESOLUTION,
    CODECS,
    SOURCE,
    AUDIO,
    OTHER,
    RELEASE_GROUP,
]


def _extract_year(text: str) -> int | None:
    """Return first plausible movie year (1900-2030) from text."""
    # Prefer bracketed year first
    for m in YEAR_BRACKETS.finditer(text):
        try:
            y = int(m.group(1))  # full 4-digit year
            if 1900 <= y <= 2030:
                return y
        except (ValueError, IndexError):
            continue
    for m in YEAR_PATTERN.finditer(text):
        try:
            y = int(m.group(1))
            if 1900 <= y <= 2030:
                return y
        except (ValueError, IndexError):
            continue
    return None


def _normalize_separators(text: str) -> str:
    """Replace dots, underscores, hyphens with spaces; collapse spaces."""
    text = text.replace(".", " ").replace("_", " ").replace("-", " ")
    return " ".join(text.split())


def _strip_tokens(text: str) -> str:
    """Remove resolution, codec, source, audio, and other release tags."""
    for pat in ALL_STRIP_PATTERNS:
        text = pat.sub(" ", text)
    return _normalize_separators(text)


def _clean_stem(stem: str) -> str:
    """Normalize and strip known tokens from filename stem."""
    s = _normalize_separators(stem)
    s = _strip_tokens(s)
    return s.strip()


def _title_from_cleaned(cleaned: str, year: int | None) -> str:
    """
    Derive title from cleaned stem. If year was found, take content before year
    and any trailing junk; otherwise use the whole cleaned string up to first
    obvious non-title token.
    """
    if not cleaned:
        return ""
    # If we have a year, try to truncate at year position to avoid suffix junk
    if year is not None:
        year_str = str(year)
        idx = cleaned.find(year_str)
        if idx > 0:
            cleaned = cleaned[:idx].strip()
    # Take first "segment" (avoid trailing single letters/numbers that are tags)
    parts = cleaned.split()
    if not parts:
        return ""
    # Drop trailing tokens that look like tags (single cap letter, short acronyms)
    while parts and len(parts[-1]) <= 3 and parts[-1].isalnum():
        parts.pop()
    return " ".join(parts).strip() or cleaned


def parse_path(file_path: Path) -> ParsedMovie:
    """
    Extract a best-guess movie title and optional year from a file path.
    Uses the file stem and parent folder name; strips common release tags.
    """
    path = Path(file_path)
    stem = path.stem
    parent_name = path.parent.name if path.parent else ""

    # Combined text: parent often has "Movie Title (Year)"
    combined = f"{parent_name} {stem}" if parent_name else stem
    year = _extract_year(combined)

    # Prefer parent folder if it looks like "Title (Year)" and filename is generic
    generic_names = {"movie", "film", "video", "untitled"}
    if (
        parent_name
        and stem.lower() in generic_names
        and YEAR_BRACKETS.search(parent_name)
    ):
        cleaned_parent = _clean_stem(parent_name)
        title = _title_from_cleaned(cleaned_parent, year)
        if title:
            return ParsedMovie(title=title, year=year)

    cleaned = _clean_stem(stem)
    title = _title_from_cleaned(cleaned, year)
    if not title and parent_name:
        cleaned_parent = _clean_stem(parent_name)
        title = _title_from_cleaned(cleaned_parent, year)
    if not title:
        title = cleaned or stem.replace(".", " ").strip() or "Unknown"
    return ParsedMovie(title=title, year=year)
