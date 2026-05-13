import type { AnalysisProgress as Progress } from '../../hooks/useGameAnalysis'

interface Props {
  stage: 'fetching' | 'analyzing';
  gameCount: number;
  progress: Progress | null;
}

export function AnalysisProgress({ stage, gameCount, progress }: Props) {
  if (stage === 'fetching') {
    return (
      <div className="ga-progress">
        <div className="ga-spinner" />
        <p className="ga-progress-label">Fetching games from Chess.com…</p>
      </div>
    )
  }

  const pct = progress ? Math.round(progress.progress * 100) : 0
  const analyzed = progress?.analyzedCount ?? 0
  const total = progress?.total ?? gameCount

  // Rough ETA: 0.15s/position × 30 moves/game, but simplified to ~4s/game for display
  const remaining = total - analyzed
  const etaSec = remaining * 4
  const etaLabel =
    etaSec < 60
      ? `~${etaSec}s remaining`
      : `~${Math.ceil(etaSec / 60)}min remaining`

  return (
    <div className="ga-progress">
      <p className="ga-progress-label">
        Analyzing game {analyzed} of {total}…
      </p>
      <div className="ga-progress-bar-track">
        <div className="ga-progress-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <p className="ga-progress-sub">{pct}% complete — {etaLabel}</p>
      <p className="ga-progress-note">
        Stockfish is reviewing each position for blunders. This runs in the background.
      </p>
    </div>
  )
}
