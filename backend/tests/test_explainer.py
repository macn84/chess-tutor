"""Tests for the explainer module (template-based move prose generation).

No engine or Flask server required — all tests use python-chess directly.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import chess
import pytest
from explainer import explain_move, _tag_move, _assemble_prose


class TestExplainMoveBookPriority:
    """Book explanations take precedence over template generation."""

    def test_returns_book_explanation_verbatim(self):
        """When book_explanation is supplied it is returned without modification."""
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")
        book_prose = "Controls the centre and opens lines for the bishop and queen."
        result = explain_move(board, move, book_explanation=book_prose)
        assert result == book_prose

    def test_ignores_template_when_book_provided(self):
        """Template logic is never invoked when book prose is present."""
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")
        result = explain_move(board, move, book_explanation="Custom prose.")
        assert "Custom prose." in result

    def test_falls_back_to_template_when_book_is_none(self):
        """No book explanation triggers template generation."""
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")
        result = explain_move(board, move, book_explanation=None)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_falls_back_to_template_when_book_is_empty_string(self):
        """Empty-string book explanation is falsy and triggers templates."""
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")
        result = explain_move(board, move, book_explanation="")
        # Template should produce something, not an empty string
        assert len(result) > 0


class TestTagMove:
    """Unit tests for _tag_move()."""

    def test_central_pawn_e4(self):
        """1.e4 is tagged central_pawn."""
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")
        tags = _tag_move(board, move)
        assert "central_pawn" in tags

    def test_central_pawn_d4(self):
        """1.d4 is tagged central_pawn."""
        board = chess.Board()
        move = chess.Move.from_uci("d2d4")
        tags = _tag_move(board, move)
        assert "central_pawn" in tags

    def test_knight_development_f3(self):
        """Nf3 is tagged develops_piece."""
        board = chess.Board()
        move = chess.Move.from_uci("g1f3")
        tags = _tag_move(board, move)
        assert "develops_piece" in tags

    def test_knight_development_c3(self):
        """Nc3 is tagged develops_piece."""
        board = chess.Board()
        move = chess.Move.from_uci("b1c3")
        tags = _tag_move(board, move)
        assert "develops_piece" in tags

    def test_capture_tag(self):
        """A capture is tagged captures_<piece>."""
        # Set up a position where White can capture the d5 pawn
        board = chess.Board("rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")
        move = chess.Move.from_uci("e4d5")
        tags = _tag_move(board, move)
        assert "captures_pawn" in tags

    def test_castling_tag(self):
        """Kingside castling is tagged castles."""
        # Position where White can castle kingside
        board = chess.Board("r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4")
        move = chess.Move.from_uci("e1g1")
        tags = _tag_move(board, move)
        assert "castles" in tags

    def test_gives_check_tag(self):
        """A move that gives check is tagged gives_check.

        Position: Black king on d8, White rook on e2, White king on e1.
        Re8+ checks via the 8th rank.
        """
        board = chess.Board("3k4/8/8/8/8/8/4R3/4K3 w - - 0 1")
        move = chess.Move.from_uci("e2e8")
        tags = _tag_move(board, move)
        assert "gives_check" in tags

    def test_no_piece_returns_empty(self):
        """A move from an empty square returns no tags."""
        board = chess.Board()
        # Manually create a move from an empty square
        move = chess.Move(chess.E3, chess.E4)
        tags = _tag_move(board, move)
        assert tags == []

    def test_controls_center_tag(self):
        """A move that attacks a central square is tagged controls_center."""
        board = chess.Board()
        move = chess.Move.from_uci("g1f3")  # Nf3 attacks e5
        tags = _tag_move(board, move)
        assert "controls_center" in tags


class TestAssembleProse:
    """Unit tests for _assemble_prose()."""

    def test_prose_ends_with_period(self):
        """All generated prose ends with a full stop."""
        board = chess.Board()
        for uci in ("e2e4", "d2d4", "g1f3", "b1c3"):
            move = chess.Move.from_uci(uci)
            tags = _tag_move(board, move)
            prose = _assemble_prose(board, move, tags)
            assert prose.endswith("."), f"Prose missing period: {prose!r}"

    def test_castling_prose_mentions_kingside(self):
        """Kingside castling prose contains 'kingside'."""
        board = chess.Board(
            "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
        )
        move = chess.Move.from_uci("e1g1")
        tags = _tag_move(board, move)
        prose = _assemble_prose(board, move, tags)
        assert "kingside" in prose.lower()

    def test_central_pawn_prose_mentions_center(self):
        """Central pawn push prose mentions the centre."""
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")
        tags = _tag_move(board, move)
        prose = _assemble_prose(board, move, tags)
        assert "center" in prose.lower() or "centre" in prose.lower()

    def test_development_prose_mentions_square(self):
        """Knight development prose names the destination square."""
        board = chess.Board()
        move = chess.Move.from_uci("g1f3")
        tags = _tag_move(board, move)
        prose = _assemble_prose(board, move, tags)
        assert "f3" in prose

    def test_empty_square_returns_empty_string(self):
        """Move from empty square produces empty prose."""
        board = chess.Board()
        move = chess.Move(chess.E3, chess.E4)
        tags = _tag_move(board, move)
        prose = _assemble_prose(board, move, tags)
        assert prose == ""
