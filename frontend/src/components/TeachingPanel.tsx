/**
 * Teaching panel component — the right-side column of the Chess Tutor UI.
 *
 * Composes three sub-panels vertically:
 * 1. **Opening badge** — ECO code, opening name, strategic ideas from the book.
 * 2. **Candidate moves** — Stockfish lines with prose, loaded with skeleton.
 * 3. **Opponent responses** — "If opponent plays…" accordion.
 */

import type { OpeningEntry, AnalysisResult, OpponentResponsesResult } from '../types'
import { CandidateMoves } from './CandidateMoves'
import { OpponentResponses } from './OpponentResponses'

/** Props for {@link TeachingPanel}. */
interface Props {
  /** Opening-book result for the current position. */
  opening: OpeningEntry | null
  /** Stockfish analysis for the current position. */
  analysis: AnalysisResult | null
  /** Engine-ranked opponent replies. */
  opponentResponses: OpponentResponsesResult | null
  /** True while Stockfish analysis is loading. */
  loadingAnalysis: boolean
  /** True while opponent-responses are loading. */
  loadingResponses: boolean
  /**
   * Play a move on the board (used by the CandidateMoves "Play" button).
   *
   * @param from - Origin square.
   * @param to - Destination square.
   * @param promotion - Optional promotion piece.
   * @returns ``true`` if the move was legal and applied.
   */
  onPlayMove: (from: string, to: string, promotion?: string) => boolean
  /**
   * Play a move given as SAN (used by the OpponentResponses "Play this line"
   * button).  chess.js resolves the SAN in the current position context.
   *
   * @param san - Move in standard algebraic notation.
   */
  onPlaySan: (san: string) => void
}

/**
 * Scrollable right-side teaching panel.
 *
 * @param props - {@link Props}
 */
export function TeachingPanel({
  opening,
  analysis,
  opponentResponses,
  loadingAnalysis,
  loadingResponses,
  onPlayMove,
  onPlaySan,
}: Props) {
  const hasOpening = opening?.found

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
        height: '100%',
        overflowY: 'auto',
        paddingRight: 4,
      }}
    >
      {/* Opening badge */}
      <div
        style={{
          background: '#252525',
          borderRadius: 6,
          padding: '10px 14px',
          borderLeft: '3px solid #769656',
        }}
      >
        {hasOpening ? (
          <>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                marginBottom: 4,
              }}
            >
              <span
                style={{
                  background: '#769656',
                  color: '#fff',
                  borderRadius: 3,
                  padding: '1px 6px',
                  fontSize: 11,
                  fontFamily: 'monospace',
                  fontWeight: 700,
                }}
              >
                {opening.eco}
              </span>
              <span style={{ color: '#ddd', fontSize: 14, fontWeight: 600 }}>
                {opening.opening_name}
              </span>
            </div>
            {opening.variation_name && (
              <div style={{ color: '#aaa', fontSize: 12, marginBottom: 6 }}>
                {opening.variation_name}
              </div>
            )}
            {opening.strategic_ideas && opening.strategic_ideas.length > 0 && (
              <ul style={{ margin: '6px 0 0', padding: '0 0 0 16px' }}>
                {opening.strategic_ideas.map((idea, i) => (
                  <li
                    key={i}
                    style={{
                      color: '#bbb',
                      fontSize: 13,
                      lineHeight: 1.5,
                      marginBottom: 3,
                    }}
                  >
                    {idea}
                  </li>
                ))}
              </ul>
            )}
          </>
        ) : (
          <div style={{ color: '#666', fontSize: 13 }}>
            {opening === null
              ? 'Loading opening...'
              : 'Position not in opening book — engine analysis below'}
          </div>
        )}
      </div>

      {/* Candidate moves with skeleton loader */}
      <CandidateMoves
        candidates={analysis?.candidates ?? []}
        loading={loadingAnalysis}
        onPlayMove={(uci) => {
          onPlayMove(uci.slice(0, 2), uci.slice(2, 4), uci.slice(4) || undefined)
        }}
      />

      {/* Opponent responses — hidden until at least one is ready */}
      {(loadingResponses ||
        (opponentResponses?.responses?.length ?? 0) > 0) && (
        <OpponentResponses
          responses={opponentResponses?.responses ?? []}
          loading={loadingResponses}
          onPlayResponse={onPlaySan}
        />
      )}
    </div>
  )
}
