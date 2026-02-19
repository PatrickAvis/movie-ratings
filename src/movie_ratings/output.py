"""Export and display: CSV, JSON, console table, to_delete list."""

import csv
import json
from pathlib import Path

from .models import MovieRecord

try:
    from rich.console import Console
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def _record_to_row(rec: MovieRecord) -> dict:
    """One row for CSV/JSON export."""
    return {
        "path": str(rec.path),
        "parsed_title": rec.parsed_title,
        "parsed_year": rec.parsed_year,
        "imdb_id": rec.imdb_id,
        "title": rec.title,
        "year": rec.year,
        "imdb_rating": rec.imdb_rating,
        "imdb_votes": rec.imdb_votes,
        "genre": rec.genre,
        "runtime": rec.runtime,
        "verdict": rec.verdict,
        "reason": rec.reason,
    }


def export_csv(records: list[MovieRecord], path: Path) -> None:
    """Write records to CSV."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "path", "parsed_title", "parsed_year", "imdb_id", "title", "year",
        "imdb_rating", "imdb_votes", "genre", "runtime", "verdict", "reason",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for rec in records:
            row = _record_to_row(rec)
            row["path"] = str(rec.path)
            w.writerow(row)


def export_json(records: list[MovieRecord], path: Path) -> None:
    """Write records to JSON (list of dicts)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [_record_to_row(rec) for rec in records]
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _sorted_by_rating(records: list[MovieRecord], reverse: bool = True) -> list[MovieRecord]:
    """Sort by imdb_rating (None last when reverse=True)."""
    def key(r: MovieRecord) -> tuple[bool, float]:
        if r.imdb_rating is None:
            return (False, 0.0)
        return (True, r.imdb_rating)
    return sorted(records, key=key, reverse=reverse)


def print_console_table(
    records: list[MovieRecord],
    *,
    top_n: int | None = None,
    bottom_n: int | None = None,
) -> None:
    """Print a sortable table (Rich if available, else plain)."""
    sorted_records = _sorted_by_rating(records)
    if top_n is not None and top_n > 0:
        sorted_records = sorted_records[:top_n]
    elif bottom_n is not None and bottom_n > 0:
        sorted_records = _sorted_by_rating(records, reverse=False)[:bottom_n]
        sorted_records = list(reversed(sorted_records))

    if HAS_RICH:
        table = Table(title="Movie Ratings", show_header=True)
        table.add_column("Path", style="dim")
        table.add_column("Title")
        table.add_column("Year")
        table.add_column("Rating", justify="right")
        table.add_column("Votes", justify="right")
        table.add_column("Verdict")
        table.add_column("Reason", style="dim")
        for rec in sorted_records:
            rating = str(rec.imdb_rating) if rec.imdb_rating is not None else "—"
            votes = str(rec.imdb_votes) if rec.imdb_votes is not None else "—"
            year = rec.year or (str(rec.parsed_year) if rec.parsed_year else "—")
            title = rec.title or rec.parsed_title
            verdict_style = "green" if rec.verdict == "KEEP" else "red"
            table.add_row(
                str(rec.path),
                title,
                year,
                rating,
                votes,
                f"[{verdict_style}]{rec.verdict}[/]",
                rec.reason,
            )
        Console().print(table)
    else:
        print(f"{'Path':<50} {'Title':<30} {'Year':<6} {'Rating':<6} {'Votes':<8} {'Verdict':<8} {'Reason'}")
        print("-" * 130)
        for rec in sorted_records:
            rating = str(rec.imdb_rating) if rec.imdb_rating is not None else "—"
            votes = str(rec.imdb_votes) if rec.imdb_votes is not None else "—"
            year = rec.year or (str(rec.parsed_year) if rec.parsed_year else "—")
            title = (rec.title or rec.parsed_title)[:28]
            path_str = str(rec.path)
            if len(path_str) > 48:
                path_str = "..." + path_str[-45:]
            print(f"{path_str:<50} {title:<30} {year:<6} {rating:<6} {votes:<8} {rec.verdict:<8} {rec.reason}")


def write_to_delete(records: list[MovieRecord], path: Path, *, use_relative: bool = False, root: Path | None = None) -> None:
    """Write REMOVE file paths to a text file, one per line."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    remove = [r for r in records if r.verdict == "REMOVE"]
    lines = []
    for rec in remove:
        p = rec.path
        if use_relative and root is not None:
            try:
                p = rec.path.relative_to(root)
            except ValueError:
                pass
        lines.append(str(p))
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
