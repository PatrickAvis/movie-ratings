"""Tests for Pydantic models."""

import pytest
from pathlib import Path

from movie_ratings.models import ParsedMovie, OMDbMovie, MovieRecord


def test_parsed_movie():
    p = ParsedMovie(title="Inception", year=2010)
    assert p.title == "Inception"
    assert p.year == 2010
    p2 = ParsedMovie(title="Unknown", year=None)
    assert p2.year is None


def test_parsed_movie_year_range():
    with pytest.raises(ValueError):
        ParsedMovie(title="X", year=1800)
    with pytest.raises(ValueError):
        ParsedMovie(title="X", year=2100)


def test_omdb_na_rating_votes():
    data = {
        "imdbID": "tt1375666",
        "Title": "Inception",
        "Year": "2010",
        "imdbRating": "N/A",
        "imdbVotes": "N/A",
        "Genre": "Action, Sci-Fi",
        "Runtime": "148 min",
        "Response": "True",
    }
    m = OMDbMovie.model_validate(data)
    assert m.imdb_rating is None
    assert m.imdb_votes is None
    assert m.title == "Inception"
    assert m.runtime == 148


def test_omdb_comma_votes():
    data = {
        "imdbID": "tt1375666",
        "Title": "Inception",
        "Year": "2010",
        "imdbRating": "8.8",
        "imdbVotes": "2,345,678",
        "Genre": "Action",
        "Runtime": "148 min",
        "Response": "True",
    }
    m = OMDbMovie.model_validate(data)
    assert m.imdb_rating == 8.8
    assert m.imdb_votes == 2345678


def test_movie_record():
    r = MovieRecord(
        path=Path("/foo/movie.mkv"),
        parsed_title="Inception",
        parsed_year=2010,
        imdb_id="tt1375666",
        title="Inception",
        year="2010",
        imdb_rating=8.8,
        imdb_votes=1000,
        genre="Action",
        runtime=148,
        verdict="KEEP",
        reason="ok",
    )
    assert r.verdict == "KEEP"
    assert r.imdb_votes == 1000
