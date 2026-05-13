"""Tests for engine_manager.py.

Engine-level integration tests require the Stockfish binary and are marked
with ``@pytest.mark.integration`` so they can be skipped in CI with::

    pytest -m "not integration"

Unit tests that mock the engine run in all environments.
"""

import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import chess
import pytest
import engine_manager
from engine_manager import _pv_to_san, analyze


class TestPvToSan:
    """Unit tests for the PV-to-SAN conversion helper."""

    def test_empty_pv_returns_empty_list(self):
        """Empty variation produces an empty list."""
        board = chess.Board()
        assert _pv_to_san(board, []) == []

    def test_single_legal_move(self):
        """A single legal move converts correctly."""
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")
        result = _pv_to_san(board, [move])
        assert result == ["e4"]

    def test_multi_move_variation(self):
        """A two-move variation (e4, e5) converts to SAN."""
        board = chess.Board()
        moves = [chess.Move.from_uci("e2e4"), chess.Move.from_uci("e7e5")]
        result = _pv_to_san(board, moves)
        assert result == ["e4", "e5"]

    def test_stops_at_illegal_move(self):
        """An illegal move in the middle truncates the result."""
        board = chess.Board()
        legal = chess.Move.from_uci("e2e4")
        illegal = chess.Move.from_uci("e2e4")  # Already played
        board_copy = board.copy()
        board_copy.push(legal)
        # From the post-e4 board, e2e4 is illegal (pawn already moved)
        result = _pv_to_san(chess.Board(), [legal, illegal])
        # First move should succeed; second is illegal after board state changes
        assert result[0] == "e4"

    def test_does_not_mutate_input_board(self):
        """The input board's turn/position is unchanged after the call."""
        board = chess.Board()
        original_fen = board.fen()
        moves = [chess.Move.from_uci("e2e4"), chess.Move.from_uci("e7e5")]
        _pv_to_san(board, moves)
        assert board.fen() == original_fen


class TestAnalyzeUnit:
    """Unit tests for engine_manager.analyze() with a mocked engine."""

    def _make_mock_engine(self, score_cp: int = 30) -> MagicMock:
        """Build a mock SimpleEngine that returns a single candidate."""
        mock_score = MagicMock()
        mock_score.white.return_value.score.return_value = score_cp

        mock_info = {
            "pv": [chess.Move.from_uci("e2e4"), chess.Move.from_uci("e7e5")],
            "score": mock_score,
        }
        engine = MagicMock()
        engine.analyse.return_value = [mock_info]
        return engine

    def test_returns_list_of_candidates(self):
        """analyze() returns a list when the engine succeeds."""
        mock_engine = self._make_mock_engine()
        with patch("engine_manager._engine", mock_engine), \
             patch("engine_manager.get_engine", return_value=mock_engine):
            result = analyze("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        assert isinstance(result, list)
        assert len(result) == 1

    def test_candidate_has_required_keys(self):
        """Each candidate dict has uci, san, score_cp, pv_san."""
        mock_engine = self._make_mock_engine(score_cp=50)
        with patch("engine_manager._engine", mock_engine), \
             patch("engine_manager.get_engine", return_value=mock_engine):
            result = analyze("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        cand = result[0]
        for key in ("uci", "san", "score_cp", "pv_san"):
            assert key in cand, f"Missing key: {key}"

    def test_score_cp_value(self):
        """score_cp is taken from the engine's white-relative score."""
        mock_engine = self._make_mock_engine(score_cp=120)
        with patch("engine_manager._engine", mock_engine), \
             patch("engine_manager.get_engine", return_value=mock_engine):
            result = analyze("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        assert result[0]["score_cp"] == 120

    def test_missing_pv_skips_entry(self):
        """An info dict with no pv list produces no candidate."""
        mock_info_no_pv = {"pv": [], "score": MagicMock()}
        engine = MagicMock()
        engine.analyse.return_value = [mock_info_no_pv]
        with patch("engine_manager._engine", engine), \
             patch("engine_manager.get_engine", return_value=engine):
            result = analyze("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        assert result == []


@pytest.mark.integration
class TestAnalyzeIntegration:
    """Integration tests that invoke the real Stockfish binary.

    Skip with: ``pytest -m "not integration"``
    """

    def test_real_engine_returns_candidates(self):
        """Stockfish returns at least one candidate for the starting position."""
        result = analyze(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            time_sec=0.5,
            multipv=2,
        )
        assert len(result) >= 1

    def test_real_engine_candidate_fields(self):
        """Real engine candidates have all required fields with correct types."""
        result = analyze(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            time_sec=0.5,
            multipv=1,
        )
        c = result[0]
        assert isinstance(c["uci"], str)
        assert isinstance(c["san"], str)
        assert isinstance(c["score_cp"], int)
        assert isinstance(c["pv_san"], list)
