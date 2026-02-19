"""SQLite cache for OMDb API responses."""

import json
import sqlite3
from pathlib import Path


def _normalize_key(title: str, year: int | None) -> str:
    """Cache key: normalized title and year."""
    t = title.strip().lower().replace(" ", " ")
    y = str(year) if year is not None else ""
    return f"{t}|{y}"


def ensure_cache_dir(cache_path: Path) -> None:
    """Create parent directories for the cache file."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)


def get(cache_path: Path, title: str, year: int | None) -> dict | None:
    """
    Return cached OMDb response as dict, or None if missing.
    """
    key = _normalize_key(title, year)
    ensure_cache_dir(cache_path)
    with sqlite3.connect(cache_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS omdb_cache (
                cache_key TEXT PRIMARY KEY,
                response_json TEXT NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        row = conn.execute(
            "SELECT response_json FROM omdb_cache WHERE cache_key = ?",
            (key,),
        ).fetchone()
    if row is None:
        return None
    return json.loads(row[0])


def set(
    cache_path: Path,
    title: str,
    year: int | None,
    response: dict,
) -> None:
    """Store OMDb response in cache."""
    key = _normalize_key(title, year)
    ensure_cache_dir(cache_path)
    with sqlite3.connect(cache_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS omdb_cache (
                cache_key TEXT PRIMARY KEY,
                response_json TEXT NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO omdb_cache (cache_key, response_json, fetched_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (key, json.dumps(response)),
        )
