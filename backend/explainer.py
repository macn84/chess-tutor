"""Template-based move explanation engine.

Generates human-readable prose describing a chess move without calling any
external API.  Uses python-chess move properties (piece type, captures,
checks, central pawn pushes, development squares) to tag moves, then
assembles natural-language sentences from those tags.

When an opening-book prose string is supplied it takes full priority over the
template system — the templates only fire for out-of-book positions.
"""

import chess

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PIECE_NAMES: dict[int, str] = {
    chess.PAWN: "pawn",
    chess.KNIGHT: "knight",
    chess.BISHOP: "bishop",
    chess.ROOK: "rook",
    chess.QUEEN: "queen",
    chess.KING: "king",
}

_CENTER_SQUARES: frozenset[int] = frozenset({
    chess.E4, chess.D4, chess.E5, chess.D5,
})

# "Natural" development squares where piece activity is high in the opening
_NATURAL_DEVELOPMENT: dict[bool, dict[int, frozenset[int]]] = {
    chess.WHITE: {
        chess.KNIGHT: frozenset({chess.F3, chess.C3, chess.E2}),
        chess.BISHOP: frozenset({chess.C4, chess.B5, chess.E2, chess.D3}),
    },
    chess.BLACK: {
        chess.KNIGHT: frozenset({chess.F6, chess.C6, chess.E7}),
        chess.BISHOP: frozenset({chess.C5, chess.B4, chess.E7, chess.D6}),
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def explain_move(
    board: chess.Board,
    move: chess.Move,
    book_explanation: str | None = None,
) -> str:
    """Produce a one-sentence prose explanation for a chess move.

    Prefers the supplied ``book_explanation`` when available; falls back to
    template-based prose derived from move properties.

    Args:
        board: Position *before* the move is played.
        move: The move to explain.
        book_explanation: Optional hand-written prose from the opening book.
            When truthy, returned verbatim without further processing.

    Returns:
        A human-readable explanation string ending in a full stop.
    """
    if book_explanation:
        return book_explanation

    tags = _tag_move(board, move)
    return _assemble_prose(board, move, tags)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _tag_move(board: chess.Board, move: chess.Move) -> list[str]:
    """Analyse a move and return descriptive string tags.

    Tags are single-word identifiers used by ``_assemble_prose`` to select
    appropriate sentence fragments.  Multiple tags may apply to one move.

    Args:
        board: Position before the move.
        move: Move to tag.

    Returns:
        List of tag strings (e.g. ``["central_pawn", "controls_center"]``).
        Returns an empty list if the origin square has no piece.
    """
    tags: list[str] = []
    piece = board.piece_at(move.from_square)
    if piece is None:
        return tags

    # Captures
    if board.is_capture(move):
        captured = board.piece_at(move.to_square)
        if captured:
            captured_name = _PIECE_NAMES.get(captured.piece_type, "piece")
            tags.append(f"captures_{captured_name}")

    # Check / mate — push onto a copy so we don't mutate the caller's board
    board_copy = board.copy()
    board_copy.push(move)
    if board_copy.is_checkmate():
        tags.append("checkmate")
    elif board_copy.is_check():
        tags.append("gives_check")

    # Castling has unique prose; return early to avoid conflating tags
    if board.is_castling(move):
        tags.append("castles")
        return tags

    # Central pawn advance
    if piece.piece_type == chess.PAWN and move.to_square in _CENTER_SQUARES:
        tags.append("central_pawn")

    # Development to a principled opening square
    natural_squares = (
        _NATURAL_DEVELOPMENT
        .get(piece.color, {})
        .get(piece.piece_type, frozenset())
    )
    if move.to_square in natural_squares and piece.piece_type in (
        chess.KNIGHT, chess.BISHOP
    ):
        tags.append("develops_piece")

    tags.append(f"moves_{_PIECE_NAMES.get(piece.piece_type, 'piece')}")

    # Post-move central influence
    if any(
        board_copy.is_attacked_by(piece.color, sq) for sq in _CENTER_SQUARES
    ):
        tags.append("controls_center")

    return tags


def _assemble_prose(
    board: chess.Board,
    move: chess.Move,
    tags: list[str],
) -> str:
    """Build a prose sentence from a tagged move.

    Args:
        board: Position before the move (used to read the moving piece).
        move: The move being described.
        tags: Tags produced by ``_tag_move``.

    Returns:
        A natural-language sentence ending in ``'.'``, or an empty string if
        the origin square has no piece.
    """
    piece = board.piece_at(move.from_square)
    if piece is None:
        return ""

    piece_name = _PIECE_NAMES.get(piece.piece_type, "piece").capitalize()
    to_sq = chess.square_name(move.to_square)

    if "checkmate" in tags:
        return f"{piece_name} to {to_sq} delivers checkmate."

    if "castles" in tags:
        side = "kingside" if move.to_square > move.from_square else "queenside"
        return (
            f"{side.capitalize()} castling: the king moves to safety and the "
            f"rook becomes active. A key moment in development."
        )

    parts: list[str] = []

    if "central_pawn" in tags:
        parts.append("Stakes a claim in the center")
    elif "develops_piece" in tags:
        parts.append(
            f"Develops the {piece_name.lower()} to its most natural square "
            f"({to_sq})"
        )
    elif "captures_queen" in tags:
        parts.append("Wins the queen")
    elif "captures_rook" in tags:
        parts.append("Wins the exchange (captures the rook)")
    elif "captures_bishop" in tags or "captures_knight" in tags:
        parts.append("Captures a minor piece")
    elif "captures_pawn" in tags:
        parts.append("Captures a pawn")
    else:
        parts.append(f"Moves the {piece_name.lower()} to {to_sq}")

    if "gives_check" in tags:
        parts.append("giving check")

    if "controls_center" in tags and "central_pawn" not in tags:
        parts.append("increasing central control")

    return ", ".join(parts) + "."
