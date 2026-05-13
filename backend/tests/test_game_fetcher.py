"""Tests for game_fetcher module."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date
from unittest.mock import patch, MagicMock
import pytest
import requests as req

from game_fetcher import (
    _month_range,
    _parse_result,
    _parse_color,
    _extract_eco,
    fetch_games,
)

# ---------------------------------------------------------------------------
# _month_range
# ---------------------------------------------------------------------------


class TestMonthRange:
    def test_single_month(self):
        assert _month_range(date(2024, 3, 1), date(2024, 3, 1)) == [(2024, 3)]

    def test_same_year_span(self):
        assert _month_range(date(2024, 1, 1), date(2024, 3, 1)) == [
            (2024, 1),
            (2024, 2),
            (2024, 3),
        ]

    def test_year_boundary_wrap(self):
        assert _month_range(date(2023, 11, 1), date(2024, 2, 1)) == [
            (2023, 11),
            (2023, 12),
            (2024, 1),
            (2024, 2),
        ]

    def test_single_day_in_month_still_included(self):
        pairs = _month_range(date(2024, 6, 15), date(2024, 6, 15))
        assert pairs == [(2024, 6)]


# ---------------------------------------------------------------------------
# _parse_result
# ---------------------------------------------------------------------------


def _game(white_result: str, black_result: str) -> dict:
    return {
        "white": {"username": "Alice", "result": white_result},
        "black": {"username": "Bob", "result": black_result},
    }


class TestParseResult:
    def test_win_as_white(self):
        assert _parse_result(_game("win", "checkmated"), "alice") == "win"

    def test_loss_as_white(self):
        assert _parse_result(_game("checkmated", "win"), "alice") == "loss"

    def test_stalemate_is_draw(self):
        assert _parse_result(_game("stalemate", "stalemate"), "alice") == "draw"

    def test_agreed_is_draw(self):
        assert _parse_result(_game("agreed", "agreed"), "alice") == "draw"

    def test_repetition_is_draw(self):
        assert _parse_result(_game("repetition", "repetition"), "alice") == "draw"

    def test_win_as_black(self):
        assert _parse_result(_game("checkmated", "win"), "bob") == "win"

    def test_loss_as_black(self):
        assert _parse_result(_game("win", "checkmated"), "bob") == "loss"

    def test_case_insensitive_username(self):
        assert _parse_result(_game("win", "checkmated"), "ALICE") == "win"


# ---------------------------------------------------------------------------
# _parse_color
# ---------------------------------------------------------------------------


class TestParseColor:
    def test_white_player(self):
        game = {"white": {"username": "Alice"}, "black": {"username": "Bob"}}
        assert _parse_color(game, "alice") == "white"

    def test_black_player(self):
        game = {"white": {"username": "Alice"}, "black": {"username": "Bob"}}
        assert _parse_color(game, "bob") == "black"


# ---------------------------------------------------------------------------
# _extract_eco
# ---------------------------------------------------------------------------


class TestExtractEco:
    def test_both_tags_present(self):
        pgn = '[ECO "B20"]\n[Opening "Sicilian Defense"]\n\n1. e4 c5'
        eco, name = _extract_eco(pgn)
        assert eco == "B20"
        assert name == "Sicilian Defense"

    def test_no_tags_returns_empty_strings(self):
        eco, name = _extract_eco("1. e4 e5")
        assert eco == ""
        assert name == ""

    def test_eco_only(self):
        eco, name = _extract_eco('[ECO "A00"]\n\n1. a3')
        assert eco == "A00"
        assert name == ""

    def test_opening_only(self):
        eco, name = _extract_eco('[Opening "English Opening"]\n\n1. c4')
        assert eco == ""
        assert name == "English Opening"


# ---------------------------------------------------------------------------
# fetch_games
# ---------------------------------------------------------------------------

_RAPID_GAME = {
    "url": "https://chess.com/game/1",
    "pgn": '[ECO "B20"]\n[Opening "Sicilian"]\n\n1. e4 c5 1-0',
    "time_class": "rapid",
    "rules": "chess",
    "white": {"username": "Alice", "rating": 1200, "result": "win"},
    "black": {"username": "Bob", "rating": 1100, "result": "checkmated"},
    "end_time": 1700000000,
}

_BLITZ_GAME = {**_RAPID_GAME, "time_class": "blitz", "url": "https://chess.com/game/2"}
_CHESS960_GAME = {**_RAPID_GAME, "rules": "chess960", "url": "https://chess.com/game/3"}


def _mock_get(games: list[dict]) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {"games": games}
    resp.raise_for_status.return_value = None
    return resp


class TestFetchGames:
    def test_returns_game_list(self):
        with patch("requests.get", return_value=_mock_get([_RAPID_GAME])):
            result = fetch_games("Alice", date(2024, 1, 1), date(2024, 1, 31))
        assert len(result) == 1
        g = result[0]
        assert g["color"] == "white"
        assert g["result"] == "win"
        assert g["eco"] == "B20"
        assert g["time_class"] == "rapid"

    def test_filters_by_time_class(self):
        with patch("requests.get", return_value=_mock_get([_RAPID_GAME, _BLITZ_GAME])):
            result = fetch_games("Alice", date(2024, 1, 1), date(2024, 1, 31), time_class="blitz")
        assert len(result) == 1
        assert result[0]["time_class"] == "blitz"

    def test_all_time_class_includes_both(self):
        with patch("requests.get", return_value=_mock_get([_RAPID_GAME, _BLITZ_GAME])):
            result = fetch_games("Alice", date(2024, 1, 1), date(2024, 1, 31), time_class="all")
        assert len(result) == 2

    def test_filters_non_chess_variants(self):
        with patch("requests.get", return_value=_mock_get([_CHESS960_GAME])):
            result = fetch_games("Alice", date(2024, 1, 1), date(2024, 1, 31))
        assert len(result) == 0

    def test_filters_by_color(self):
        black_game = {
            **_RAPID_GAME,
            "white": {"username": "Bob", "rating": 1100, "result": "checkmated"},
            "black": {"username": "Alice", "rating": 1200, "result": "win"},
            "url": "https://chess.com/game/4",
        }
        with patch("requests.get", return_value=_mock_get([_RAPID_GAME, black_game])):
            result = fetch_games("Alice", date(2024, 1, 1), date(2024, 1, 31), color="black")
        assert len(result) == 1
        assert result[0]["color"] == "black"

    def test_filters_by_result(self):
        loss_game = {
            **_RAPID_GAME,
            "white": {"username": "Alice", "rating": 1200, "result": "checkmated"},
            "black": {"username": "Bob", "rating": 1100, "result": "win"},
            "url": "https://chess.com/game/5",
        }
        with patch("requests.get", return_value=_mock_get([_RAPID_GAME, loss_game])):
            result = fetch_games("Alice", date(2024, 1, 1), date(2024, 1, 31), result="loss")
        assert len(result) == 1
        assert result[0]["result"] == "loss"

    def test_max_games_cap(self):
        games = [_RAPID_GAME] * 10
        with patch("requests.get", return_value=_mock_get(games)):
            result = fetch_games("Alice", date(2024, 1, 1), date(2024, 1, 31), max_games=3)
        assert len(result) == 3

    def test_network_error_raises_runtime_error(self):
        with patch("requests.get", side_effect=req.RequestException("timeout")):
            with pytest.raises(RuntimeError, match="Chess.com fetch failed"):
                fetch_games("Alice", date(2024, 1, 1), date(2024, 1, 31))

    def test_multiple_months_fetched(self):
        with patch("requests.get", return_value=_mock_get([])) as mock_get:
            fetch_games("Alice", date(2024, 1, 1), date(2024, 3, 31))
        assert mock_get.call_count == 3
