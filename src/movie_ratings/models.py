"""Pydantic models for parsed data, API responses, and output records."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ParsedMovie(BaseModel):
    """Result of filename parsing: title and optional year."""

    title: str = Field(..., min_length=1)
    year: int | None = None

    @field_validator("title")
    @classmethod
    def title_stripped(cls, v: str) -> str:
        return v.strip()

    @field_validator("year")
    @classmethod
    def year_range(cls, v: int | None) -> int | None:
        if v is not None and not (1888 <= v <= 2030):
            raise ValueError("year must be between 1888 and 2030")
        return v


def _na_to_none(s: str | None) -> str | None:
    if s is None or (isinstance(s, str) and s.upper() in ("N/A", "NA", "")):
        return None
    return s


def _parse_rating(s: str | None) -> float | None:
    s = _na_to_none(s)
    if s is None:
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _parse_votes(s: str | None) -> int | None:
    s = _na_to_none(s)
    if s is None:
        return None
    try:
        return int(s.replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _parse_runtime_minutes(s: str | None) -> int | None:
    s = _na_to_none(s)
    if s is None:
        return None
    s = s.strip().upper().removesuffix(" MIN")
    try:
        return int(s) if s.isdigit() else None
    except (TypeError, ValueError):
        return None


class OMDbMovie(BaseModel):
    """OMDb API response with normalized rating/votes and N/A handling."""

    imdb_id: str | None = Field(None, alias="imdbID")
    title: str | None = Field(None, alias="Title")
    year: str | None = Field(None, alias="Year")
    imdb_rating: float | None = Field(None, alias="imdbRating")
    imdb_votes: int | None = Field(None, alias="imdbVotes")
    genre: str | None = Field(None, alias="Genre")
    runtime: int | None = Field(None, alias="Runtime")
    response: str | None = Field(None, alias="Response")

    model_config = {"populate_by_name": True}

    @field_validator("imdb_rating", mode="before")
    @classmethod
    def normalize_rating(cls, v: str | float | None) -> float | None:
        return _parse_rating(v)

    @field_validator("imdb_votes", mode="before")
    @classmethod
    def normalize_votes(cls, v: str | int | None) -> int | None:
        return _parse_votes(v)

    @field_validator("runtime", mode="before")
    @classmethod
    def normalize_runtime(cls, v: str | int | None) -> int | None:
        if isinstance(v, int):
            return v
        return _parse_runtime_minutes(v)

    @field_validator("title", "year", "genre", mode="before")
    @classmethod
    def na_to_none_str(cls, v: str | None) -> str | None:
        return _na_to_none(v)


class MovieRecord(BaseModel):
    """Final output record: file path, parsed/API data, verdict and reason."""

    path: Path
    parsed_title: str
    parsed_year: int | None
    imdb_id: str | None = None
    title: str | None = None
    year: str | None = None
    imdb_rating: float | None = None
    imdb_votes: int | None = None
    genre: str | None = None
    runtime: int | None = None
    verdict: Literal["KEEP", "REMOVE"]
    reason: str

    class Config:
        arbitrary_types_allowed = True


class ScanConfig(BaseModel):
    """CLI/config: root, extensions, thresholds, paths."""

    root: Path
    extensions: list[str] = Field(default_factory=lambda: ["mkv", "mp4", "avi", "m4v", "mov", "iso"])
    threshold: float = 7.0
    min_votes: int = 0
    cache_path: Path = Field(default_factory=lambda: Path(".cache/imdb_cache.db"))
    refresh: bool = False
    export_csv: Path = Field(default_factory=lambda: Path("./movie_ratings.csv"))
    export_json: Path | None = None
    dry_run: bool = False
    quarantine: Path | None = None
    print_top: int | None = None
    print_bottom: int | None = None
    exclude_regex: str | None = None
    include_regex: str | None = None
    to_delete: Path | None = None

    class Config:
        arbitrary_types_allowed = True
