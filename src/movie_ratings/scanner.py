"""Orchestration: scan directory, parse filenames, lookup OMDb, compute verdicts."""

import asyncio
import re
import shutil
from pathlib import Path

from .api_client import fetch_movie_async, get_api_key
from .models import MovieRecord, OMDbMovie, ParsedMovie, ScanConfig
from .parser import parse_path

DEFAULT_CONCURRENCY = 5


def _collect_files(root: Path, extensions: list[str]) -> list[Path]:
    """Recursively find files with given extensions under root."""
    exts = {e.lstrip(".").lower() for e in extensions}
    out = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lstrip(".").lower() in exts:
            out.append(p)
    return out


def _filter_paths(
    paths: list[Path],
    root: Path,
    exclude_pat: re.Pattern | None,
    include_pat: re.Pattern | None,
) -> list[Path]:
    """Apply compiled exclude/include patterns to relative paths."""
    if not exclude_pat and not include_pat:
        return paths
    result = []
    for p in paths:
        try:
            rel = p.relative_to(root)
        except ValueError:
            continue
        rel_str = str(rel).replace("\\", "/")
        if exclude_pat and exclude_pat.search(rel_str):
            continue
        if include_pat and not include_pat.search(rel_str):
            continue
        result.append(p)
    return result


def _verdict_and_reason(
    omdb: OMDbMovie | None,
    threshold: float,
    min_votes: int,
) -> tuple[str, str]:
    """Return (verdict, reason)."""
    if omdb is None:
        return "REMOVE", "not found"
    rating = omdb.imdb_rating
    votes = omdb.imdb_votes
    if rating is None and votes is None:
        return "REMOVE", "no rating/votes"
    if rating is None:
        return "REMOVE", "no rating"
    if votes is not None and votes < min_votes:
        return "REMOVE", f"votes {votes} < {min_votes}"
    if rating < threshold:
        return "REMOVE", f"rating {rating} < {threshold}"
    return "KEEP", "ok"


def _record(
    path: Path,
    parsed: ParsedMovie,
    omdb: OMDbMovie | None,
    threshold: float,
    min_votes: int,
) -> MovieRecord:
    verdict, reason = _verdict_and_reason(omdb, threshold, min_votes)
    size_gb = None
    try:
        if path.is_file():
            size_gb = round(path.stat().st_size / (1024**3), 2)
    except OSError:
        pass
    return MovieRecord(
        path=path,
        folder_path=path.parent,
        size_gb=size_gb,
        parsed_title=parsed.title,
        parsed_year=parsed.year,
        imdb_id=omdb.imdb_id if omdb else None,
        title=omdb.title if omdb else None,
        year=omdb.year if omdb else None,
        imdb_rating=omdb.imdb_rating if omdb else None,
        imdb_votes=omdb.imdb_votes if omdb else None,
        genre=omdb.genre if omdb else None,
        runtime=omdb.runtime if omdb else None,
        verdict=verdict,
        reason=reason,
    )


async def _run_scan_async(config: ScanConfig, api_key: str) -> list[MovieRecord]:
    root = config.root.resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Root is not a directory: {root}")

    paths = _collect_files(root, config.extensions)

    # Compile regexes once for the entire scan
    exclude_pat = re.compile(config.exclude_regex) if config.exclude_regex else None
    include_pat = re.compile(config.include_regex) if config.include_regex else None
    paths = _filter_paths(paths, root, exclude_pat, include_pat)

    semaphore = asyncio.Semaphore(DEFAULT_CONCURRENCY)

    async def fetch_one(path: Path) -> MovieRecord:
        parsed = parse_path(path)
        async with semaphore:
            omdb = await fetch_movie_async(
                parsed.title,
                parsed.year,
                api_key=api_key,
                cache_path=config.cache_path,
                refresh=config.refresh,
            )
        rec = _record(path, parsed, omdb, config.threshold, config.min_votes)
        title_display = parsed.title
        year_display = f" ({parsed.year})" if parsed.year else ""
        if omdb and omdb.imdb_rating is not None:
            rating_display = f" -> {omdb.imdb_rating} ({rec.verdict})"
        else:
            rating_display = " -> not found"
        folder = path.parent.name or "."
        print(f"  {folder} / {path.name} | {title_display}{year_display}{rating_display}")
        return rec

    records = await asyncio.gather(*[fetch_one(p) for p in paths])
    return list(records)


def run_scan(config: ScanConfig, api_key: str | None = None) -> list[MovieRecord]:
    """
    Scan root for movie files, parse titles, fetch OMDb data concurrently (with cache),
    and return list of MovieRecord with verdicts.
    """
    key = api_key or get_api_key()
    return asyncio.run(_run_scan_async(config, key))


def run_quarantine(
    records: list[MovieRecord],
    root: Path,
    quarantine_dir: Path,
    dry_run: bool,
) -> None:
    """
    Move REMOVE files into quarantine_dir preserving relative structure.
    If dry_run, no moves; caller may log intended moves.
    """
    root = root.resolve()
    quarantine_dir = quarantine_dir.resolve()
    for rec in records:
        if rec.verdict != "REMOVE":
            continue
        path = rec.path.resolve()
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        dest = quarantine_dir / rel
        if dry_run:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(dest))
