/**
 * Unit tests for the useGameState hook.
 *
 * Uses renderHook from @testing-library/react so the hook runs inside a
 * real React tree without a DOM render.
 */

import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useGameState } from '../hooks/useGameState'

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

describe('useGameState — initial state', () => {
  it('starts at the opening position', () => {
    const { result } = renderHook(() => useGameState())
    expect(result.current.state.fen).toBe(START_FEN)
  })

  it('starts with empty history', () => {
    const { result } = renderHook(() => useGameState())
    expect(result.current.state.history).toHaveLength(0)
  })

  it('starts with currentIndex -1', () => {
    const { result } = renderHook(() => useGameState())
    expect(result.current.state.currentIndex).toBe(-1)
  })

  it('starts with White orientation', () => {
    const { result } = renderHook(() => useGameState())
    expect(result.current.state.orientation).toBe('white')
  })

  it('starts with no last-move highlights', () => {
    const { result } = renderHook(() => useGameState())
    expect(result.current.lastMoveSquares).toEqual({})
  })
})

describe('useGameState — makeMove', () => {
  it('accepts a legal move and updates the FEN', () => {
    const { result } = renderHook(() => useGameState())
    let ok: boolean
    act(() => {
      ok = result.current.makeMove('e2', 'e4')
    })
    expect(ok!).toBe(true)
    expect(result.current.state.fen).not.toBe(START_FEN)
  })

  it('rejects an illegal move and keeps the FEN unchanged', () => {
    const { result } = renderHook(() => useGameState())
    let ok: boolean
    act(() => {
      ok = result.current.makeMove('e2', 'e5') // illegal — two-square push from e2 is fine but this is actually 3 squares
    })
    // e2→e5 is 3 squares — illegal
    expect(ok!).toBe(false)
    expect(result.current.state.fen).toBe(START_FEN)
  })

  it('adds the move to history', () => {
    const { result } = renderHook(() => useGameState())
    act(() => { result.current.makeMove('e2', 'e4') })
    expect(result.current.state.history).toHaveLength(1)
    expect(result.current.state.history[0].san).toBe('e4')
  })

  it('computes last-move highlight squares', () => {
    const { result } = renderHook(() => useGameState())
    act(() => { result.current.makeMove('e2', 'e4') })
    const squares = result.current.lastMoveSquares
    expect(squares['e2']).toBeDefined()
    expect(squares['e4']).toBeDefined()
  })

  it('truncates future history when branching', () => {
    const { result } = renderHook(() => useGameState())
    act(() => { result.current.makeMove('e2', 'e4') })
    act(() => { result.current.makeMove('e7', 'e5') })
    act(() => { result.current.navigate(0) }) // go back to after 1.e4
    act(() => { result.current.makeMove('d7', 'd5') }) // branch with 1…d5 instead
    expect(result.current.state.history).toHaveLength(2)
    expect(result.current.state.history[1].san).toBe('d5')
  })
})

describe('useGameState — navigate', () => {
  it('navigates back to the start position at index -1', () => {
    const { result } = renderHook(() => useGameState())
    act(() => { result.current.makeMove('e2', 'e4') })
    act(() => { result.current.navigate(-1) })
    expect(result.current.state.fen).toBe(START_FEN)
    expect(result.current.state.currentIndex).toBe(-1)
  })

  it('clamps negative indices to -1', () => {
    const { result } = renderHook(() => useGameState())
    act(() => { result.current.navigate(-99) })
    expect(result.current.state.currentIndex).toBe(-1)
  })

  it('clamps indices beyond history length', () => {
    const { result } = renderHook(() => useGameState())
    act(() => { result.current.makeMove('e2', 'e4') }) // history length = 1
    act(() => { result.current.navigate(100) })
    expect(result.current.state.currentIndex).toBe(0)
  })
})

describe('useGameState — flipBoard', () => {
  it('toggles orientation from white to black', () => {
    const { result } = renderHook(() => useGameState())
    act(() => { result.current.flipBoard() })
    expect(result.current.state.orientation).toBe('black')
  })

  it('toggles back to white on second flip', () => {
    const { result } = renderHook(() => useGameState())
    act(() => { result.current.flipBoard() })
    act(() => { result.current.flipBoard() })
    expect(result.current.state.orientation).toBe('white')
  })
})

describe('useGameState — reset', () => {
  it('clears history and returns to start FEN', () => {
    const { result } = renderHook(() => useGameState())
    act(() => { result.current.makeMove('e2', 'e4') })
    act(() => { result.current.makeMove('e7', 'e5') })
    act(() => { result.current.reset() })
    expect(result.current.state.fen).toBe(START_FEN)
    expect(result.current.state.history).toHaveLength(0)
  })

  it('preserves board orientation on reset', () => {
    const { result } = renderHook(() => useGameState())
    act(() => { result.current.flipBoard() }) // flip to black
    act(() => { result.current.reset() })
    expect(result.current.state.orientation).toBe('black')
  })
})
