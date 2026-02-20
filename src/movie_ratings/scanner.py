"""Orchestration: scan directory, parse filenames, lookup OMDb, compute verdicts."""

import re
import shutil
from pathlib import Path

from .api_client import fetch_movie, get_api_key
from .models import MovieRecord, OMDbMovie, ParsedMovie, ScanConfig
from .parser import parse_path


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
    exclude_regex: str | None,
    include_regex: str | None,
) -> list[Path]:
    """Apply exclude/include regex to relative paths."""
    if not exclude_regex and not include_regex:
        return paths
    exclude = re.compile(exclude_regex) if exclude_regex else None
    include = re.compile(include_regex) if include_regex else None
    result = []
    for p in paths:
        try:
            rel = p.relative_to(root)
        except ValueError:
            continue
        rel_str = str(rel).replace("\\", "/")
        if exclude and exclude.search(rel_str):
            continue
        if include and not include.search(rel_str):
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
    return MovieRecord(
        path=path,
        folder_path=path.parent,
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


def run_scan(config: ScanConfig, api_key: str | None = None) -> list[MovieRecord]:
    """
    Scan root for movie files, parse titles, fetch OMDb data (with cache),
    and return list of MovieRecord with verdicts.
    """
    root = config.root.resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Root is not a directory: {root}")

    key = api_key or get_api_key()
    paths = _collect_files(root, config.extensions)
    paths = _filter_paths(
        paths,
        root,
        config.exclude_regex,
        config.include_regex,
    )
    records = []
    for path in paths:
        parsed = parse_path(path)
        omdb = fetch_movie(
            parsed.title,
            parsed.year,
            api_key=key,
            cache_path=str(config.cache_path),
            refresh=config.refresh,
        )
        rec = _record(
            path,
            parsed,
            omdb,
            config.threshold,
            config.min_votes,
        )
        records.append(rec)
        # Show progress: folder / filename -> parsed title (year) -> rating or not found
        title_display = parsed.title
        year_display = f" ({parsed.year})" if parsed.year else ""
        if omdb and omdb.imdb_rating is not None:
            rating_display = f" -> {omdb.imdb_rating} ({rec.verdict})"
        else:
            rating_display = " -> not found"
        folder = path.parent.name or "."
        file_display = f"{folder} / {path.name}"
        print(f"  {file_display} | {title_display}{year_display}{rating_display}")
    return records


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
