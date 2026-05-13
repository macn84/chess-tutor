"""Generate coaching insights from pattern data, using Claude API when available."""

from __future__ import annotations

import json
import os


def generate_insights(patterns: dict, analyzed_games: list[dict]) -> dict:
    """Return coaching insights dict with keys 'insights' (str) and 'llm_used' (bool).

    Uses Claude Haiku if ANTHROPIC_API_KEY is set, otherwise generates
    structured plain-text insights from the patterns data directly.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        try:
            return _llm_insights(patterns, analyzed_games, api_key)
        except Exception:
            pass  # fall through to fallback

    return {"insights": _fallback_insights(patterns), "llm_used": False}


# ---------------------------------------------------------------------------
# LLM path
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a skilled chess coach reviewing a player's game history. You have been given \
structured analysis data from a set of their recent games.

Respond with exactly 5 numbered findings, each with a concrete training recommendation. \
Format:

**Finding 1: <title>**
<2-3 sentence observation about the pattern>
Training tip: <specific, actionable advice>

...and so on through Finding 5.

Be direct and specific. Reference move numbers, openings, or game phases mentioned in the data. \
Avoid generic advice like "study tactics" — tie every recommendation to the actual data provided.

IMPORTANT: Prioritise RECURRING patterns over single-occurrence events. A mistake made once \
(even a large cp_loss) is less actionable than a pattern that appears across multiple games. \
If a blunder move number does not also appear in error_prone_move_numbers, treat it as a \
one-off outlier and omit or heavily discount it. Focus findings on patterns the player \
will encounter again.\
"""


