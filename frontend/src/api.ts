/**
 * API client for the Chess Tutor Flask backend.
 *
 * All functions accept an optional {@link AbortSignal} so callers can cancel
 * stale requests when the user navigates rapidly.  The Vite dev proxy
 * forwards ``/api`` to ``http://localhost:5000``, so no base-URL config is
 * needed.
 */

import type { AnalysisResult, OpeningEntry, OpponentResponsesResult } from './types'

/**
 * Look up a position in the opening book (fast, no engine call).
 *
 * @param fen - FEN string of the position to look up.
 * @param signal - Optional abort signal to cancel the request.
 * @returns Opening entry; ``found: false`` when not in the book.
 */
export async function fetchOpening(
  fen: string,
  signal?: AbortSignal,
): Promise<OpeningEntry> {
  const res = await fetch(`/api/opening?fen=${encodeURIComponent(fen)}`, {
    signal,
  })
  if (!res.ok) throw new Error('opening fetch failed')
  return res.json()
}

/**
 * Run Stockfish multi-PV analysis and retrieve ranked candidates with prose.
 *
 * Stockfish is given 1.5 s per call.  Expect ~1.5 s latency on first load
 * and when the engine is cold.
 *
 * @param fen - FEN string of the position to analyse.
 * @param signal - Optional abort signal to cancel the request.
 * @returns Analysis result with up to 4 candidate moves.
 */
export async function fetchAnalysis(
  fen: string,
  signal?: AbortSignal,
): Promise<AnalysisResult> {
  const res = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fen, num_candidates: 4 }),
    signal,
  })
  if (!res.ok) throw new Error('analysis fetch failed')
  return res.json()
}

/**
 * Fetch the top opponent replies after the user's last move.
 *
 * The backend analyses from the current FEN (which is the opponent's turn)
 * and returns the top 3 engine moves enriched with teaching prose.
 *
 * @param fen - FEN after the user's last move (opponent to move).
 * @param your_move_uci - The user's last move in UCI notation (metadata only).
 * @param signal - Optional abort signal to cancel the request.
 * @returns Up to 3 annotated opponent responses.
 */
export async function fetchOpponentResponses(
  fen: string,
  your_move_uci: string,
  signal?: AbortSignal,
): Promise<OpponentResponsesResult> {
  const res = await fetch('/api/opponent-responses', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fen, your_move_uci, num_responses: 3 }),
    signal,
  })
  if (!res.ok) throw new Error('opponent responses fetch failed')
  return res.json()
}
