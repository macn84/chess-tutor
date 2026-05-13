/**
 * Chess board panel component.
 *
 * Thin wrapper around react-chessboard v5.  The v5 API uses a single
 * ``options`` object instead of flat props, and ``onPieceDrop`` receives an
 * object with a {@link DraggingPieceDataType} rather than a plain string for
 * the piece.
 */

import { Chessboard } from 'react-chessboard'

/** Props for {@link ChessBoardPanel}. */
interface Props {
  /** FEN string of the position to display. */
  fen: string
  /** Which colour is rendered at the bottom of the board. */
  orientation: 'white' | 'black'
  /**
   * Called when the user drops a piece onto a target square.
   *
   * @param from - Origin square (e.g. "e2").
   * @param to - Destination square (e.g. "e4").
   * @param promotion - Promotion piece type when a pawn reaches the back rank.
   * @returns ``true`` to confirm the move; ``false`` to snap the piece back.
   */
  onMove: (from: string, to: string, promotion?: string) => boolean
  /**
   * Per-square CSS style overrides for highlighting (last move, checks, etc.).
   * Keyed by square name (e.g. ``{ e2: { background: 'rgba(255,206,68,0.5)' } }``).
   */
  customSquareStyles?: Record<string, React.CSSProperties>
}

/**
 * Interactive chess board sized to a maximum of 560 px.
 *
 * @param props - {@link Props}
 */
export function ChessBoardPanel({
  fen,
  orientation,
  onMove,
  customSquareStyles,
}: Props) {
  return (
    <div style={{ width: '100%', maxWidth: 560 }}>
      <Chessboard
        options={{
          position: fen,
          boardOrientation: orientation,
          squareStyles: customSquareStyles,
          boardStyle: {
            borderRadius: 6,
            boxShadow: '0 4px 24px rgba(0,0,0,0.35)',
          },
          darkSquareStyle: { backgroundColor: '#769656' },
          lightSquareStyle: { backgroundColor: '#eeeed2' },
          animationDurationInMs: 150,
          onPieceDrop: ({ piece, sourceSquare, targetSquare }) => {
            if (!targetSquare) return false
            // piece.pieceType is e.g. "wP" — index 1 is the piece letter
            const pieceType = piece.pieceType ?? ''
            const isPromotion =
              pieceType[1]?.toUpperCase() === 'P' &&
              (targetSquare[1] === '8' || targetSquare[1] === '1')
            return onMove(
              sourceSquare,
              targetSquare,
              isPromotion ? 'q' : undefined,
            )
          },
        }}
      />
    </div>
  )
}