def _llm_insights(patterns: dict, analyzed_games: list[dict], api_key: str) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    # Build a concise summary to send — avoid sending full PGNs
    sample_blunders = []
    for b in patterns.get("top_blunders", [])[:3]:
        sample_blunders.append({
            "move_number": b["move_number"],
            "phase": b["phase"],
            "played": b["move_played_san"],
            "best": b["best_move_san"],
            "cp_loss": b["cp_loss"],
            "game_url": b.get("game_url", ""),
        })

    payload = {
        "total_games": patterns["total_games"],
        "wins": patterns["wins"],
        "losses": patterns["losses"],
        "draws": patterns["draws"],
        "blunders_per_game": patterns["blunders_per_game"],
        "mistakes_per_game": patterns["mistakes_per_game"],
        "avg_cp_loss": patterns["avg_cp_loss"],
        "phase_distribution_pct": patterns["phase_distribution"],
        "most_played_openings": patterns["opening_stats"][:5],
        "error_prone_move_numbers": patterns["mistake_move_numbers"][:5],
        "worst_blunders": sample_blunders,
    }

    user_message = (
        f"Please analyse this data for player '{patterns['username']}':\n\n"
        + json.dumps(payload, indent=2)
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1200,
        system=[
            {
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )

    text = response.content[0].text if response.content else ""
    return {"insights": text, "llm_used": True}


# ---------------------------------------------------------------------------
# Fallback path (no API key)
# ---------------------------------------------------------------------------

def _fallback_insights(patterns: dict) -> str:
    total = patterns["total_games"]
    if total == 0:
        return "No games were analyzed."

    wins = patterns["wins"]
    losses = patterns["losses"]
    draws = patterns["draws"]
    win_rate = round(wins / total * 100, 1)

    bpg = patterns["blunders_per_game"]
    mpg = patterns["mistakes_per_game"]
    avg_cp = patterns["avg_cp_loss"]

    phase_dist = patterns["phase_distribution"]
    worst_phase = max(phase_dist, key=lambda p: phase_dist[p]) if phase_dist else "middlegame"

    top_openings = patterns["opening_stats"][:3]
    top_blunders = patterns["top_blunders"][:3]
    move_hist = patterns["mistake_move_numbers"][:3]

    lines: list[str] = []
    lines.append(f"**Finding 1: Overall Performance ({total} games)**")
    lines.append(
        f"You scored {wins}W / {draws}D / {losses}L ({win_rate}% win rate). "
        f"Your average centipawn loss per game is {avg_cp}, with {bpg:.1f} blunders "
        f"and {mpg:.1f} mistakes per game on average."
    )
    lines.append(
        "Training tip: Track your cp-loss trend over time. Aim to bring the average "
        "below 50 cp/game for your time control."
    )
    lines.append("")

    lines.append(f"**Finding 2: Mistakes Cluster in the {worst_phase.title()}**")
    dist_str = ", ".join(f"{p}: {v}%" for p, v in phase_dist.items())
    lines.append(
        f"Error distribution — {dist_str}. "
        f"The {worst_phase} is your most error-prone phase."
    )
    lines.append(
        f"Training tip: Dedicate study time to {worst_phase} patterns. "
        "Use puzzle sets filtered to that phase."
    )
    lines.append("")

    if top_openings:
        lines.append("**Finding 3: Opening Repertoire Performance**")
        worst_op = max(top_openings, key=lambda o: o["avg_cp_loss"])
        best_op = min(top_openings, key=lambda o: o["avg_cp_loss"])
        lines.append(
            f"Your highest cp-loss opening is {worst_op['opening_name']} ({worst_op['eco']}, "
            f"avg {worst_op['avg_cp_loss']} cp/game, {worst_op['win_rate']}% wins). "
            f"Your most accurate is {best_op['opening_name']} ({best_op['eco']}, "
            f"avg {best_op['avg_cp_loss']} cp/game)."
        )
        lines.append(
            f"Training tip: Review your games in {worst_op['opening_name']} with an engine. "
            "Look for the specific move where you deviate from best play."
        )
        lines.append("")
    else:
        lines.append("**Finding 3: Opening Data**")
        lines.append("Not enough games with ECO data to draw opening conclusions.")
        lines.append("")

    if move_hist:
        move_nums = ", ".join(str(m["move_number"]) for m in move_hist)
        lines.append("**Finding 4: Recurring Error Move Numbers**")
        lines.append(
            f"You make the most errors on moves {move_nums}. "
            "These move numbers coincide with typical transition points "
            "(opening → middlegame, or time pressure)."
        )
        lines.append(
            "Training tip: In your next games, pause and double-check your candidate "
            f"moves extra carefully around move {move_hist[0]['move_number']}."
        )
        lines.append("")
    else:
        lines.append("**Finding 4: Move Number Patterns**")
        lines.append("Insufficient data to identify recurring error move numbers.")
        lines.append("")

    # Only highlight a blunder if its move number is also a recurring error move (count > 1)
    recurring_move_numbers = {m["move_number"] for m in move_hist if m["count"] > 1}
    recurring_blunder = next(
        (b for b in top_blunders if b["move_number"] in recurring_move_numbers), None
    )
    if recurring_blunder:
        b = recurring_blunder
        count = next((m["count"] for m in move_hist if m["move_number"] == b["move_number"]), 1)
        lines.append("**Finding 5: Recurring Blunder Pattern**")
        lines.append(
            f"You have blundered on move {b['move_number']} ({b['phase']}) across {count} games. "
            f"In your worst instance you played {b['move_played_san']} "
            f"(best was {b['best_move_san']}, loss: {b['cp_loss']} cp)."
        )
        lines.append(
            f"Training tip: Load several of your games where you reached move {b['move_number']} "
            "and compare the positions. Identify the recurring tactical or positional theme "
            "you're missing."
        )
    elif top_blunders:
        lines.append("**Finding 5: Accuracy**")
        lines.append(
            "Your blunders appear to be one-off oversights rather than a recurring pattern — "
            f"your worst was {top_blunders[0]['cp_loss']} cp on move {top_blunders[0]['move_number']}. "
            "Focus on eliminating time-pressure mistakes."
        )
        lines.append(
            "Training tip: Practice slower time controls occasionally to build the habit "
            "of checking for opponent threats before each move."
        )
    else:
        lines.append("**Finding 5: No Blunders Detected**")
        lines.append(
            "No blunders above 300 cp were found in this sample — great accuracy! "
            "Focus on converting your small advantages more consistently."
        )

    return "\n".join(lines)
