"""OMDb API client with rate limiting and optional cache."""

import os
import time
import httpx

from .cache import get as cache_get, set as cache_set
from .models import OMDbMovie

OMDB_BASE = "https://www.omdbapi.com/"
DEFAULT_DELAY_SECONDS = 1.0
DEFAULT_TIMEOUT = 15.0


def get_api_key() -> str:
    """Read OMDb API key from OMDB_API_KEY env (or .env via dotenv in CLI)."""
    key = os.environ.get("OMDB_API_KEY", "").strip()
    if not key:
        raise ValueError(
            "OMDB_API_KEY is not set. Get a free key at https://www.omdbapi.com/apikey.aspx"
        )
    return key


def fetch_movie(
    title: str,
    year: int | None = None,
    *,
    api_key: str | None = None,
    cache_path: str | None = None,
    refresh: bool = False,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
) -> OMDbMovie | None:
    """
    Fetch movie by title (and optional year). Uses cache unless refresh=True.
    Returns None if not found or on error. Respects rate limit with delay.
    """
    from pathlib import Path

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

    params = {"apikey": key, "t": title}
    if year is not None:
        params["y"] = str(year)

    time.sleep(delay_seconds)
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        resp = client.get(OMDB_BASE, params=params)
        if resp.status_code == 429:
            time.sleep(2.0)
            resp = client.get(OMDB_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

    if data.get("Response") == "False":
        if cache_path_p:
            cache_set(cache_path_p, title, year, data)
        return None

    if cache_path_p:
        cache_set(cache_path_p, title, year, data)

    return OMDbMovie.model_validate(data)
