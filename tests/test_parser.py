"""Tests for filename parser."""

import pytest
from pathlib import Path

from movie_ratings.parser import parse_path
from movie_ratings.models import ParsedMovie


def test_inception_style():
    p = parse_path(Path("Inception.2010.1080p.BluRay.x264.mkv"))
    assert p.title == "Inception"
    assert p.year == 2010


def test_year_in_brackets():
    p = parse_path(Path("The Matrix (1999).mkv"))
    assert p.year == 1999
    assert "Matrix" in p.title


def test_year_in_square_brackets():
    p = parse_path(Path("Movie.Name[2001].avi"))
    assert p.year == 2001


def test_parent_folder_fallback():
    # movie.mkv inside "Inception (2010)/" -> use folder
    p = parse_path(Path("Inception (2010)/movie.mkv"))
    assert p.year == 2010
    assert "Inception" in p.title


def test_2001_space_odyssey():
    # Year-like number in title should not break; we take first year or title
    p = parse_path(Path("2001 A Space Odyssey (1968).mkv"))
    assert p.year == 1968
    assert "2001" in p.title or "Space" in p.title


def test_dots_underscores_as_spaces():
    p = parse_path(Path("Spider.Man.Far.From.Home.2019.1080p.mkv"))
    assert p.year == 2019
    assert "Spider" in p.title and "Home" in p.title


def test_returns_parsed_movie():
    p = parse_path(Path("Anything.2020.mkv"))
    assert isinstance(p, ParsedMovie)
    assert p.title
    assert p.year == 2020
