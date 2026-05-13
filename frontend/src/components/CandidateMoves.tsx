/**
 * Candidate-moves panel component.
 *
 * Renders a ranked list of Stockfish candidate moves with expandable cards
 * showing the prose explanation, principal variation, and a "Play" button.
 * Shows a skeleton loader while analysis is in-flight.
 */

import { useState } from 'react'
import type { CandidateMove } from '../types'

/** Props for {@link CandidateMoves}. */
interface Props {
  /** Ranked candidate moves to display, best first. */
  candidates: CandidateMove[]
  /** When true, renders skeleton placeholder rows instead of real data. */
  loading: boolean
  /**
   * Called when the user clicks the "Play" button on a candidate.
   *
   * @param uci - The candidate's UCI string (e.g. "g1f3").
   */
  onPlayMove?: (uci: string) => void
}

/**
 * Map a centipawn score to a colour on a red-to-green scale.
 *
 * @param cp - Score in centipawns from the moving side's perspective.
 * @returns CSS colour string.
 */
function scoreColor(cp: number): string {
  if (cp >= 100) return '#7fc97f'
  if (cp >= 30) return '#b8d8a8'
  if (cp >= -30) return '#e8d88a'
  if (cp >= -100) return '#e8aa6a'
  return '#e87a6a'
}

/**
 * Expandable list of engine candidate moves with teaching prose.
 *
 * @param props - {@link Props}
 */
export function CandidateMoves({ candidates, loading, onPlayMove }: Props) {
  const [expanded, setExpanded] = useState<number | null>(null)

  if (loading) {
    return (
      <div>
        <div style={{ color: '#777', fontSize: 12, marginBottom: 6 }}>
          Candidate Moves
        </div>
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            style={{
              height: 48,
              borderRadius: 4,
              background: '#2a2a2a',
              marginBottom: 4,
              animation: 'pulse 1.4s ease-in-out infinite',
              animationDelay: `${i * 0.1}s`,
            }}
          />
        ))}
      </div>
    )
  }

  if (!candidates.length) return null

  return (
    <div>
      <div style={{ color: '#777', fontSize: 12, marginBottom: 6 }}>
        Candidate Moves
      </div>
      {candidates.map((c, i) => (
        <div
          key={c.san + i}
          style={{
            borderRadius: 4,
            background: '#222',
            marginBottom: 4,
            overflow: 'hidden',
            border: '1px solid #333',
          }}
        >
          {/* Collapsed header row */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '6px 8px',
              cursor: 'pointer',
              gap: 8,
            }}
            onClick={() => setExpanded(expanded === i ? null : i)}
          >
            {/* Rank badge: star for best move, number for the rest */}
            {i === 0 ? (
              <span style={{ fontSize: 10, color: '#888', minWidth: 16 }}>
                ★
              </span>
            ) : (
              <span style={{ fontSize: 10, color: '#555', minWidth: 16 }}>
                {i + 1}.
              </span>
            )}

            <span
              style={{
                fontFamily: 'monospace',
                fontWeight: 700,
                fontSize: 15,
                color: '#fff',
                minWidth: 52,
              }}
            >
              {c.san}
            </span>

            {c.label && (
              <span style={{ fontSize: 12, color: '#aaa', flex: 1 }}>
                {c.label}
              </span>
            )}

            <span
              style={{
                fontSize: 11,
                fontFamily: 'monospace',
                color: scoreColor(c.score_cp),
                marginLeft: 'auto',
                minWidth: 40,
                textAlign: 'right',
              }}
            >
              {c.score_label}
            </span>

            <span style={{ color: '#555', fontSize: 10, marginLeft: 4 }}>
              {expanded === i ? '▲' : '▼'}
            </span>
          </div>

          {/* Expanded detail panel */}
          {expanded === i && (
            <div
              style={{ padding: '0 8px 8px 32px', borderTop: '1px solid #2a2a2a' }}
            >
              <p
                style={{
                  margin: '8px 0 6px',
                  color: '#ccc',
                  fontSize: 13,
                  lineHeight: 1.5,
                }}
              >
                {c.explanation}
              </p>

              {c.pv_san.length > 0 && (
                <div style={{ marginBottom: 6 }}>
                  <span style={{ color: '#666', fontSize: 11 }}>Line: </span>
                  <span
                    style={{
                      fontFamily: 'monospace',
                      fontSize: 12,
                      color: '#888',
                    }}
                  >
                    {c.pv_san.join(' ')}
                  </span>
                </div>
              )}

              {onPlayMove && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onPlayMove(c.uci)
                    setExpanded(null)
                  }}
                  style={{
                    fontSize: 11,
                    padding: '3px 10px',
                    borderRadius: 3,
                    border: '1px solid #444',
                    background: '#2a2a2a',
                    color: '#aaa',
                    cursor: 'pointer',
                  }}
                >
                  Play {c.san}
                </button>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
