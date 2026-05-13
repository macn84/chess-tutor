/**
 * Core game-state hook for Chess Tutor.
 *
 * Manages the navigable move history, current board FEN, board orientation,
 * and the last-move UCI (used to compute highlighting squares).
 *
 * State transitions are handled by a pure reducer so that navigation is
 * always deterministic and testable without DOM.
 */

import { useReducer, useCallback } from 'react'
import { Chess } from 'chess.js'
import type { GameMove } from '../types'

const START_FEN =
  'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

/** Complete snapshot of game state stored in the reducer. */
export interface GameState {
  /** Full move history (index 0 = move 1 by White). */
  history: GameMove[]
  /** Index of the move currently displayed on the board (-1 = start position). */
  currentIndex: number
  /** FEN of the position currently on the board. */
  fen: string
  /** Which colour is at the bottom of the board. */
  orientation: 'white' | 'black'
  /** UCI of the last move played/navigated-to, for highlighting. Null at start. */
  lastMoveUci: string | null
}

type Action =
  | { type: 'MOVE'; move: GameMove }
  | { type: 'NAVIGATE'; index: number }
  | { type: 'FLIP_BOARD' }
  | { type: 'RESET' }

function reducer(state: GameState, action: Action): GameState {
  switch (action.type) {
    case 'MOVE': {
      // Truncate future history when branching from a mid-game position
      const newHistory = state.history.slice(0, state.currentIndex + 1)
      newHistory.push(action.move)
      return {
        ...state,
        history: newHistory,
        currentIndex: newHistory.length - 1,
        fen: action.move.fen_after,
        lastMoveUci: action.move.uci,
      }
    }
    case 'NAVIGATE': {
      const idx = Math.max(-1, Math.min(action.index, state.history.length - 1))
      const fen = idx === -1 ? START_FEN : state.history[idx].fen_after
      const lastMoveUci = idx >= 0 ? state.history[idx].uci : null
      return { ...state, currentIndex: idx, fen, lastMoveUci }
    }
    case 'FLIP_BOARD':
      return {
        ...state,
        orientation: state.orientation === 'white' ? 'black' : 'white',
      }
    case 'RESET':
      return {
        history: [],
        currentIndex: -1,
        fen: START_FEN,
        orientation: state.orientation,
        lastMoveUci: null,
      }
    default:
      return state
  }
}

/**
 * Return value of {@link useGameState}.
 */
export interface UseGameStateReturn {
  state: GameState
  /**
   * Attempt a move on the current board position.
   *
   * Validates with chess.js locally.  Returns ``true`` and updates state
   * on a legal move; returns ``false`` without side-effects on an illegal one.
   *
   * @param sourceSquare - Origin square in algebraic notation (e.g. "e2").
   * @param targetSquare - Destination square (e.g. "e4").
   * @param promotion - Promotion piece type (e.g. "q").  Defaults to queen.
   */
  makeMove: (
    sourceSquare: string,
    targetSquare: string,
    promotion?: string,
  ) => boolean
  /**
   * Jump to a position in the move history.
   *
   * @param index - History index to show (-1 for the starting position).
   */
  navigate: (index: number) => void
  /** Toggle board orientation between White-at-bottom and Black-at-bottom. */
  flipBoard: () => void
  /** Reset to starting position, preserving board orientation. */
  reset: () => void
  /**
   * Square-style map for highlighting the last-move squares.
   *
   * Pass directly to ``<ChessBoardPanel customSquareStyles={…} />``.
   */
  lastMoveSquares: Record<string, { background: string }>
}

/**
 * Manage chess game state with navigable move history.
 *
 * @returns Game state and action callbacks.  See {@link UseGameStateReturn}.
 */
export function useGameState(): UseGameStateReturn {
  const [state, dispatch] = useReducer(reducer, {
    history: [],
    currentIndex: -1,
    fen: START_FEN,
    orientation: 'white',
    lastMoveUci: null,
  })

  const makeMove = useCallback(
    (
      sourceSquare: string,
      targetSquare: string,
      promotion?: string,
    ): boolean => {
      const chess = new Chess(state.fen)
      try {
        const move = chess.move({
          from: sourceSquare,
          to: targetSquare,
          promotion: promotion ?? 'q',
        })
        if (!move) return false
        dispatch({
          type: 'MOVE',
          move: {
            san: move.san,
            uci: sourceSquare + targetSquare + (promotion ?? ''),
            fen_after: chess.fen(),
          },
        })
        return true
      } catch {
        return false
      }
    },
    [state.fen],
  )

  const navigate = useCallback(
    (index: number) => dispatch({ type: 'NAVIGATE', index }),
    [],
  )
  const flipBoard = useCallback(() => dispatch({ type: 'FLIP_BOARD' }), [])
  const reset = useCallback(() => dispatch({ type: 'RESET' }), [])

  const lastMoveSquares: Record<string, { background: string }> = {}
  if (state.lastMoveUci) {
    const from = state.lastMoveUci.slice(0, 2)
    const to = state.lastMoveUci.slice(2, 4)
    lastMoveSquares[from] = { background: 'rgba(255, 206, 68, 0.5)' }
    lastMoveSquares[to] = { background: 'rgba(255, 206, 68, 0.5)' }
  }

  return { state, makeMove, navigate, flipBoard, reset, lastMoveSquares }
}
