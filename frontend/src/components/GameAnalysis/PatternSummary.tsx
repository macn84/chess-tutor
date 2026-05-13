import type { AnalysisPatterns } from '../../types'

interface Props {
  patterns: AnalysisPatterns;
}

export function PatternSummary({ patterns }: Props) {
  const { total_games, wins, losses, draws, blunders_per_game, mistakes_per_game,
    avg_cp_loss, phase_distribution, opening_stats, top_blunders, mistake_move_numbers,
    severity_totals } = patterns

  const winRate = total_games > 0 ? ((wins / total_games) * 100).toFixed(1) : '0'
  const phases = ['opening', 'middlegame', 'endgame'] as const

  return (
    <div className="ga-patterns">
      {/* Summary stats */}
      <section className="ga-card">
        <h3 className="ga-card-title">Overall Summary</h3>
        <div className="ga-stats-grid">
          <div className="ga-stat"><span className="ga-stat-val">{total_games}</span><span className="ga-stat-lbl">Games</span></div>
          <div className="ga-stat"><span className="ga-stat-val">{wins}W/{draws}D/{losses}L</span><span className="ga-stat-lbl">Record ({winRate}% wins)</span></div>
          <div className="ga-stat"><span className="ga-stat-val">{avg_cp_loss}</span><span className="ga-stat-lbl">Avg CP Loss</span></div>
          <div className="ga-stat"><span className="ga-stat-val">{blunders_per_game.toFixed(1)}</span><span className="ga-stat-lbl">Blunders/game</span></div>
          <div className="ga-stat"><span className="ga-stat-val">{mistakes_per_game.toFixed(1)}</span><span className="ga-stat-lbl">Mistakes/game</span></div>
          <div className="ga-stat">
            <span className="ga-stat-val">
              {severity_totals.blunder + severity_totals.mistake + severity_totals.inaccuracy}
            </span>
            <span className="ga-stat-lbl">Total errors</span>
          </div>
        </div>
      </section>

      {/* Phase distribution */}
      <section className="ga-card">
        <h3 className="ga-card-title">Where Mistakes Happen</h3>
        <div className="ga-phase-bars">
          {phases.map((p) => (
            <div key={p} className="ga-phase-row">
              <span className="ga-phase-label">{p.charAt(0).toUpperCase() + p.slice(1)}</span>
              <div className="ga-phase-track">
                <div
                  className={`ga-phase-fill ga-phase-fill--${p}`}
                  style={{ width: `${phase_distribution[p]}%` }}
                />
              </div>
              <span className="ga-phase-pct">{phase_distribution[p]}%</span>
            </div>
          ))}
        </div>
      </section>

      {/* Error-prone move numbers */}
      {mistake_move_numbers.length > 0 && (
        <section className="ga-card">
          <h3 className="ga-card-title">Most Error-Prone Move Numbers</h3>
          <div className="ga-move-hist">
            {mistake_move_numbers.slice(0, 8).map(({ move_number, count }) => (
              <div key={move_number} className="ga-move-hist-row">
                <span className="ga-move-num">Move {move_number}</span>
                <div className="ga-move-track">
                  <div
                    className="ga-move-fill"
                    style={{
                      width: `${Math.round((count / mistake_move_numbers[0].count) * 100)}%`,
                    }}
                  />
                </div>
                <span className="ga-move-count">{count}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Opening performance */}
      {opening_stats.length > 0 && (
        <section className="ga-card">
          <h3 className="ga-card-title">Opening Performance</h3>
          <div className="ga-table-wrap">
            <table className="ga-table">
              <thead>
                <tr>
                  <th>Opening</th>
                  <th>Games</th>
                  <th>Wins</th>
                  <th>Win%</th>
                  <th>Avg CP Loss</th>
                </tr>
              </thead>
              <tbody>
                {opening_stats.slice(0, 10).map((o, i) => (
                  <tr key={i}>
                    <td>
                      {o.eco && <span className="ga-td-eco">{o.eco} · </span>}
                      {o.opening_name || 'Unknown'}
                    </td>
                    <td>{o.games}</td>
                    <td>{o.wins}</td>
                    <td>{o.win_rate}%</td>
                    <td className={o.avg_cp_loss > 60 ? 'ga-td-warn' : ''}>{o.avg_cp_loss}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Top blunders */}
      {top_blunders.length > 0 && (
        <section className="ga-card">
          <h3 className="ga-card-title">Worst Blunders</h3>
          <div className="ga-blunders">
            {top_blunders.map((b, i) => (
              <div key={i} className="ga-blunder-row">
                <div className="ga-blunder-meta">
                  <span className="ga-blunder-num">#{i + 1}</span>
                  <span className="ga-blunder-phase">{b.phase} · move {b.move_number}</span>
                  <span className="ga-blunder-loss">−{b.cp_loss} cp</span>
                </div>
                <div className="ga-blunder-moves">
                  <span className="ga-blunder-played">Played: <strong>{b.move_played_san}</strong></span>
                  <span className="ga-blunder-best">Best: <strong>{b.best_move_san}</strong></span>
                </div>
                {b.game_url && (
                  <a className="ga-blunder-link" href={b.game_url} target="_blank" rel="noreferrer">
                    View on Chess.com →
                  </a>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
