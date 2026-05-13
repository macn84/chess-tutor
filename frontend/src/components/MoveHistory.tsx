/**
 * Navigable move-history table component.
 *
 * Renders the game's move list as a two-column table (White / Black) with
 * clickable cells.  The currently displayed move is highlighted in a darker
 * background.
 */

import type { GameMove } from '../types'

/** Props for {@link MoveHistory}. */
interface Props {
  /** Full ordered move history (index 0 = White's first move). */
  history: GameMove[]
  /** Index of the move currently shown on the board (-1 = start position). */
  currentIndex: number
  /**
   * Called when the user clicks a move cell.
   *
   * @param index - History index to navigate to.
   */
  onNavigate: (index: number) => void
}

/**
 * Scrollable move-history table with click-to-navigate support.
 *
 * @param props - {@link Props}
 */
export function MoveHistory({ history, currentIndex, onNavigate }: Props) {
  // Pair adjacent moves into (White, Black) rows
  const pairs: {
    white?: GameMove
    black?: GameMove
    moveNum: number
    whiteIdx: number
  }[] = []

  for (let i = 0; i < history.length; i += 2) {
    pairs.push({
      white: history[i],
      black: history[i + 1],
      moveNum: Math.floor(i / 2) + 1,
      whiteIdx: i,
    })
  }

  return (
    <div
      style={{
        background: '#1e1e1e',
        borderRadius: 6,
        padding: '8px 4px',
        maxHeight: 160,
        overflowY: 'auto',
        fontFamily: 'monospace',
        fontSize: 13,
      }}
    >
      {pairs.length === 0 ? (
        <div style={{ color: '#555', textAlign: 'center', padding: 8 }}>
          No moves yet
        </div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <tbody>
            {pairs.map(({ white, black, moveNum, whiteIdx }) => (
              <tr key={moveNum}>
                <td
                  style={{
                    color: '#555',
                    width: 28,
                    paddingLeft: 6,
                    userSelect: 'none',
                  }}
                >
                  {moveNum}.
                </td>
                <td
                  onClick={() => white && onNavigate(whiteIdx)}
                  style={{
                    cursor: 'pointer',
                    padding: '2px 6px',
                    borderRadius: 3,
                    background:
                      currentIndex === whiteIdx ? '#3a3a3a' : 'transparent',
                    color: currentIndex === whiteIdx ? '#fff' : '#ccc',
                    fontWeight: currentIndex === whiteIdx ? 700 : 400,
                  }}
                >
                  {white?.san ?? ''}
                </td>
                <td
                  onClick={() => black && onNavigate(whiteIdx + 1)}
                  style={{
                    cursor: black ? 'pointer' : 'default',
                    padding: '2px 6px',
                    borderRadius: 3,
                    background:
                      currentIndex === whiteIdx + 1 ? '#3a3a3a' : 'transparent',
                    color: currentIndex === whiteIdx + 1 ? '#fff' : '#ccc',
                    fontWeight: currentIndex === whiteIdx + 1 ? 700 : 400,
                  }}
                >
                  {black?.san ?? ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
