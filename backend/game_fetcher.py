"""Chess.com public API client for fetching player games."""

from __future__ import annotations

import re
from datetime import date
from typing import Literal

import requests

_HEADERS = {"User-Agent": "chess-tutor/1.0 (github.com/local)"}
_BASE = "https://api.chess.com/pub/player"

TimeClass = Literal["rapid", "blitz", "bullet", "daily", "all"]
Color = Literal["white", "black", "both"]
Result = Literal["win", "loss", "draw", "all"]
Termination = Literal[
    "all",
    "checkmate",
    "resignation",
    "timeout",
    "abandonment",
    "draw_agreement",
    "draw_repetition",
    "draw_stalemate",
    "draw_50move",
    "draw_insufficient",
]
Rated = Literal["all", "rated", "unrated"]


def _month_range(start: date, end: date) -> list[tuple[int, int]]:
    """Return (year, month) pairs from start to end inclusive."""
    pairs: list[tuple[int, int]] = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        pairs.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return pairs


def _parse_result(game: dict, username: str) -> str:
    """Return 'win', 'loss', or 'draw' from the perspective of username."""
    uname = username.lower()
    white = game.get("white", {})
    black = game.get("black", {})

    if white.get("username", "").lower() == uname:
        r = white.get("result", "")
    else:
        r = black.get("result", "")

    win_results = {"win"}
    draw_results = {"agreed", "repetition", "stalemate", "insufficient", "50move", "timevsinsufficient", "draw"}
    if r == "win":
        return "win"
    if r in draw_results:
        return "draw"
    return "loss"


def _parse_termination(game: dict) -> str:
    """Return a normalised termination string from the raw Chess.com result codes."""
    results = {
        game.get("white", {}).get("result", ""),
        game.get("black", {}).get("result", ""),
    }
    if "checkmated" in results:
        return "checkmate"
    if "resigned" in results:
        return "resignation"
    if "abandoned" in results:
        return "abandonment"
    if "timeout" in results:
        return "timeout"
    if "stalemate" in results:
        return "draw_stalemate"
    if results & {"timevsinsufficient", "insufficient"}:
        return "draw_insufficient"
    if "50move" in results:
        return "draw_50move"
    if results & {"agreed", "draw"}:
        return "draw_agreement"
    if "repetition" in results:
        return "draw_repetition"
    return "other"


def _parse_color(game: dict, username: str) -> str:
    uname = username.lower()
    if game.get("white", {}).get("username", "").lower() == uname:
        return "white"
    return "black"


def _extract_eco(pgn: str) -> tuple[str, str]:
    """Return (eco_code, opening_name) from PGN headers."""
    eco = ""
    name = ""
    eco_url_name = ""
    for line in pgn.splitlines():
        m = re.match(r'\[ECO "([^"]+)"\]', line)
        if m:
            eco = m.group(1)
        m = re.match(r'\[Opening "([^"]+)"\]', line)
        if m:
            name = m.group(1)
        # Chess.com encodes the opening name in the ECOUrl path as a fallback
        m = re.match(r'\[ECOUrl "https?://[^/]+/openings/([^"]+)"\]', line)
        if m:
            eco_url_name = m.group(1).replace("-", " ")
        if eco and name:
            break
    return eco, name or eco_url_name


def fetch_games(
    username: str,
    start_date: date,
    end_date: date,
    time_class: TimeClass = "all",
    color: Color = "both",
    result: Result = "all",
    termination: Termination = "all",
    rated: Rated = "all",
    min_opponent_rating: int | None = None,
    max_opponent_rating: int | None = None,
    max_games: int = 100,
) -> list[dict]:
    """Fetch and filter games from Chess.com.

    Returns a list of game summary dicts, each containing:
        url, pgn, time_class, color, result, termination, rated,
        eco, opening_name, white_username, black_username,
        white_rating, black_rating, opponent_rating, end_time
    """
    months = _month_range(start_date, end_date)
    raw_games: list[dict] = []

    for year, month in months:
        url = f"{_BASE}/{username}/games/{year}/{month:02d}"
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            raise RuntimeError(f"Chess.com fetch failed for {year}/{month}: {exc}") from exc

        for g in data.get("games", []):
            if g.get("rules") != "chess":
                continue
            raw_games.append(g)

    filtered: list[dict] = []
    for g in raw_games:
        tc = g.get("time_class", "")
        if time_class != "all" and tc != time_class:
            continue

        g_color = _parse_color(g, username)
        if color != "both" and g_color != color:
            continue

        g_result = _parse_result(g, username)
        if result != "all" and g_result != result:
            continue

        g_termination = _parse_termination(g)
        if termination != "all" and g_termination != termination:
            continue

        g_rated = g.get("rated", True)
        if rated == "rated" and not g_rated:
            continue
        if rated == "unrated" and g_rated:
            continue

        white = g.get("white", {})
        black = g.get("black", {})
        opp = black if g_color == "white" else white
        opp_rating = opp.get("rating", 0)
        if min_opponent_rating is not None and opp_rating < min_opponent_rating:
            continue
        if max_opponent_rating is not None and opp_rating > max_opponent_rating:
            continue

        eco, opening_name = _extract_eco(g.get("pgn", ""))

        filtered.append({
            "url": g.get("url", ""),
            "pgn": g.get("pgn", ""),
            "time_class": tc,
            "color": g_color,
            "result": g_result,
            "termination": g_termination,
            "rated": g_rated,
            "eco": eco,
            "opening_name": opening_name,
            "white_username": white.get("username", ""),
            "black_username": black.get("username", ""),
            "white_rating": white.get("rating", 0),
            "black_rating": black.get("rating", 0),
            "opponent_rating": opp_rating,
            "end_time": g.get("end_time", 0),
            "accuracies": g.get("accuracies"),
        })

        if len(filtered) >= max_games:
            break

    return filtered
