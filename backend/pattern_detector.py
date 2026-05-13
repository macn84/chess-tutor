"""Aggregate pattern analysis across a set of analyzed games."""

from __future__ import annotations

from collections import defaultdict


def detect_patterns(analyzed_games: list[dict], username: str) -> dict:
    """Compute aggregate patterns across all analyzed games.

    Returns a dict with keys:
        username, total_games, wins, losses, draws,
        blunders_per_game, mistakes_per_game, inaccuracies_per_game,
        avg_cp_loss, phase_distribution, opening_stats,
        top_blunders, mistake_move_numbers
    """
    total = len(analyzed_games)
    if total == 0:
        return _empty_patterns(username)

    wins = sum(1 for g in analyzed_games if g["result"] == "win")
    losses = sum(1 for g in analyzed_games if g["result"] == "loss")
    draws = sum(1 for g in analyzed_games if g["result"] == "draw")

    all_mistakes: list[dict] = []
    phase_totals: dict[str, int] = {"opening": 0, "middlegame": 0, "endgame": 0}
    severity_totals: dict[str, int] = {"blunder": 0, "mistake": 0, "inaccuracy": 0}
    total_cp_loss = 0.0

    # opening_key -> {games, wins, total_cp_loss, blunders: list}
    opening_map: dict[str, dict] = defaultdict(lambda: {
        "eco": "",
        "opening_name": "",
        "games": 0,
        "wins": 0,
        "total_cp_loss": 0.0,
        "blunders": [],
    })

    move_number_counts: dict[int, int] = defaultdict(int)

    for game in analyzed_games:
        eco = game.get("eco", "") or "?"
        oname = game.get("opening_name", "") or "Unknown"
        key = eco if eco != "?" else oname

        entry = opening_map[key]
        entry["eco"] = eco
        entry["opening_name"] = oname
        entry["games"] += 1
        if game["result"] == "win":
            entry["wins"] += 1
        entry["total_cp_loss"] += game.get("avg_cp_loss", 0)
        total_cp_loss += game.get("avg_cp_loss", 0)

        for mistake in game.get("mistakes", []):
            mistake_with_game = {**mistake, "game_url": game["url"]}
            all_mistakes.append(mistake_with_game)

            phase = mistake["phase"]
            phase_totals[phase] += 1
            severity_totals[mistake["severity"]] += 1
            move_number_counts[mistake["move_number"]] += 1

            if mistake["severity"] == "blunder":
                entry["blunders"].append(mistake_with_game)

    grand_total_mistakes = sum(severity_totals.values())
    phase_dist = {}
    if grand_total_mistakes > 0:
        for phase, count in phase_totals.items():
            phase_dist[phase] = round(count / grand_total_mistakes * 100, 1)
    else:
        phase_dist = {"opening": 0, "middlegame": 0, "endgame": 0}

    top_blunders = sorted(
        [m for m in all_mistakes if m["severity"] == "blunder"],
        key=lambda m: m["cp_loss"],
        reverse=True,
    )[:5]

    opening_stats = []
    for key, data in opening_map.items():
        n = data["games"]
        opening_stats.append({
            "eco": data["eco"],
            "opening_name": data["opening_name"],
            "games": n,
            "wins": data["wins"],
            "win_rate": round(data["wins"] / n * 100, 1) if n else 0,
            "avg_cp_loss": round(data["total_cp_loss"] / n, 1) if n else 0,
        })
    opening_stats.sort(key=lambda x: x["games"], reverse=True)

    # Mistake move number histogram: top 10 most error-prone move numbers
    move_hist = sorted(
        [{"move_number": mn, "count": cnt} for mn, cnt in move_number_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:10]

    return {
        "username": username,
        "total_games": total,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "blunders_per_game": round(severity_totals["blunder"] / total, 2),
        "mistakes_per_game": round(severity_totals["mistake"] / total, 2),
        "inaccuracies_per_game": round(severity_totals["inaccuracy"] / total, 2),
        "avg_cp_loss": round(total_cp_loss / total, 1),
        "phase_distribution": phase_dist,
        "opening_stats": opening_stats,
        "top_blunders": top_blunders,
        "mistake_move_numbers": move_hist,
        "severity_totals": severity_totals,
    }


def _empty_patterns(username: str) -> dict:
    return {
        "username": username,
        "total_games": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "blunders_per_game": 0,
        "mistakes_per_game": 0,
        "inaccuracies_per_game": 0,
        "avg_cp_loss": 0,
        "phase_distribution": {"opening": 0, "middlegame": 0, "endgame": 0},
        "opening_stats": [],
        "top_blunders": [],
        "mistake_move_numbers": [],
        "severity_totals": {"blunder": 0, "mistake": 0, "inaccuracy": 0},
    }
