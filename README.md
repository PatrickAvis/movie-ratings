# Movie Ratings Scanner

A Python 3.12 CLI that scans a directory of movie files, looks up IMDb ratings via the **OMDb API** (no scraping), and produces **keep vs remove** recommendations based on a configurable rating threshold.

## Features

- Recursively finds movie files (mkv, mp4, avi, m4v, mov, iso by default)
- Extracts best-guess **title** and **year** from filenames and folder names
- Queries **OMDb API** for `imdbRating`, `imdbVotes`, Genre, Runtime
- **SQLite cache** so repeated runs don’t re-query the same movie
- **CSV** and optional **JSON** export
- **Console table** (Rich) with sortable output; optional `--print-top N` / `--print-bottom N`
- **KEEP/REMOVE** verdict from `--threshold` and `--min-votes`
- Optional **to_delete.txt** list of REMOVE paths
- Optional **quarantine** folder: move REMOVE files there (preserve relative paths)
- **Dry-run** mode: no moves or deletes

## Setup

1. **Python 3.12+**

2. **Install**

   ```bash
   pip install -e .
   # or
   pip install -r requirements.txt
   ```

3. **API key**

   - Get a free key: [OMDb API Key](https://www.omdbapi.com/apikey.aspx)
   - Free tier: 1,000 requests per day; the app uses a 1 s delay between requests to stay within limits.
   - Set in environment or `.env`:

   ```bash
   cp .env.example .env
   # Edit .env and set OMDB_API_KEY=your_key
   ```

## Usage

```bash
# Basic: scan a folder, default threshold 7.0
python -m movie_ratings /path/to/movies

# Stricter: keep only if rating >= 7.5 and votes >= 1000
python -m movie_ratings /path/to/movies --threshold 7.5 --min-votes 1000

# Export CSV and JSON
python -m movie_ratings /path/to/movies --export-csv report.csv --export-json report.json

# Print only top 10 by rating
python -m movie_ratings /path/to/movies --print-top 10

# Write REMOVE list and move those files to a quarantine folder (dry-run first)
python -m movie_ratings /path/to/movies --to-delete to_delete.txt --quarantine ./quarantine --dry-run
python -m movie_ratings /path/to/movies --to-delete to_delete.txt --quarantine ./quarantine

# Ignore cache and re-fetch all
python -m movie_ratings /path/to/movies --refresh

# Filter paths
python -m movie_ratings /path/to/movies --exclude-regex "sample|trailer"
python -m movie_ratings /path/to/movies --include-regex "\.mkv$"
```

## CLI Reference

| Option | Default | Description |
|--------|---------|-------------|
| `root` | (required) | Root directory to scan |
| `--ext` | mkv,mp4,avi,m4v,mov,iso | Comma-separated extensions |
| `--threshold` | 7.0 | Keep if imdb_rating >= this |
| `--min-votes` | 0 | Keep only if imdb_votes >= this |
| `--cache` | .cache/imdb_cache.db | SQLite cache path |
| `--refresh` | false | Ignore cache |
| `--export-csv` | ./movie_ratings.csv | CSV output path |
| `--export-json` | (none) | Optional JSON path |
| `--dry-run` | false | No move/delete |
| `--quarantine` | (none) | Move REMOVE files here |
| `--print-top` | (none) | Print top N by rating |
| `--print-bottom` | (none) | Print bottom N by rating |
| `--exclude-regex` | (none) | Exclude paths matching regex |
| `--include-regex` | (none) | Include only paths matching regex |
| `--to-delete` | (none) | Write REMOVE list to file |

## Filename parsing

The parser:

- Detects years like `(1999)`, `[1999]`, or `1999` in filenames and parent folders
- Strips resolution (720p, 1080p, 4K), codecs (x264, HEVC), source (BluRay, WEB-DL), audio (DTS, 5.1), release tags (REPACK, PROPER), and group names
- Treats dots and underscores as spaces
- Uses parent folder name when the filename is generic (e.g. `movie.mkv` in `Inception (2010)/`)

## Development

```bash
pip install -e ".[dev]"
pytest tests -v
```

## Architecture at a glance

For newcomers, the key modules are:

- `src/movie_ratings/cli.py`: CLI entrypoint and option parsing (Typer).
- `src/movie_ratings/scanner.py`: orchestration pipeline (discover files -> parse -> fetch -> verdict).
- `src/movie_ratings/parser.py`: filename/folder parsing heuristics for title/year extraction.
- `src/movie_ratings/api_client.py`: OMDb HTTP calls, retry, and cache integration.
- `src/movie_ratings/cache.py`: SQLite cache read/write helpers.
- `src/movie_ratings/models.py`: Pydantic models and normalization/validation.
- `src/movie_ratings/output.py`: CSV/JSON export, console table printing, remove-list output.

Typical data flow:

1. Parse CLI args into `ScanConfig`.
2. Collect candidate files by extension.
3. Parse each path into `(title, year)`.
4. Query OMDb (or cache hit) for metadata.
5. Compute KEEP/REMOVE verdict from threshold + votes.
6. Export and print reports; optionally write or move REMOVE files.

## License

MIT.
