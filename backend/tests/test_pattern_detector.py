"""Tests for pattern_detector module."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from pattern_detector import detect_patterns

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_BLUNDER = {
    "move_number": 12,
    "phase": "opening",
    "severity": "blunder",
    "move_played_san": "e4",
    "best_move_san": "d4",
    "best_pv_san": ["d4"],
    "cp_loss": 350,
    "fen_before": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -",
}

_MISTAKE = {**_BLUNDER, "severity": "mistake", "cp_loss": 180, "move_number": 20, "phase": "middlegame"}
_INACCURACY = {**_BLUNDER, "severity": "inaccuracy", "cp_loss": 60, "move_number": 30, "phase": "middlegame"}

_BASE_GAME = {
    "url": "https://chess.com/game/1",
    "eco": "B20",
    "opening_name": "Sicilian Defense",
    "color": "white",
    "result": "win",
    "white_username": "testuser",
    "black_username": "opponent",
    "white_rating": 1200,
    "black_rating": 1100,
    "end_time": 1700000000,
    "accuracies": None,
    "mistakes": [],
    "phase_mistakes": {"opening": 0, "middlegame": 0, "endgame": 0},
    "avg_cp_loss": 0.0,
    "total_moves_analyzed": 10,
}


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------


class TestEmptyGames:
    def test_empty_input_returns_zero_totals(self):
        result = detect_patterns([], "testuser")
        assert result["total_games"] == 0
        assert result["wins"] == 0
        assert result["losses"] == 0
        assert result["draws"] == 0

    def test_empty_input_preserves_username(self):
        result = detect_patterns([], "hikaru")
        assert result["username"] == "hikaru"

    def test_empty_input_empty_lists(self):
        result = detect_patterns([], "testuser")
        assert result["top_blunders"] == []
        assert result["opening_stats"] == []
        assert result["mistake_move_numbers"] == []


# ---------------------------------------------------------------------------
# Win / loss / draw counting
# ---------------------------------------------------------------------------


class TestResultCounting:
    def test_single_win(self):
        result = detect_patterns([_BASE_GAME], "testuser")
        assert result["wins"] == 1
        assert result["losses"] == 0
        assert result["draws"] == 0
        assert result["total_games"] == 1

    def test_mixed_results(self):
        games = [
            {**_BASE_GAME, "result": "win"},
            {**_BASE_GAME, "result": "loss"},
            {**_BASE_GAME, "result": "draw"},
        ]
        result = detect_patterns(games, "testuser")
        assert result["wins"] == 1
        assert result["losses"] == 1
        assert result["draws"] == 1


# ---------------------------------------------------------------------------
# Blunder / mistake aggregation
# ---------------------------------------------------------------------------


class TestSeverityAggregation:
    def test_blunder_counted(self):
        game = {**_BASE_GAME, "mistakes": [_BLUNDER], "avg_cp_loss": 35.0}
        result = detect_patterns([game], "testuser")
        assert result["blunders_per_game"] == 1.0
        assert result["severity_totals"]["blunder"] == 1

    def test_top_blunders_populated(self):
        game = {**_BASE_GAME, "mistakes": [_BLUNDER], "avg_cp_loss": 35.0}
        result = detect_patterns([game], "testuser")
        assert len(result["top_blunders"]) == 1
        assert result["top_blunders"][0]["cp_loss"] == 350

    def test_top_blunders_limited_to_5(self):
        blunders = [
            {**_BLUNDER, "cp_loss": 300 + i * 50, "move_number": i + 1}
            for i in range(8)
        ]
        game = {**_BASE_GAME, "mistakes": blunders, "avg_cp_loss": 50.0}
        result = detect_patterns([game], "testuser")
        assert len(result["top_blunders"]) == 5

    def test_top_blunders_sorted_by_cp_loss_descending(self):
        blunders = [
            {**_BLUNDER, "cp_loss": 300 + i * 50, "move_number": i + 1}
            for i in range(6)
        ]
        game = {**_BASE_GAME, "mistakes": blunders, "avg_cp_loss": 50.0}
        result = detect_patterns([game], "testuser")
        losses = [b["cp_loss"] for b in result["top_blunders"]]
        assert losses == sorted(losses, reverse=True)

    def test_no_blunders_in_top_blunders_when_none(self):
        game = {**_BASE_GAME, "mistakes": [_MISTAKE], "avg_cp_loss": 18.0}
        result = detect_patterns([game], "testuser")
        assert result["top_blunders"] == []


# ---------------------------------------------------------------------------
# Phase distribution
# ---------------------------------------------------------------------------


class TestPhaseDistribution:
    def test_phase_totals_sum_to_100(self):
        mistakes = [_BLUNDER, _MISTAKE, _INACCURACY]
        game = {**_BASE_GAME, "mistakes": mistakes, "avg_cp_loss": 30.0}
        result = detect_patterns([game], "testuser")
        total = sum(result["phase_distribution"].values())
        assert abs(total - 100.0) < 0.5

    def test_all_opening_mistakes(self):
        mistakes = [{**_BLUNDER, "move_number": i} for i in range(1, 4)]
        game = {**_BASE_GAME, "mistakes": mistakes, "avg_cp_loss": 35.0}
        result = detect_patterns([game], "testuser")
        assert result["phase_distribution"]["opening"] == 100.0
        assert result["phase_distribution"]["middlegame"] == 0
        assert result["phase_distribution"]["endgame"] == 0

    def test_no_mistakes_gives_zero_distribution(self):
        result = detect_patterns([_BASE_GAME], "testuser")
        assert result["phase_distribution"] == {"opening": 0, "middlegame": 0, "endgame": 0}


# ---------------------------------------------------------------------------
# Opening stats
# ---------------------------------------------------------------------------


class TestOpeningStats:
    def test_single_opening_computed(self):
        result = detect_patterns([_BASE_GAME], "testuser")
        assert len(result["opening_stats"]) == 1
        stat = result["opening_stats"][0]
        assert stat["eco"] == "B20"
        assert stat["games"] == 1
        assert stat["wins"] == 1
        assert stat["win_rate"] == 100.0

    def test_two_distinct_openings(self):
        london = {**_BASE_GAME, "eco": "D00", "opening_name": "London System"}
        result = detect_patterns([_BASE_GAME, london], "testuser")
        ecos = {s["eco"] for s in result["opening_stats"]}
        assert "B20" in ecos
        assert "D00" in ecos

    def test_avg_cp_loss_averaged_across_games(self):
        g1 = {**_BASE_GAME, "avg_cp_loss": 40.0}
        g2 = {**_BASE_GAME, "avg_cp_loss": 60.0}
        result = detect_patterns([g1, g2], "testuser")
        assert result["opening_stats"][0]["avg_cp_loss"] == 50.0


# ---------------------------------------------------------------------------
# Mistake move-number histogram
# ---------------------------------------------------------------------------


class TestMoveNumberHistogram:
    def test_most_common_move_number_first(self):
        m1 = {**_BLUNDER, "move_number": 5, "severity": "mistake", "cp_loss": 150}
        m2 = {**_BLUNDER, "move_number": 5, "severity": "inaccuracy", "cp_loss": 60}
        m3 = {**_BLUNDER, "move_number": 10, "severity": "inaccuracy", "cp_loss": 55}
        game = {**_BASE_GAME, "mistakes": [m1, m2, m3], "avg_cp_loss": 20.0}
        result = detect_patterns([game], "testuser")
        hist = result["mistake_move_numbers"]
        assert hist[0]["move_number"] == 5
        assert hist[0]["count"] == 2

    def test_histogram_limited_to_10(self):
        mistakes = [
            {**_BLUNDER, "move_number": i, "severity": "inaccuracy", "cp_loss": 55}
            for i in range(1, 20)
        ]
        game = {**_BASE_GAME, "mistakes": mistakes, "avg_cp_loss": 20.0}
        result = detect_patterns([game], "testuser")
        assert len(result["mistake_move_numbers"]) <= 10
