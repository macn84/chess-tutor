"""Tests for insights_generator module."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock
import pytest

from insights_generator import generate_insights, _fallback_insights

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_PATTERNS = {
    "username": "testuser",
    "total_games": 10,
    "wins": 6,
    "losses": 3,
    "draws": 1,
    "blunders_per_game": 1.2,
    "mistakes_per_game": 2.1,
    "inaccuracies_per_game": 3.0,
    "avg_cp_loss": 55.0,
    "phase_distribution": {"opening": 30.0, "middlegame": 50.0, "endgame": 20.0},
    "opening_stats": [
        {
            "eco": "B20",
            "opening_name": "Sicilian",
            "games": 5,
            "wins": 3,
            "win_rate": 60.0,
            "avg_cp_loss": 50.0,
        },
        {
            "eco": "C20",
            "opening_name": "King's Pawn",
            "games": 3,
            "wins": 2,
            "win_rate": 66.7,
            "avg_cp_loss": 80.0,
        },
    ],
    "top_blunders": [
        {
            "move_number": 12,
            "phase": "opening",
            "severity": "blunder",
            "move_played_san": "e4",
            "best_move_san": "d4",
            "best_pv_san": ["d4"],
            "cp_loss": 350,
            "fen_before": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -",
            "game_url": "https://chess.com/game/1",
        }
    ],
    "mistake_move_numbers": [
        {"move_number": 5, "count": 4},
        {"move_number": 12, "count": 2},
    ],
    "severity_totals": {"blunder": 12, "mistake": 21, "inaccuracy": 30},
}

_EMPTY_PATTERNS = {**_PATTERNS, "total_games": 0}


# ---------------------------------------------------------------------------
# _fallback_insights
# ---------------------------------------------------------------------------


class TestFallbackInsights:
    def test_returns_string(self):
        result = _fallback_insights(_PATTERNS)
        assert isinstance(result, str)

    def test_contains_five_findings(self):
        result = _fallback_insights(_PATTERNS)
        for i in range(1, 6):
            assert f"Finding {i}" in result

    def test_zero_games_returns_message(self):
        result = _fallback_insights(_EMPTY_PATTERNS)
        assert "No games" in result

    def test_includes_win_rate(self):
        result = _fallback_insights(_PATTERNS)
        # 6 wins / 10 games = 60.0%
        assert "60.0%" in result

    def test_includes_worst_phase(self):
        # middlegame is 50% — highest
        result = _fallback_insights(_PATTERNS)
        assert "middlegame" in result.lower() or "Middlegame" in result

    def test_includes_blunder_move_number(self):
        result = _fallback_insights(_PATTERNS)
        # move 5 has the highest error count
        assert "5" in result

    def test_no_openings_handled_gracefully(self):
        patterns = {**_PATTERNS, "opening_stats": []}
        result = _fallback_insights(patterns)
        assert "Finding 3" in result

    def test_no_blunders_handled_gracefully(self):
        patterns = {**_PATTERNS, "top_blunders": []}
        result = _fallback_insights(patterns)
        assert "Finding 5" in result


# ---------------------------------------------------------------------------
# generate_insights — no API key (fallback path)
# ---------------------------------------------------------------------------


class TestGenerateInsightsNoKey:
    def test_no_key_uses_fallback(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
            result = generate_insights(_PATTERNS, [])
        assert result["llm_used"] is False
        assert isinstance(result["insights"], str)
        assert len(result["insights"]) > 50

    def test_no_key_contains_findings(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
            result = generate_insights(_PATTERNS, [])
        assert "Finding 1" in result["insights"]


# ---------------------------------------------------------------------------
# generate_insights — with API key (LLM path)
# ---------------------------------------------------------------------------


class TestGenerateInsightsWithKey:
    def _make_mock_client(self, text: str = "Finding 1: Analysis.") -> MagicMock:
        mock_content = MagicMock()
        mock_content.text = text
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        return mock_client

    def test_calls_claude_when_key_set(self):
        mock_client = self._make_mock_client()
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
            with patch("anthropic.Anthropic", return_value=mock_client):
                result = generate_insights(_PATTERNS, [])
        assert result["llm_used"] is True
        mock_client.messages.create.assert_called_once()

    def test_uses_haiku_model(self):
        mock_client = self._make_mock_client()
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
            with patch("anthropic.Anthropic", return_value=mock_client):
                generate_insights(_PATTERNS, [])
        call_kwargs = mock_client.messages.create.call_args
        assert "haiku" in call_kwargs.kwargs.get("model", "")

    def test_returns_llm_text(self):
        mock_client = self._make_mock_client("Finding 1: You blunder too much.")
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
            with patch("anthropic.Anthropic", return_value=mock_client):
                result = generate_insights(_PATTERNS, [])
        assert result["insights"] == "Finding 1: You blunder too much."

    def test_llm_failure_falls_back_to_engine_analysis(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
            with patch("anthropic.Anthropic", side_effect=Exception("network error")):
                result = generate_insights(_PATTERNS, [])
        assert result["llm_used"] is False
        assert isinstance(result["insights"], str)
