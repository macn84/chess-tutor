"""Tests for the opening_book package (loader + FEN normalisation).

All tests are pure in-memory — no engine, no Flask server required.
"""

import sys
import os

# Allow importing from the backend directory without installing as a package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import opening_book
from opening_book.loader import _normalize_fen, _load, lookup, get_all_entries


class TestNormalizeFen:
    """Unit tests for the FEN normalisation helper."""

    def test_strips_halfmove_and_fullmove(self):
        """6-field FEN is trimmed to 4 fields."""
        full = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        assert _normalize_fen(full) == "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq -"

    def test_already_four_fields_unchanged(self):
        """4-field FEN is returned as-is."""
        four = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq -"
        assert _normalize_fen(four) == four

    def test_handles_en_passant_square(self):
        """En-passant square in field 4 is preserved."""
        fen = "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3"
        assert _normalize_fen(fen).endswith("d6")

    def test_start_position(self):
        """Starting position normalises correctly."""
        start = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = _normalize_fen(start)
        assert result == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -"
        assert len(result.split()) == 4


class TestLookup:
    """Integration tests for opening_book.lookup()."""

    def test_starting_position_found(self):
        """Starting position is present in the book."""
        start_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        entry = lookup(start_fen)
        assert entry is not None

    def test_starting_position_has_required_fields(self):
        """Starting-position entry contains all expected keys."""
        start_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        entry = lookup(start_fen)
        for key in ("eco", "opening_name", "strategic_ideas", "candidate_explanations"):
            assert key in entry, f"Missing key: {key}"

    def test_unknown_position_returns_none(self):
        """A random mid-game position not in the book returns None."""
        random_fen = "r1bqk2r/pp3ppp/2nbpn2/3p4/3P4/2N1PN2/PPP1BPPP/R1BQK2R w KQkq - 0 8"
        assert lookup(random_fen) is None

    def test_lookup_is_transposition_safe(self):
        """Same position reached by different move orders hits the same entry.

        After 1.e4 the FEN has different half-move/full-move counters than the
        raw book key, but normalisation should match both.
        """
        # FEN after 1.e4 (full 6-field)
        after_e4_full = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        # Same position stripped to 4 fields (as stored in the book)
        after_e4_short = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3"
        assert lookup(after_e4_full) == lookup(after_e4_short)

    def test_returns_dict(self):
        """Successful lookup returns a plain dict."""
        start_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        entry = lookup(start_fen)
        assert isinstance(entry, dict)


class TestGetAllEntries:
    """Tests for get_all_entries()."""

    def test_returns_list(self):
        """get_all_entries returns a list."""
        entries = get_all_entries()
        assert isinstance(entries, list)

    def test_non_empty(self):
        """Book has at least one entry."""
        assert len(get_all_entries()) > 0

    def test_all_entries_have_fen_key(self):
        """Every entry in the book has a ``fen_key`` field."""
        for entry in get_all_entries():
            assert "fen_key" in entry
