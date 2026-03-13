"""Extract movie title and year from file paths using guessit."""

from pathlib import Path

from guessit import guessit

from .models import ParsedMovie


def parse_path(file_path: Path) -> ParsedMovie:
    """
    Extract a best-guess movie title and optional year from a file path.
    Prefers the parent folder name for lookup (e.g. "Inception (2010)"); falls back to filename.
    """
    path = Path(file_path)
    parent_name = path.parent.name if path.parent and path.parent.name else ""

    # Prefer folder name — it's usually "Movie Title (Year)" and gives a cleaner title
    if parent_name:
        guess = guessit(parent_name)
        title = str(guess.get("title", "")).strip()
        year = guess.get("year")
        if title:
            return ParsedMovie(title=title, year=int(year) if year is not None else None)

    # Fall back to filename
    guess = guessit(str(path.name))
    title = str(guess.get("title", "")).strip()
    year = guess.get("year")
    if not title:
        title = path.stem.replace(".", " ").strip() or "Unknown"
    return ParsedMovie(title=title, year=int(year) if year is not None else None)
