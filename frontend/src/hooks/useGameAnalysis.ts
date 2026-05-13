/**
 * State machine hook for the My Games analysis flow.
 *
 * Stages: idle → fetching → analyzing → done (or error)
 */

import { useState, useRef, useCallback } from 'react'
import type {
  GameFilter,
  FetchedGame,
  AnalysisPatterns,
  CoachingInsightsResult,
} from '../types'
import {
  fetchPlayerGames,
  startAnalysisJob,
  pollJobStatus,
  fetchAnalysisResults,
} from '../api'

export type AnalysisStage = 'idle' | 'fetching' | 'analyzing' | 'done' | 'error'

export interface AnalysisProgress {
  analyzedCount: number;
  total: number;
  progress: number;
}

export interface GameAnalysisState {
  stage: AnalysisStage;
  error: string | null;
  gameCount: number;
  progress: AnalysisProgress | null;
  patterns: AnalysisPatterns | null;
  insights: CoachingInsightsResult | null;
}

export interface GameAnalysisActions {
  run: (filter: GameFilter) => void;
  reset: () => void;
}

const INITIAL_STATE: GameAnalysisState = {
  stage: 'idle',
  error: null,
  gameCount: 0,
  progress: null,
  patterns: null,
  insights: null,
}

export function useGameAnalysis(): [GameAnalysisState, GameAnalysisActions] {
  const [state, setState] = useState<GameAnalysisState>(INITIAL_STATE)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const run = useCallback(
    async (filter: GameFilter) => {
      stopPolling()
      setState({ ...INITIAL_STATE, stage: 'fetching' })

      // --- Phase 1: Fetch games from Chess.com ---
      let games: FetchedGame[]
      try {
        const res = await fetchPlayerGames(filter)
        games = res.games
        if (games.length === 0) {
          setState((s) => ({ ...s, stage: 'error', error: 'No games found for the selected filters.' }))
          return
        }
        setState((s) => ({ ...s, gameCount: games.length, stage: 'analyzing' }))
      } catch (err) {
        setState((s) => ({
          ...s,
          stage: 'error',
          error: err instanceof Error ? err.message : 'Failed to fetch games.',
        }))
        return
      }

      // --- Phase 2: Start analysis job ---
      let jobId: string
      try {
        const res = await startAnalysisJob(games)
        jobId = res.job_id
      } catch (err) {
        setState((s) => ({
          ...s,
          stage: 'error',
          error: err instanceof Error ? err.message : 'Failed to start analysis.',
        }))
        return
      }

      // --- Phase 3: Poll until done ---
      setState((s) => ({
        ...s,
        progress: { analyzedCount: 0, total: games.length, progress: 0 },
      }))

      pollRef.current = setInterval(async () => {
        try {
          const status = await pollJobStatus(jobId)
          setState((s) => ({
            ...s,
            progress: {
              analyzedCount: status.analyzed_count,
              total: status.total,
              progress: status.progress,
            },
          }))

          if (status.status === 'done') {
            stopPolling()
            const results = await fetchAnalysisResults(jobId)
            setState((s) => ({
              ...s,
              stage: 'done',
              patterns: results.patterns,
              insights: results.insights,
            }))
          } else if (status.status === 'error') {
            stopPolling()
            setState((s) => ({
              ...s,
              stage: 'error',
              error: status.error ?? 'Analysis failed on the server.',
            }))
          }
        } catch {
          // transient poll failure — keep trying
        }
      }, 2000)
    },
    [stopPolling],
  )

  const reset = useCallback(() => {
    stopPolling()
    setState(INITIAL_STATE)
  }, [stopPolling])

  return [state, { run, reset }]
}
