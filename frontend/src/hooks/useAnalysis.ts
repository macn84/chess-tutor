/**
 * Analysis data hook for Chess Tutor.
 *
 * Triggers two independent fetch flows on each FEN change:
 *
 * 1. **Opening lookup** — instant book hit, fires immediately.
 * 2. **Stockfish analysis** — debounced 150 ms to avoid hammering the engine
 *    while the user is navigating the move history quickly.
 *
 * A third effect watches ``lastMoveUci`` to load opponent responses after
 * each user move.
 *
 * All three use {@link AbortController} so that stale requests from a
 * previous position are cancelled before a new one starts.
 */

import { useState, useEffect, useRef } from 'react'
import { fetchOpening, fetchAnalysis, fetchOpponentResponses } from '../api'
import type { OpeningEntry, AnalysisResult, OpponentResponsesResult } from '../types'

/** Return value of {@link useAnalysis}. */
export interface UseAnalysisReturn {
  /** Opening-book result for the current FEN.  Null while the first request
   *  is in-flight. */
  opening: OpeningEntry | null
  /** Stockfish analysis for the current FEN.  Null while loading. */
  analysis: AnalysisResult | null
  /** Top opponent replies after the last user move.  Null until computed. */
  opponentResponses: OpponentResponsesResult | null
  /** True while the Stockfish analysis request is in-flight. */
  loadingAnalysis: boolean
  /** True while the opponent-responses request is in-flight. */
  loadingResponses: boolean
}

/**
 * Manage opening, analysis, and opponent-response data for a given position.
 *
 * @param fen - FEN of the position currently on the board.
 * @param lastMoveUci - UCI of the last move played; null at start or after reset.
 * @returns Derived data and loading flags.  See {@link UseAnalysisReturn}.
 */
export function useAnalysis(
  fen: string,
  lastMoveUci: string | null,
): UseAnalysisReturn {
  const [opening, setOpening] = useState<OpeningEntry | null>(null)
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [opponentResponses, setOpponentResponses] =
    useState<OpponentResponsesResult | null>(null)
  const [loadingAnalysis, setLoadingAnalysis] = useState(false)
  const [loadingResponses, setLoadingResponses] = useState(false)

  const analysisAbort = useRef<AbortController | null>(null)
  const responsesAbort = useRef<AbortController | null>(null)
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Opening lookup + analysis on every FEN change
  useEffect(() => {
    if (analysisAbort.current) analysisAbort.current.abort()
    if (responsesAbort.current) responsesAbort.current.abort()
    if (debounceTimer.current) clearTimeout(debounceTimer.current)

    setAnalysis(null)
    setOpponentResponses(null)

    const ac1 = new AbortController()
    analysisAbort.current = ac1

    // Opening lookup is fast (in-memory dict) — fire immediately
    fetchOpening(fen, ac1.signal)
      .then(setOpening)
      .catch(() => {})

    // Debounce Stockfish so rapid navigation doesn't queue many engine calls
    debounceTimer.current = setTimeout(() => {
      setLoadingAnalysis(true)
      const ac2 = new AbortController()
      analysisAbort.current = ac2

      fetchAnalysis(fen, ac2.signal)
        .then((res) => {
          setAnalysis(res)
          setLoadingAnalysis(false)
        })
        .catch((err) => {
          if (err.name !== 'AbortError') setLoadingAnalysis(false)
        })
    }, 150)

    return () => {
      ac1.abort()
      if (debounceTimer.current) clearTimeout(debounceTimer.current)
    }
  }, [fen])

  // Opponent responses fire after each user move (tied to lastMoveUci, not fen)
  useEffect(() => {
    if (!lastMoveUci) {
      setOpponentResponses(null)
      return
    }

    if (responsesAbort.current) responsesAbort.current.abort()
    const ac = new AbortController()
    responsesAbort.current = ac
    setLoadingResponses(true)

    // fen is already *after* the user's move, so the opponent is to move next
    fetchOpponentResponses(fen, lastMoveUci, ac.signal)
      .then((res) => {
        setOpponentResponses(res)
        setLoadingResponses(false)
      })
      .catch((err) => {
        if (err.name !== 'AbortError') setLoadingResponses(false)
      })

    return () => ac.abort()
  }, [lastMoveUci, fen])

  return { opening, analysis, opponentResponses, loadingAnalysis, loadingResponses }
}
