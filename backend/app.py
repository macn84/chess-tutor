"""Flask application: Chess Tutor API.

Exposes four JSON endpoints consumed by the React frontend:

- ``GET  /api/opening``           — Fast opening-book lookup (no engine).
- ``POST /api/analyze``           — Stockfish multi-PV analysis with prose.
- ``POST /api/opponent-responses``— Top engine replies from opponent's view.
- ``GET  /api/legal-moves``       — All legal SAN moves for a position.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import chess
import chess.engine

import engine_manager
import explainer
import opening_book

app = Flask(__name__)
CORS(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_fen(fen: str) -> str:
    """Return the first four FEN fields (strips clocks for book lookup).

    Args:
        fen: Full FEN string.

    Returns:
        Normalised FEN with only piece placement, side, castling, en-passant.
    """
    parts = fen.split()
    return " ".join(parts[:4])


def _format_score(cp: int) -> str:
    """Format a centipawn score as a human-readable string.

    Args:
        cp: Score in centipawns from White's perspective.  Values ≥ 9000 are
            treated as forced-mate signals.

    Returns:
        Strings like ``"+0.3"``, ``"-1.5"``, ``"+M"``, or ``"-M"``.
    """
    if abs(cp) >= 9000:
        return "+M" if cp > 0 else "-M"
    val = cp / 100
    if val > 0:
        return f"+{val:.1f}"
    return f"{val:.1f}"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/opening")
def api_opening():
    """Look up a position in the opening book.

    Query params:
        fen (str): URL-encoded FEN of the position.

    Returns:
        JSON with ``found: false`` when not in book, or the full entry fields
        (``eco``, ``opening_name``, ``variation_name``, ``strategic_ideas``,
        ``main_line_moves``) when found.
    """
    fen = request.args.get("fen", "")
    if not fen:
        return jsonify({"found": False})
    entry = opening_book.lookup(fen)
    if entry is None:
        return jsonify({"found": False})
    return jsonify({
        "found": True,
        "eco": entry.get("eco", ""),
        "opening_name": entry.get("opening_name", ""),
        "variation_name": entry.get("variation_name", ""),
        "strategic_ideas": entry.get("strategic_ideas", []),
        "main_line_moves": entry.get("main_line_moves", []),
    })


@app.post("/api/analyze")
def api_analyze():
    """Run Stockfish multi-PV analysis and enrich results with prose.

    Request body (JSON):
        fen (str): Position to analyse.
        num_candidates (int, optional): Lines to return (default 4).

    Returns:
        JSON with ``candidates`` list, ``best_move_san``, and ``eval_cp``.
        Each candidate includes ``san``, ``uci``, ``score_cp``,
        ``score_label``, ``pv_san``, ``explanation``, ``label``.

    HTTP errors:
        400: Invalid FEN.
        500: Engine error.
    """
    data = request.get_json(force=True)
    fen = data.get("fen", "")
    num_candidates = int(data.get("num_candidates", 4))

    try:
        board = chess.Board(fen)
    except Exception:
        return jsonify({"error": "invalid FEN"}), 400

    try:
        raw = engine_manager.analyze(fen, time_sec=1.5, multipv=num_candidates)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    book_entry = opening_book.lookup(fen)
    book_candidates = (
        book_entry.get("candidate_explanations", {}) if book_entry else {}
    )

    candidates = []
    for c in raw:
        move = chess.Move.from_uci(c["uci"])
        book_info = book_candidates.get(c["san"], {})
        prose = explainer.explain_move(board, move, book_info.get("prose"))
        candidates.append({
            "san": c["san"],
            "uci": c["uci"],
            "score_cp": c["score_cp"],
            "score_label": _format_score(c["score_cp"]),
            "pv_san": c["pv_san"],
            "explanation": prose,
            "label": book_info.get("label", ""),
        })

    eval_cp = candidates[0]["score_cp"] if candidates else 0
    best_move = candidates[0]["san"] if candidates else ""

    return jsonify({
        "candidates": candidates,
        "best_move_san": best_move,
        "eval_cp": eval_cp,
    })


@app.post("/api/opponent-responses")
def api_opponent_responses():
    """Return the top engine moves from the opponent's perspective.

    Analyses the current position (which is the opponent's turn after the
    user's last move) and annotates each reply with prose, opening name if
    the resulting position is in the book, and a follow-up idea string.

    Request body (JSON):
        fen (str): Position after the user's last move (opponent to move).
        num_responses (int, optional): Responses to return (default 3).

    Returns:
        JSON with a ``responses`` list.  Each entry contains ``san``,
        ``score_cp``, ``explanation``, ``label``, ``follow_up_idea``,
        ``resulting_opening``, and ``in_book``.

    HTTP errors:
        400: Invalid FEN.
        500: Engine error.
    """
    data = request.get_json(force=True)
    fen = data.get("fen", "")
    num_responses = int(data.get("num_responses", 3))

    try:
        board = chess.Board(fen)
    except Exception:
        return jsonify({"error": "invalid FEN"}), 400

    try:
        raw = engine_manager.analyze(fen, time_sec=1.5, multipv=num_responses)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    book_entry = opening_book.lookup(fen)
    book_candidates = (
        book_entry.get("candidate_explanations", {}) if book_entry else {}
    )

    responses = []
    for c in raw:
        move = chess.Move.from_uci(c["uci"])

        # Check if the resulting position lands in the opening book
        board_after = board.copy()
        board_after.push(move)
        result_entry = opening_book.lookup(board_after.fen())

        book_info = book_candidates.get(c["san"], {})
        prose = explainer.explain_move(board, move, book_info.get("prose"))

        resulting_opening = ""
        if result_entry:
            name = result_entry.get("opening_name", "")
            variation = result_entry.get("variation_name", "")
            resulting_opening = f"{name} — {variation}" if variation else name

        responses.append({
            "san": c["san"],
            "score_cp": c["score_cp"],
            "explanation": prose,
            "label": book_info.get("label", ""),
            "follow_up_idea": book_info.get("follow_up_idea", ""),
            "resulting_opening": resulting_opening,
            "in_book": result_entry is not None,
        })

    return jsonify({"responses": responses})


@app.get("/api/legal-moves")
def api_legal_moves():
    """Return all legal moves for a position in SAN notation.

    This endpoint exists as a fallback; the frontend uses chess.js for
    move validation and does not normally call this route.

    Query params:
        fen (str): URL-encoded FEN of the position.

    Returns:
        JSON ``{"moves": [<san>, …]}``.

    HTTP errors:
        400: Invalid FEN.
    """
    fen = request.args.get("fen", "")
    try:
        board = chess.Board(fen)
    except Exception:
        return jsonify({"error": "invalid FEN"}), 400
    moves = [board.san(m) for m in board.legal_moves]
    return jsonify({"moves": moves})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Starting Stockfish engine...")
    engine_manager.get_engine()
    print("Engine ready. Starting Flask on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
