"""CLI for movie ratings scanner."""

from pathlib import Path

import typer

from .output import export_csv, export_json, print_console_table, write_to_delete
from .scanner import run_quarantine, run_scan
from .models import ScanConfig

app = typer.Typer(help="Scan movie files and get IMDb keep/remove recommendations via OMDb API.")


def _ext_callback(value: str) -> list[str]:
    return [x.strip().lstrip(".") for x in value.split(",") if x.strip()]


@app.command()
def main(
    root: Path = typer.Argument(..., help="Root directory to scan", path_type=Path),
    ext: str = typer.Option(
        "mkv,mp4,avi,m4v,mov,iso",
        "--ext",
        help="Comma-separated file extensions",
    ),
    threshold: float = typer.Option(7.0, "--threshold", help="Keep if imdb_rating >= this"),
    min_votes: int = typer.Option(0, "--min-votes", help="Keep only if imdb_votes >= this"),
    cache: Path = typer.Option(
        Path(".cache/imdb_cache.db"),
        "--cache",
        help="SQLite cache path",
        path_type=Path,
    ),
    refresh: bool = typer.Option(False, "--refresh", help="Ignore cache and re-fetch"),
    export_csv_path: Path = typer.Option(
        Path("./movie_ratings.csv"),
        "--export-csv",
        help="CSV output path",
        path_type=Path,
    ),
    export_json_path: Path | None = typer.Option(
        None,
        "--export-json",
        help="Optional JSON export path",
        path_type=Path,
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not move or delete anything"),
    quarantine: Path | None = typer.Option(
        None,
        "--quarantine",
        help="Move REMOVE files here (preserve relative paths)",
        path_type=Path,
    ),
    print_top: int | None = typer.Option(None, "--print-top", help="Print top N by rating"),
    print_bottom: int | None = typer.Option(None, "--print-bottom", help="Print bottom N by rating"),
    exclude_regex: str | None = typer.Option(None, "--exclude-regex", help="Regex to exclude paths"),
    include_regex: str | None = typer.Option(None, "--include-regex", help="Regex to include (only matching paths)"),
    to_delete: Path | None = typer.Option(
        None,
        "--to-delete",
        help="Write REMOVE file list to this path (e.g. to_delete.txt)",
        path_type=Path,
    ),
) -> None:
    """Scan directory for movies, lookup IMDb ratings via OMDb API, output keep/remove report."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    extensions = _ext_callback(ext)
    config = ScanConfig(
        root=root,
        extensions=extensions,
        threshold=threshold,
        min_votes=min_votes,
        cache_path=cache,
        refresh=refresh,
        export_csv=export_csv_path,
        export_json=export_json_path,
        dry_run=dry_run,
        quarantine=quarantine,
        print_top=print_top,
        print_bottom=print_bottom,
        exclude_regex=exclude_regex,
        include_regex=include_regex,
        to_delete=to_delete,
    )

    typer.echo("Scanning and fetching ratings...")
    records = run_scan(config)
    typer.echo(f"Found {len(records)} movie(s).")

    export_csv(records, config.export_csv)
    typer.echo(f"Report saved to CSV: {config.export_csv.resolve()}")

    if config.export_json is not None:
        export_json(records, config.export_json)
        typer.echo(f"JSON written to {config.export_json}")

    print_console_table(
        records,
        top_n=config.print_top,
        bottom_n=config.print_bottom,
    )

    if config.to_delete is not None:
        write_to_delete(records, config.to_delete, use_relative=True, root=config.root)
        typer.echo(f"REMOVE list written to {config.to_delete}")

    if config.quarantine is not None:
        if config.dry_run:
            typer.echo("Dry run: quarantine moves skipped.")
        else:
            run_quarantine(records, config.root, config.quarantine, dry_run=False)
            typer.echo(f"REMOVE files moved to {config.quarantine}")


def run_cli() -> None:
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    run_cli()
