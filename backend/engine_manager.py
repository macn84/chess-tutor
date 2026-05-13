"""Persistent Stockfish engine singleton for Flask backend.

Manages one ``chess.engine.SimpleEngine`` process for the lifetime of the
Flask server.  Lazy-initialises on first call and restarts automatically if
the process dies.

Critical constraints
--------------------
- ``analyse()`` must NOT be called while holding ``_lock``.  SimpleEngine uses
  asyncio background threads internally; acquiring an external Lock inside
  that context causes a deadlock.
- Use ``Limit(time=…)`` not ``Limit(depth=…)``.  Depth-based limits with
  multipv>1 take >30 s on this hardware.
"""

import atexit
import threading
import chess
import chess.engine

STOCKFISH_PATH = (
    "/home/andrew/workshop/chess/chess-analysis-tool/data/src/stockfish"
)

_engine: chess.engine.SimpleEngine | None = None
# _lock guards only the initialisation/restart critical section, never analyse()
_lock = threading.Lock()


def _start_engine() -> chess.engine.SimpleEngine:
    """Spawn a new Stockfish process and return the engine handle.

    Returns:
        A ready-to-use ``chess.engine.SimpleEngine`` instance.
    """
    return chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)


def get_engine() -> chess.engine.SimpleEngine:
    """Return the singleton engine, initialising it on first call.

    Thread-safe via double-checked locking; only the first caller pays the
    ~275 ms startup cost.

    Returns:
        The shared ``chess.engine.SimpleEngine`` instance.
    """
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = _start_engine()
    return _engine


def analyze(fen: str, time_sec: float = 1.5, multipv: int = 4) -> list[dict]:
    """Run Stockfish multi-PV analysis and return ranked candidate moves.

    Calls ``engine.analyse()`` without an external lock — SimpleEngine is
    internally thread-safe.  If the engine process is dead, restarts it once
    and retries.

    Args:
        fen: FEN string of the position to analyse.
        time_sec: Wall-clock seconds to allow Stockfish per call.
        multipv: Number of distinct lines to return.

    Returns:
        List of candidate dicts, each containing:
            - ``uci`` (str): Move in UCI notation.
            - ``san`` (str): Move in standard algebraic notation.
            - ``score_cp`` (int): Centipawn score from White's perspective.
            - ``pv_san`` (list[str]): Principal variation in SAN (up to 6 ply).

    Raises:
        Exception: Re-raised if analysis fails after one restart attempt.
    """
    engine = get_engine()
    board = chess.Board(fen)
    limit = chess.engine.Limit(time=time_sec)

    try:
        results = engine.analyse(board, limit, multipv=multipv)
    except Exception:
        # Engine process died; restart and retry once
        global _engine
        with _lock:
            try:
                _engine.quit()
            except Exception:
                pass
            _engine = _start_engine()
        results = _engine.analyse(board, limit, multipv=multipv)

    candidates = []
    for info in results:
        pv = info.get("pv", [])
        move = pv[0] if pv else None
        if move is None:
            continue
        score = info.get("score")
        if score is None:
            continue

        cp = score.white().score(mate_score=10000)
        pv_san = _pv_to_san(board, pv[:6])

        candidates.append({
            "uci": move.uci(),
            "san": board.san(move),
            "score_cp": cp if cp is not None else 0,
            "pv_san": pv_san,
        })

    return candidates


def _pv_to_san(board: chess.Board, pv: list[chess.Move]) -> list[str]:
    """Convert a principal variation of Move objects to SAN strings.

    Plays each move onto a copy of the board to generate context-correct SAN.
    Stops at the first illegal move encountered.

    Args:
        board: The position at the root of the variation.
        pv: Sequence of moves forming the variation.

    Returns:
        List of SAN strings, possibly shorter than ``pv`` if an illegal move
        is hit.
    """
    b = board.copy()
    san_list = []
    for move in pv:
        try:
            san_list.append(b.san(move))
            b.push(move)
        except Exception:
            break
    return san_list


@atexit.register
def _shutdown() -> None:
    """Quit Stockfish gracefully when the Python process exits."""
    global _engine
    if _engine:
        try:
            _engine.quit()
        except Exception:
            pass
