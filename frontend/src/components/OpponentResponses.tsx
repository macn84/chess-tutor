/**
 * Opponent-responses panel component.
 *
 * Shows the engine's top replies from the opponent's perspective after the
 * user plays a move.  Each response is an expandable card with prose,
 * follow-up idea, resulting opening name, and a "Play this line" button.
 */

import { useState } from 'react'
import type { OpponentResponse } from '../types'

/** Props for {@link OpponentResponses}. */
interface Props {
  /** Engine-ranked opponent replies to display. */
  responses: OpponentResponse[]
  /** When true and ``responses`` is empty, renders a skeleton placeholder. */
  loading: boolean
  /**
   * Called when the user clicks "Play this line".
   *
   * @param san - The opponent move in SAN notation to play onto the board.
   */
  onPlayResponse?: (san: string) => void
}

/**
 * Expandable list of opponent responses with teaching annotations.
 *
 * @param props - {@link Props}
 */
export function OpponentResponses({ responses, loading, onPlayResponse }: Props) {
  const [expanded, setExpanded] = useState<number | null>(null)

  if (loading && !responses.length) {
    return (
      <div>
        <div style={{ color: '#777', fontSize: 12, marginBottom: 6 }}>
          If opponent plays...
        </div>
        <div
          style={{
            height: 36,
            borderRadius: 4,
            background: '#2a2a2a',
            animation: 'pulse 1.4s ease-in-out infinite',
          }}
        />
      </div>
    )
  }

  if (!responses.length) return null

  return (
    <div>
      <div style={{ color: '#777', fontSize: 12, marginBottom: 6 }}>
        If opponent plays...
      </div>
      {responses.map((r, i) => (
        <div
          key={r.san + i}
          style={{
            borderRadius: 4,
            background: '#1a2030',
            marginBottom: 4,
            overflow: 'hidden',
            border: '1px solid #2a3040',
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
            <span
              style={{
                fontFamily: 'monospace',
                fontWeight: 700,
                fontSize: 14,
                color: '#a0b8d8',
                minWidth: 52,
              }}
            >
              {r.san}
            </span>
            {r.label && (
              <span style={{ fontSize: 12, color: '#7a9ab8', flex: 1 }}>
                {r.label}
              </span>
            )}
            {/* Book indicator */}
            {r.in_book && (
              <span style={{ fontSize: 10, color: '#4a7aaa', marginLeft: 'auto' }}>
                📖
              </span>
            )}
            <span style={{ color: '#445', fontSize: 10, marginLeft: 4 }}>
              {expanded === i ? '▲' : '▼'}
            </span>
          </div>

          {/* Expanded detail panel */}
          {expanded === i && (
            <div style={{ padding: '0 8px 8px 12px', borderTop: '1px solid #2a3040' }}>
              {r.explanation && (
                <p
                  style={{
                    margin: '8px 0 6px',
                    color: '#9ab8d8',
                    fontSize: 13,
                    lineHeight: 1.5,
                  }}
                >
                  {r.explanation}
                </p>
              )}
              {r.follow_up_idea && (
                <p
                  style={{
                    margin: '0 0 6px',
                    color: '#7a9ab0',
                    fontSize: 12,
                    lineHeight: 1.5,
                    fontStyle: 'italic',
                  }}
                >
                  {r.follow_up_idea}
                </p>
              )}
              {r.resulting_opening && (
                <div
                  style={{ fontSize: 11, color: '#4a6a88', marginBottom: 6 }}
                >
                  → {r.resulting_opening}
                </div>
              )}
              {onPlayResponse && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onPlayResponse(r.san)
                    setExpanded(null)
                  }}
                  style={{
                    fontSize: 11,
                    padding: '3px 10px',
                    borderRadius: 3,
                    border: '1px solid #2a3a50',
                    background: '#1a2a40',
                    color: '#7a9ab8',
                    cursor: 'pointer',
                  }}
                >
                  Play this line
                </button>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
