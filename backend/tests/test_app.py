"""Flask route tests for the Chess Tutor API.

Uses Flask's built-in test client and mocks ``engine_manager.analyze`` so
no Stockfish binary is needed during CI.
"""

import sys
import os
import json
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app import app

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
AFTER_E4_FEN = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"

# Minimal engine result stubbed for all analyse() calls
_MOCK_CANDIDATES = [
    {
        "uci": "g1f3",
        "san": "Nf3",
        "score_cp": 30,
        "pv_san": ["Nf3", "Nc6", "Bb5"],
    },
    {
        "uci": "e2e4",
        "san": "e4",
        "score_cp": 20,
        "pv_san": ["e4", "e5"],
    },
]


@pytest.fixture()
def client():
    """Return a Flask test client with testing mode enabled."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# GET /api/opening
# ---------------------------------------------------------------------------


class TestApiOpening:
    """Tests for the opening-book lookup endpoint."""

    def test_start_position_found(self, client):
        """Starting position is in the book."""
        resp = client.get(f"/api/opening?fen={START_FEN}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["found"] is True

    def test_start_position_has_eco(self, client):
        """Starting-position response includes an ECO code."""
        resp = client.get(f"/api/opening?fen={START_FEN}")
        data = resp.get_json()
        assert "eco" in data
        assert isinstance(data["eco"], str)

    def test_unknown_position_not_found(self, client):
        """Random mid-game position returns found: false."""
        fen = "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
        resp = client.get(f"/api/opening?fen={fen}")
        assert resp.status_code == 200
        assert resp.get_json()["found"] is False

    def test_missing_fen_returns_not_found(self, client):
        """Request without fen query param returns found: false."""
        resp = client.get("/api/opening")
        assert resp.status_code == 200
        assert resp.get_json()["found"] is False


# ---------------------------------------------------------------------------
# POST /api/analyze
# ---------------------------------------------------------------------------


class TestApiAnalyze:
    """Tests for the Stockfish analysis endpoint."""

    def test_valid_fen_returns_candidates(self, client):
        """Valid FEN returns a list of candidates."""
        with patch("engine_manager.analyze", return_value=_MOCK_CANDIDATES):
            resp = client.post(
                "/api/analyze",
                data=json.dumps({"fen": START_FEN}),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "candidates" in data
        assert len(data["candidates"]) == len(_MOCK_CANDIDATES)

    def test_candidate_shape(self, client):
        """Each candidate has required fields."""
        with patch("engine_manager.analyze", return_value=_MOCK_CANDIDATES):
            resp = client.post(
                "/api/analyze",
                data=json.dumps({"fen": START_FEN}),
                content_type="application/json",
            )
        for c in resp.get_json()["candidates"]:
            for field in ("san", "uci", "score_cp", "score_label", "explanation"):
                assert field in c, f"Missing field: {field}"

    def test_invalid_fen_returns_400(self, client):
        """Invalid FEN string returns HTTP 400."""
        resp = client.post(
            "/api/analyze",
            data=json.dumps({"fen": "not-a-fen"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_eval_cp_in_response(self, client):
        """Response includes eval_cp scalar."""
        with patch("engine_manager.analyze", return_value=_MOCK_CANDIDATES):
            resp = client.post(
                "/api/analyze",
                data=json.dumps({"fen": START_FEN}),
                content_type="application/json",
            )
        assert "eval_cp" in resp.get_json()

    def test_engine_error_returns_500(self, client):
        """Engine exception is surfaced as HTTP 500."""
        with patch("engine_manager.analyze", side_effect=RuntimeError("engine dead")):
            resp = client.post(
                "/api/analyze",
                data=json.dumps({"fen": START_FEN}),
                content_type="application/json",
            )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /api/opponent-responses
# ---------------------------------------------------------------------------


class TestApiOpponentResponses:
    """Tests for the opponent-responses endpoint."""

    # Starting position (White to move) matches the mock candidates (White moves)
    def test_valid_fen_returns_responses(self, client):
        """Valid FEN returns a responses list."""
        with patch("engine_manager.analyze", return_value=_MOCK_CANDIDATES):
            resp = client.post(
                "/api/opponent-responses",
                data=json.dumps({"fen": START_FEN}),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "responses" in data
        assert isinstance(data["responses"], list)

    def test_response_shape(self, client):
        """Each response has required fields."""
        with patch("engine_manager.analyze", return_value=_MOCK_CANDIDATES):
            resp = client.post(
                "/api/opponent-responses",
                data=json.dumps({"fen": START_FEN}),
                content_type="application/json",
            )
        for r in resp.get_json()["responses"]:
            for field in ("san", "explanation", "in_book"):
                assert field in r, f"Missing field: {field}"

    def test_invalid_fen_returns_400(self, client):
        """Invalid FEN returns HTTP 400."""
        resp = client.post(
            "/api/opponent-responses",
            data=json.dumps({"fen": "garbage"}),
            content_type="application/json",
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/legal-moves
# ---------------------------------------------------------------------------


class TestApiLegalMoves:
    """Tests for the legal-moves utility endpoint."""

    def test_start_position_has_20_moves(self, client):
        """Starting position has exactly 20 legal moves."""
        resp = client.get(f"/api/legal-moves?fen={START_FEN}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["moves"]) == 20

    def test_returns_list_of_strings(self, client):
        """All moves are SAN strings."""
        resp = client.get(f"/api/legal-moves?fen={START_FEN}")
        for move in resp.get_json()["moves"]:
            assert isinstance(move, str)

    def test_invalid_fen_returns_400(self, client):
        """Garbage FEN returns HTTP 400."""
        resp = client.get("/api/legal-moves?fen=not-fen")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Score formatting helper
# ---------------------------------------------------------------------------


class TestFormatScore:
    """Tests for the _format_score internal helper."""

    def test_positive_score(self):
        from app import _format_score
        assert _format_score(30) == "+0.3"

    def test_negative_score(self):
        from app import _format_score
        assert _format_score(-150) == "-1.5"

    def test_zero_score(self):
        from app import _format_score
        assert _format_score(0) == "0.0"

    def test_mate_positive(self):
        from app import _format_score
        assert _format_score(10000) == "+M"

    def test_mate_negative(self):
        from app import _format_score
        assert _format_score(-9500) == "-M"
