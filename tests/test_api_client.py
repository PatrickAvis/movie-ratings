"""Tests for OMDb API client (mocked)."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import httpx

from movie_ratings.api_client import fetch_movie, get_api_key


def test_get_api_key_missing(monkeypatch):
    monkeypatch.delenv("OMDB_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OMDB_API_KEY"):
        get_api_key()


def test_get_api_key_set(monkeypatch):
    monkeypatch.setenv("OMDB_API_KEY", "testkey")
    assert get_api_key() == "testkey"


@patch("movie_ratings.api_client.httpx.Client")
def test_fetch_movie_success(MockClient, tmp_path):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "imdbID": "tt1375666",
        "Title": "Inception",
        "Year": "2010",
        "imdbRating": "8.8",
        "imdbVotes": "2,000,000",
        "Genre": "Action, Sci-Fi",
        "Runtime": "148 min",
        "Response": "True",
    }
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    MockClient.return_value = mock_client

    with patch.dict("os.environ", {"OMDB_API_KEY": "testkey"}):
        result = fetch_movie(
            "Inception",
            2010,
            api_key="testkey",
            cache_path=str(tmp_path / "cache.db"),
            refresh=True,
            delay_seconds=0,
        )
    assert result is not None
    assert result.title == "Inception"
    assert result.imdb_rating == 8.8
    assert result.imdb_votes == 2000000


@patch("movie_ratings.api_client.httpx.Client")
def test_fetch_movie_not_found(MockClient, tmp_path):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"Response": "False", "Error": "Movie not found!"}
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    MockClient.return_value = mock_client

    with patch.dict("os.environ", {"OMDB_API_KEY": "testkey"}):
        result = fetch_movie(
            "NonexistentMovieXYZ",
            api_key="testkey",
            cache_path=str(tmp_path / "cache.db"),
            refresh=True,
            delay_seconds=0,
        )
    assert result is None
