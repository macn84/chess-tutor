import { useState } from 'react'
import type { GameFilter } from '../../types'

interface Props {
  onSubmit: (filter: GameFilter) => void;
  disabled: boolean;
}

function defaultEndDate(): string {
  return new Date().toISOString().slice(0, 10)
}

function defaultStartDate(): string {
  const d = new Date()
  d.setMonth(d.getMonth() - 3)
  return d.toISOString().slice(0, 10)
}

export function GameFilters({ onSubmit, disabled }: Props) {
  const [startDate, setStartDate] = useState(defaultStartDate)
  const [endDate, setEndDate] = useState(defaultEndDate)
  const [timeClass, setTimeClass] = useState<GameFilter['time_class']>('all')
  const [color, setColor] = useState<GameFilter['color']>('both')
  const [result, setResult] = useState<GameFilter['result']>('all')
  const [termination, setTermination] = useState<GameFilter['termination']>('all')
  const [rated, setRated] = useState<GameFilter['rated']>('all')
  const [minOppRating, setMinOppRating] = useState('')
  const [maxOppRating, setMaxOppRating] = useState('')
  const [maxGames, setMaxGames] = useState<GameFilter['max_games']>(100)
  const [error, setError] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (startDate > endDate) {
      setError('Start date must be before end date.')
      return
    }
    const minOpp = minOppRating ? parseInt(minOppRating, 10) : null
    const maxOpp = maxOppRating ? parseInt(maxOppRating, 10) : null
    if (minOpp !== null && maxOpp !== null && minOpp > maxOpp) {
      setError('Min opponent rating must be ≤ max.')
      return
    }
    setError('')
    onSubmit({
      start_date: startDate,
      end_date: endDate,
      time_class: timeClass,
      color,
      result,
      termination,
      rated,
      min_opponent_rating: minOpp,
      max_opponent_rating: maxOpp,
      max_games: maxGames,
    })
  }

  return (
    <form className="game-filters" onSubmit={handleSubmit}>
      <h2 className="ga-section-title">Analyze My Games</h2>
      <p className="ga-description">
        Fetch your Chess.com games, run Stockfish blunder detection across the set,
        and get personalized coaching insights.
      </p>

      {error && <div className="ga-error">{error}</div>}

      <div className="ga-fields">
        <div className="ga-row">
          <label className="ga-label">
            From
            <input
              className="ga-input"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              disabled={disabled}
            />
          </label>
          <label className="ga-label">
            To
            <input
              className="ga-input"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              disabled={disabled}
            />
          </label>
        </div>

        <div className="ga-row">
          <label className="ga-label">
            Game Type
            <select
              className="ga-select"
              value={timeClass}
              onChange={(e) => setTimeClass(e.target.value as GameFilter['time_class'])}
              disabled={disabled}
            >
              <option value="all">All types</option>
              <option value="rapid">Rapid</option>
              <option value="blitz">Blitz</option>
              <option value="bullet">Bullet</option>
              <option value="daily">Daily</option>
            </select>
          </label>

          <label className="ga-label">
            Color
            <select
              className="ga-select"
              value={color}
              onChange={(e) => setColor(e.target.value as GameFilter['color'])}
              disabled={disabled}
            >
              <option value="both">Both colors</option>
              <option value="white">White only</option>
              <option value="black">Black only</option>
            </select>
          </label>

          <label className="ga-label">
            Result
            <select
              className="ga-select"
              value={result}
              onChange={(e) => setResult(e.target.value as GameFilter['result'])}
              disabled={disabled}
            >
              <option value="all">All results</option>
              <option value="win">Wins</option>
              <option value="loss">Losses</option>
              <option value="draw">Draws</option>
            </select>
          </label>
        </div>

        <div className="ga-row">
          <label className="ga-label">
            Termination
            <select
              className="ga-select"
              value={termination}
              onChange={(e) => setTermination(e.target.value as GameFilter['termination'])}
              disabled={disabled}
            >
              <option value="all">Any termination</option>
              <option value="checkmate">Checkmate</option>
              <option value="resignation">Resignation</option>
              <option value="timeout">Timeout</option>
              <option value="abandonment">Abandonment</option>
              <option value="draw_agreement">Draw — agreement</option>
              <option value="draw_repetition">Draw — repetition</option>
              <option value="draw_stalemate">Draw — stalemate</option>
              <option value="draw_50move">Draw — 50-move rule</option>
              <option value="draw_insufficient">Draw — insufficient material</option>
            </select>
          </label>

          <label className="ga-label">
            Rated
            <select
              className="ga-select"
              value={rated}
              onChange={(e) => setRated(e.target.value as GameFilter['rated'])}
              disabled={disabled}
            >
              <option value="all">Rated &amp; unrated</option>
              <option value="rated">Rated only</option>
              <option value="unrated">Unrated only</option>
            </select>
          </label>

          <label className="ga-label">
            Max games
            <select
              className="ga-select"
              value={maxGames}
              onChange={(e) => setMaxGames(parseInt(e.target.value, 10) as GameFilter['max_games'])}
              disabled={disabled}
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
            </select>
          </label>
        </div>

        <div className="ga-row">
          <label className="ga-label">
            Min opp. rating
            <input
              className="ga-input"
              type="number"
              placeholder="e.g. 1000"
              value={minOppRating}
              onChange={(e) => setMinOppRating(e.target.value)}
              disabled={disabled}
              min={0}
              max={3500}
            />
          </label>
          <label className="ga-label">
            Max opp. rating
            <input
              className="ga-input"
              type="number"
              placeholder="e.g. 1500"
              value={maxOppRating}
              onChange={(e) => setMaxOppRating(e.target.value)}
              disabled={disabled}
              min={0}
              max={3500}
            />
          </label>
        </div>
      </div>

      <p className="ga-note">Up to {maxGames} games analyzed. Analysis takes 3–5 minutes.</p>

      <button className="ga-submit" type="submit" disabled={disabled}>
        Fetch &amp; Analyze
      </button>
    </form>
  )
}
