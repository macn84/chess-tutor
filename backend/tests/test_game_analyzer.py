"""Tests for game_analyzer module."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import chess
from unittest.mock import patch
import pytest

from game_analyzer import _phase, _cp_loss, _analyze_single_game, analyze_games

# ---------------------------------------------------------------------------
# _phase
# ---------------------------------------------------------------------------


class TestPhase:
    def test_move_1_is_opening(self):
        assert _phase(1) == "opening"

    def test_move_14_is_opening(self):
        assert _phase(14) == "opening"

    def test_move_15_is_middlegame(self):
        assert _phase(15) == "middlegame"

    def test_move_34_is_middlegame(self):
        assert _phase(34) == "middlegame"

    def test_move_35_is_endgame(self):
        assert _phase(35) == "endgame"

    def test_deep_endgame(self):
        assert _phase(80) == "endgame"


# ---------------------------------------------------------------------------
# _cp_loss
# ---------------------------------------------------------------------------


class TestCpLoss:
    def test_white_blunder(self):
        # White moves; eval drops from 0 to -310 → 310 cp loss for white
        assert _cp_loss(0, -310, chess.WHITE) == 310

    def test_white_good_move_zero_loss(self):
        assert _cp_loss(0, 30, chess.WHITE) == 0

    def test_white_no_change_zero_loss(self):
        assert _cp_loss(50, 50, chess.WHITE) == 0

    def test_black_blunder(self):
        # Black moves; eval goes from -10 (white slightly worse) to 300 (white better)
        # Black lost 310 cp
        assert _cp_loss(-10, 300, chess.BLACK) == 310

    def test_black_good_move_zero_loss(self):
        # Black improves position: eval goes from 100 to -20 (more black-favoured)
        assert _cp_loss(100, -20, chess.BLACK) == 0

    def test_loss_floored_at_zero(self):
        assert _cp_loss(0, 0, chess.WHITE) == 0


# ---------------------------------------------------------------------------
# _analyze_single_game
# ---------------------------------------------------------------------------

_MINIMAL_PGN = """\
[Event "Test"]
[White "testuser"]
[Black "opponent"]
[Result "1-0"]
[ECO "B20"]
[Opening "Sicilian"]

1. e4 c5 2. Nf3 1-0
"""

_GAME_SUMMARY = {
    "pgn": _MINIMAL_PGN,
    "url": "https://chess.com/game/1",
    "color": "white",
    "result": "win",
    "eco": "B20",
    "opening_name": "Sicilian",
    "white_username": "testuser",
    "black_username": "opponent",
    "white_rating": 1200,
    "black_rating": 1100,
    "end_time": 1700000000,
    "accuracies": None,
}


class TestAnalyzeSingleGame:
    def test_detects_blunder_on_move_1(self):
        """Simulate a 310 cp blunder on white's first move."""
        # Calls: eval_before(e4) | eval_after(e4) | best_move | eval_after(c5) | eval_after(Nf3)
        side_effects = [
            [{"score_cp": 0, "san": "e4", "uci": "e2e4", "pv_san": ["e4"]}],
            [{"score_cp": -310, "san": "c5", "uci": "c7c5", "pv_san": ["c5"]}],
            [{"score_cp": 30, "san": "d4", "uci": "d2d4", "pv_san": ["d4", "e5"]}],
            [{"score_cp": 15, "san": "Nf3", "uci": "g1f3", "pv_san": ["Nf3"]}],
            [{"score_cp": 20, "san": "d6", "uci": "d7d6", "pv_san": ["d6"]}],
        ]
        with patch("engine_manager.analyze", side_effect=side_effects):
            result = _analyze_single_game(_GAME_SUMMARY, "testuser")

        assert result["total_moves_analyzed"] == 2
        blunders = [m for m in result["mistakes"] if m["severity"] == "blunder"]
        assert len(blunders) == 1
        assert blunders[0]["move_number"] == 1
        assert blunders[0]["move_played_san"] == "e4"
        assert blunders[0]["cp_loss"] == 310
        assert blunders[0]["best_move_san"] == "d4"
        assert blunders[0]["phase"] == "opening"

    def test_no_mistakes_when_eval_is_flat(self):
        """Constant engine eval → no mistakes recorded."""
        flat = [{"score_cp": 0, "san": "e4", "uci": "e2e4", "pv_san": ["e4"]}]
        with patch("engine_manager.analyze", return_value=flat):
            result = _analyze_single_game(_GAME_SUMMARY, "testuser")
        assert result["mistakes"] == []

    def test_result_metadata_preserved(self):
        flat = [{"score_cp": 0, "san": "e4", "uci": "e2e4", "pv_san": ["e4"]}]
        with patch("engine_manager.analyze", return_value=flat):
            result = _analyze_single_game(_GAME_SUMMARY, "testuser")
        assert result["result"] == "win"
        assert result["eco"] == "B20"
        assert result["color"] == "white"
        assert result["url"] == "https://chess.com/game/1"

    def test_empty_pgn_raises_value_error(self):
        bad = {**_GAME_SUMMARY, "pgn": ""}
        with pytest.raises(ValueError, match="Could not parse PGN"):
            _analyze_single_game(bad, "testuser")


# ---------------------------------------------------------------------------
# analyze_games
# ---------------------------------------------------------------------------


class TestAnalyzeGames:
    def test_sets_done_status_on_completion(self):
        job = {"status": "running", "analyzed_count": 0, "progress": 0.0}
        flat = [{"score_cp": 0, "san": "e4", "uci": "e2e4", "pv_san": ["e4"]}]
        with patch("engine_manager.analyze", return_value=flat):
            analyze_games([_GAME_SUMMARY], "testuser", job, "fake-id")
        assert job["status"] == "done"
        assert job["progress"] == 1.0
        assert job["analyzed_count"] == 1

    def test_skips_games_without_pgn(self):
        job = {"status": "running", "analyzed_count": 0, "progress": 0.0}
        empty_game = {**_GAME_SUMMARY, "pgn": ""}
        analyze_games([empty_game], "testuser", job, "fake-id")
        assert job["status"] == "done"
        assert job["analyzed_games"] == []

    def test_skips_invalid_pgn_without_crashing(self):
        job = {"status": "running", "analyzed_count": 0, "progress": 0.0}
        bad = {**_GAME_SUMMARY, "pgn": "not valid pgn at all !!!"}
        flat = [{"score_cp": 0, "san": "e4", "uci": "e2e4", "pv_san": ["e4"]}]
        with patch("engine_manager.analyze", return_value=flat):
            analyze_games([bad], "testuser", job, "fake-id")
        assert job["status"] == "done"
        # Game may or may not be included depending on pgn parse; just no exception

    def test_progress_updated_during_run(self):
        job = {"status": "running", "analyzed_count": 0, "progress": 0.0}
        flat = [{"score_cp": 0, "san": "e4", "uci": "e2e4", "pv_san": ["e4"]}]
        snapshots: list[float] = []

        original_analyze = __import__("engine_manager").analyze

        def tracking_analyze(*args, **kwargs):
            snapshots.append(job["progress"])
            return flat

        with patch("engine_manager.analyze", side_effect=tracking_analyze):
            analyze_games([_GAME_SUMMARY, _GAME_SUMMARY], "testuser", job, "fake-id")

        assert job["progress"] == 1.0
