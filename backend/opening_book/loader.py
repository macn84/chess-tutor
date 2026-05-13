"""Opening book loader.

Loads ``book.json`` once at startup into an in-memory dict keyed by
normalised FEN (4 fields — side to move, castling rights, en-passant square,
but NOT half-move clock or full-move number).

Normalising to 4 fields makes lookup transposition-safe: the same position
reached via different move orders maps to the same key.
"""

import json
from pathlib import Path

_BOOK_PATH = Path(__file__).parent / "book.json"
_index: dict[str, dict] = {}
_loaded: bool = False


def _normalize_fen(fen: str) -> str:
    """Return the first four space-separated fields of a FEN string.

    Strips half-move clock and full-move number so transpositions share a key.

    Args:
        fen: A full FEN string (6 fields) or any prefix thereof.

    Returns:
        A string of the form ``"<pieces> <side> <castling> <ep>"``.
    """
    parts = fen.split()
    return " ".join(parts[:4])


def _load() -> None:
    """Load ``book.json`` into ``_index`` exactly once (lazy, thread-unsafe).

    Safe for single-threaded Flask (one worker process) or for multi-threaded
    Flask when called during app startup before requests are served.  A race
    on the first request is benign — both threads would load identical data.
    """
    global _index, _loaded
    if _loaded:
        return
    with open(_BOOK_PATH, encoding="utf-8") as f:
        data = json.load(f)
    for entry in data.get("entries", []):
        key = entry["fen_key"]
        _index[key] = entry
    _loaded = True


def lookup(fen: str) -> dict | None:
    """Find the opening-book entry for a position.

    Args:
        fen: FEN string of the position to look up (any standard format).

    Returns:
        The matching entry dict, or ``None`` if the position is not in the
        book.
    """
    _load()
    key = _normalize_fen(fen)
    return _index.get(key)


def get_all_entries() -> list[dict]:
    """Return every entry in the opening book.

    Returns:
        List of all book entry dicts in arbitrary order.
    """
    _load()
    return list(_index.values())
