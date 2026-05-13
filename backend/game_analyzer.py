"""Batch blunder detection across a set of games using the shared Stockfish engine."""

from __future__ import annotations

import io
import time
from typing import TYPE_CHECKING

import chess
import chess.pgn

import engine_manager

if TYPE_CHECKING:
    pass

# Centipawn swing thresholds
_BLUNDER_CP = 300
_MISTAKE_CP = 150
_INACCURACY_CP = 50

# Move number phase boundaries
_OPENING_END = 14
_MIDDLEGAME_END = 34

# Stockfish time limits (seconds)
_FAST_SEC = 0.15   # used for every move in the walk
_DEEP_SEC = 0.4    # used for the best-move lookup on significant errors


def _phase(move_number: int) -> str:
    if move_number <= _OPENING_END:
        return "opening"
    if move_number <= _MIDDLEGAME_END:
        return "middlegame"
    return "endgame"


def _eval_fen(fen: str, time_sec: float) -> int | None:
    """Return centipawn eval from White's perspective, or None on failure."""
    try:
        results = engine_manager.analyze(fen, time_sec=time_sec, multipv=1)
        if results:
            return results[0]["score_cp"]
    except Exception:
        pass
    return None


def _best_move_for_fen(fen: str) -> tuple[str, list[str]] | None:
    """Return (best_san, pv_san) or None."""
    try:
        results = engine_manager.analyze(fen, time_sec=_DEEP_SEC, multipv=1)
        if results:
            return results[0]["san"], results[0]["pv_san"]
    except Exception:
        pass
    return None


def _cp_loss(eval_before: int, eval_after: int, player_color: chess.Color) -> int:
    """Compute centipawn loss from the perspective of the player who just moved."""
    if player_color == chess.WHITE:
        # White moved; eval_before is White-to-move, eval_after is Black-to-move
        # A drop in eval is bad for White
        return max(0, eval_before - eval_after)
    else:
        # Black moved; eval_before is Black-to-move, eval_after is White-to-move
        # Eval is always from White's perspective, so for Black:
        # Before Black's move eval was eval_before (from White's view: bad for White = good for Black)
        # After Black's move eval is eval_after (from White's view)
        # Black loses cp when eval_after becomes more positive (better for White)
        return max(0, eval_after - eval_before)


def analyze_games(
    games: list[dict],
    username: str,
    job_store: dict,
    job_id: str,
) -> None:
    """Analyze all games and write results into job_store[job_id].

    Runs in a background thread. Updates progress as it goes.
    Each game dict must have at least 'pgn', 'url', 'color', 'result',
    'eco', 'opening_name'.
    """
    total = len(games)
    analyzed: list[dict] = []

    for idx, game_summary in enumerate(games):
        job_store["analyzed_count"] = idx
        job_store["progress"] = idx / total if total else 1.0

        pgn_text = game_summary.get("pgn", "")
        if not pgn_text:
            continue

        try:
            game_result = _analyze_single_game(game_summary, username)
            analyzed.append(game_result)
        except Exception:
            # Skip games that fail (corrupted PGN, engine error, etc.)
            continue

    job_store.update({
        "progress": 1.0,
        "analyzed_count": total,
        "analyzed_games": analyzed,
    })


def _analyze_single_game(game_summary: dict, username: str) -> dict:
    """Walk one game, detect errors, return structured analysis."""
    pgn_text = game_summary["pgn"]
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("Could not parse PGN")

    color_str = game_summary.get("color", "white")
    player_color = chess.WHITE if color_str == "white" else chess.BLACK

    # Extract first moves for both sides before the analysis loop
    _first_moves: list[tuple[chess.Color, str]] = []
    _preview_board = game.board()
    for _node in game.mainline():
        if len(_first_moves) >= 2:
            break
        _san = _preview_board.san(_node.move)
        _first_moves.append((_preview_board.turn, _san))
        _preview_board.push(_node.move)

    white_move_1 = next((s for c, s in _first_moves if c == chess.WHITE), "")
    black_move_1 = next((s for c, s in _first_moves if c == chess.BLACK), "")
    player_move_1 = white_move_1 if player_color == chess.WHITE else black_move_1
    opponent_move_1 = black_move_1 if player_color == chess.WHITE else white_move_1

    board = game.board()
    mistakes: list[dict] = []
    phase_mistakes: dict[str, int] = {"opening": 0, "middlegame": 0, "endgame": 0}
    total_cp_loss = 0
    move_count = 0

    eval_before: int | None = None

    for node in game.mainline():
        move = node.move
        move_number = board.fullmove_number
        mover = board.turn  # who is about to move

        # Only eval positions where it's our turn
        if mover == player_color:
            if eval_before is None:
                eval_before = _eval_fen(board.fen(), _FAST_SEC)

            san = board.san(move)
            board.push(move)
            move_count += 1

            eval_after = _eval_fen(board.fen(), _FAST_SEC)

            if eval_before is not None and eval_after is not None:
                loss = _cp_loss(eval_before, eval_after, player_color)
                total_cp_loss += loss

                if loss >= _INACCURACY_CP:
                    # Get best move (deeper) for the position before the move
                    board.pop()
                    best_info = _best_move_for_fen(board.fen())
                    board.push(move)

                    phase = _phase(move_number)
                    phase_mistakes[phase] += 1

                    severity = (
                        "blunder" if loss >= _BLUNDER_CP
                        else "mistake" if loss >= _MISTAKE_CP
                        else "inaccuracy"
                    )

                    mistakes.append({
                        "move_number": move_number,
                        "phase": phase,
                        "severity": severity,
                        "move_played_san": san,
                        "best_move_san": best_info[0] if best_info else "",
                        "best_pv_san": best_info[1] if best_info else [],
                        "cp_loss": loss,
                        "fen_before": board.fen(),  # after the move (for display)
                    })

            eval_before = None  # reset; will be fetched as eval_after next turn is ours
        else:
            board.push(move)
            # After opponent's move, capture current eval as our "eval_before" for next move
            eval_before = _eval_fen(board.fen(), _FAST_SEC)

    avg_cp_loss = round(total_cp_loss / move_count, 1) if move_count else 0

    return {
        "url": game_summary.get("url", ""),
        "eco": game_summary.get("eco", ""),
        "opening_name": game_summary.get("opening_name", ""),
        "color": color_str,
        "player_move_1": player_move_1,
        "opponent_move_1": opponent_move_1,
        "result": game_summary.get("result", ""),
        "white_username": game_summary.get("white_username", ""),
        "black_username": game_summary.get("black_username", ""),
        "white_rating": game_summary.get("white_rating", 0),
        "black_rating": game_summary.get("black_rating", 0),
        "end_time": game_summary.get("end_time", 0),
        "accuracies": game_summary.get("accuracies"),
        "mistakes": mistakes,
        "phase_mistakes": phase_mistakes,
        "avg_cp_loss": avg_cp_loss,
        "total_moves_analyzed": move_count,
    }
