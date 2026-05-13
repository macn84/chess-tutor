"""Flask application: Chess Tutor API.

Exposes four original endpoints plus four game-analysis endpoints:

- ``GET  /api/opening``           — Fast opening-book lookup (no engine).
- ``POST /api/analyze``           — Stockfish multi-PV analysis with prose.
- ``POST /api/opponent-responses``— Top engine replies from opponent's view.
- ``GET  /api/legal-moves``       — All legal SAN moves for a position.
- ``POST /api/games/fetch``       — Fetch player games from Chess.com.
- ``POST /api/games/analyze``     — Start batch Stockfish blunder analysis job.
- ``GET  /api/games/status/<id>`` — Poll job progress.
- ``GET  /api/games/results/<id>``— Retrieve completed analysis results.
"""

import os
import threading
import time
import uuid
from datetime import date

from flask import Flask, request, jsonify
from flask_cors import CORS
import chess
import chess.engine

import engine_manager
import explainer
import opening_book
import game_fetcher
import game_analyzer
import pattern_detector
import insights_generator

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# Background job store for batch analysis
# ---------------------------------------------------------------------------

_job_store: dict[str, dict] = {}
_job_lock = threading.Lock()
_JOB_TTL_SEC = 1800  # expire jobs after 30 minutes


def _cleanup_jobs() -> None:
    """Remove jobs older than TTL. Runs in a daemon thread."""
    while True:
        time.sleep(300)
        cutoff = time.time() - _JOB_TTL_SEC
        with _job_lock:
            expired = [jid for jid, j in _job_store.items() if j.get("created_at", 0) < cutoff]
            for jid in expired:
                del _job_store[jid]


threading.Thread(target=_cleanup_jobs, daemon=True).start()


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
# Game analysis routes
# ---------------------------------------------------------------------------


@app.post("/api/games/fetch")
def api_games_fetch():
    """Fetch and filter a player's games from Chess.com.

    Request body (JSON):
        start_date (str): ISO date "YYYY-MM-DD".
        end_date (str): ISO date "YYYY-MM-DD".
        time_class (str, optional): rapid|blitz|bullet|daily|all (default all).
        color (str, optional): white|black|both (default both).
        result (str, optional): win|loss|draw|all (default all).
        termination (str, optional): all|checkmate|resignation|timeout|abandonment|
            draw_agreement|draw_repetition|draw_stalemate|draw_50move|draw_insufficient
        rated (str, optional): all|rated|unrated (default all).
        min_opponent_rating (int, optional): Exclude games vs weaker opponents.
        max_opponent_rating (int, optional): Exclude games vs stronger opponents.
        max_games (int, optional): 5|25|50|100|200 (default 100).

    Username is read from the ``CHESS_COM_USERNAME`` environment variable.

    Returns:
        JSON with ``games`` list (summaries) and ``count``.
    """
    username = os.environ.get("CHESS_COM_USERNAME", "").strip()
    if not username:
        return jsonify({"error": "CHESS_COM_USERNAME not configured"}), 400
    data = request.get_json(force=True)

    try:
        start = date.fromisoformat(data.get("start_date", ""))
        end = date.fromisoformat(data.get("end_date", ""))
    except (ValueError, TypeError):
        return jsonify({"error": "start_date and end_date must be YYYY-MM-DD"}), 400

    if start > end:
        return jsonify({"error": "start_date must be before end_date"}), 400

    raw_max = data.get("max_games", 100)
    try:
        max_games = int(raw_max)
    except (ValueError, TypeError):
        max_games = 100
    max_games = min(max(max_games, 1), 200)

    min_opp = data.get("min_opponent_rating")
    max_opp = data.get("max_opponent_rating")

    try:
        games = game_fetcher.fetch_games(
            username=username,
            start_date=start,
            end_date=end,
            time_class=data.get("time_class", "all"),
            color=data.get("color", "both"),
            result=data.get("result", "all"),
            termination=data.get("termination", "all"),
            rated=data.get("rated", "all"),
            min_opponent_rating=int(min_opp) if min_opp is not None else None,
            max_opponent_rating=int(max_opp) if max_opp is not None else None,
            max_games=max_games,
        )
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify({"games": games, "count": len(games)})


@app.post("/api/games/analyze")
def api_games_analyze():
    """Start a background batch analysis job.

    Request body (JSON):
        games (list): Game dicts as returned by /api/games/fetch (must include pgn).

    Username is read from the ``CHESS_COM_USERNAME`` environment variable.

    Returns:
        JSON with ``job_id`` to poll.
    """
    username = os.environ.get("CHESS_COM_USERNAME", "").strip()
    if not username:
        return jsonify({"error": "CHESS_COM_USERNAME not configured"}), 400
    data = request.get_json(force=True)
    games = data.get("games", [])

    if not games:
        return jsonify({"error": "games are required"}), 400
    if len(games) > 200:
        return jsonify({"error": "maximum 200 games per analysis"}), 400

    job_id = str(uuid.uuid4())
    job: dict = {
        "status": "running",
        "progress": 0.0,
        "analyzed_count": 0,
        "total": len(games),
        "created_at": time.time(),
    }
    with _job_lock:
        _job_store[job_id] = job

    def _run():
        try:
            game_analyzer.analyze_games(games, username, job, job_id)
            # After analysis, build patterns and insights and attach to job
            analyzed = job.get("analyzed_games", [])
            patterns = pattern_detector.detect_patterns(analyzed, username)
            insights = insights_generator.generate_insights(patterns, analyzed)
            job["patterns"] = patterns
            job["insights"] = insights
            if insights.get("debug_payload"):
                job["debug_payload"] = insights["debug_payload"]
            job["status"] = "done"
        except Exception as exc:
            job["status"] = "error"
            job["error"] = str(exc)

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"job_id": job_id, "total": len(games)})


@app.get("/api/games/status/<job_id>")
def api_games_status(job_id: str):
    """Poll the status of a batch analysis job.

    Returns:
        JSON with ``status``, ``progress`` (0–1), ``analyzed_count``, ``total``.
    """
    with _job_lock:
        job = _job_store.get(job_id)
    if job is None:
        return jsonify({"error": "job not found"}), 404

    return jsonify({
        "status": job.get("status", "running"),
        "progress": job.get("progress", 0.0),
        "analyzed_count": job.get("analyzed_count", 0),
        "total": job.get("total", 0),
        "error": job.get("error"),
    })


@app.get("/api/games/results/<job_id>")
def api_games_results(job_id: str):
    """Retrieve completed analysis results.

    Returns:
        JSON with ``patterns`` and ``insights`` when status is done.
    """
    with _job_lock:
        job = _job_store.get(job_id)
    if job is None:
        return jsonify({"error": "job not found"}), 404
    if job.get("status") != "done":
        return jsonify({"error": "job not complete", "status": job.get("status")}), 202

    return jsonify({
        "patterns": job.get("patterns", {}),
        "insights": job.get("insights", {}),
        "debug_payload": job.get("debug_payload"),
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Starting Stockfish engine...")
    engine_manager.get_engine()
    print("Engine ready. Starting Flask on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
