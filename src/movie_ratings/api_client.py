"""OMDb API client with rate limiting, exponential backoff, and optional cache."""

import asyncio
import os
import time
from pathlib import Path

import httpx

from .cache import get as cache_get, set as cache_set
from .models import OMDbMovie

OMDB_BASE = "https://www.omdbapi.com/"
DEFAULT_DELAY_SECONDS = 1.0
DEFAULT_TIMEOUT = 15.0
MAX_RETRIES = 5
BASE_BACKOFF = 2.0


def get_api_key() -> str:
    """Read OMDb API key from OMDB_API_KEY env (or .env via dotenv in CLI)."""
    key = os.environ.get("OMDB_API_KEY", "").strip()
    if not key:
        raise ValueError(
            "OMDB_API_KEY is not set. Get a free key at https://www.omdbapi.com/apikey.aspx"
        )
    return key


def _parse_response(data: dict, cache_path: Path | None, title: str, year: int | None) -> OMDbMovie | None:
    """Cache and parse a raw OMDb JSON response. Returns None if not found."""
    if cache_path:
        cache_set(cache_path, title, year, data)
    if data.get("Response") == "False":
        return None
    return OMDbMovie.model_validate(data)


def fetch_movie(
    title: str,
    year: int | None = None,
    *,
    api_key: str | None = None,
    cache_path: Path | str | None = None,
    refresh: bool = False,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
) -> OMDbMovie | None:
    """
    Fetch movie by title (and optional year). Uses cache unless refresh=True.
    Returns None if not found or on error. Uses exponential backoff on 429.
    """
    key = api_key or get_api_key()
    title = title.strip()
    if not title:
        return None

    cache_path_p = Path(cache_path) if cache_path else None
    if not refresh and cache_path_p:
        cached = cache_get(cache_path_p, title, year)
        if cached is not None:
            if cached.get("Response") == "False":
                return None
            try:
                return OMDbMovie.model_validate(cached)
            except Exception:
                pass

    params: dict[str, str] = {"apikey": key, "t": title}
    if year is not None:
        params["y"] = str(year)

    time.sleep(delay_seconds)
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        for attempt in range(MAX_RETRIES):
            resp = client.get(OMDB_BASE, params=params)
            if resp.status_code != 429:
                break
            time.sleep(BASE_BACKOFF * (2 ** attempt))
        resp.raise_for_status()

    return _parse_response(resp.json(), cache_path_p, title, year)


async def fetch_movie_async(
    title: str,
    year: int | None = None,
    *,
    api_key: str | None = None,
    cache_path: Path | str | None = None,
    refresh: bool = False,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
) -> OMDbMovie | None:
    """
    Async fetch movie by title (and optional year). Uses cache unless refresh=True.
    Returns None if not found or on error. Uses exponential backoff on 429.
    """
    key = api_key or get_api_key()
    title = title.strip()
    if not title:
        return None

    cache_path_p = Path(cache_path) if cache_path else None
    if not refresh and cache_path_p:
        cached = cache_get(cache_path_p, title, year)
        if cached is not None:
            if cached.get("Response") == "False":
                return None
            try:
                return OMDbMovie.model_validate(cached)
            except Exception:
                pass

    params: dict[str, str] = {"apikey": key, "t": title}
    if year is not None:
        params["y"] = str(year)

    await asyncio.sleep(delay_seconds)
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        for attempt in range(MAX_RETRIES):
            resp = await client.get(OMDB_BASE, params=params)
            if resp.status_code != 429:
                break
            await asyncio.sleep(BASE_BACKOFF * (2 ** attempt))
        resp.raise_for_status()

    return _parse_response(resp.json(), cache_path_p, title, year)
