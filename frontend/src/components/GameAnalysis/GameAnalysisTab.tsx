import { useGameAnalysis } from '../../hooks/useGameAnalysis'
import { GameFilters } from './GameFilters'
import { AnalysisProgress } from './AnalysisProgress'
import { PatternSummary } from './PatternSummary'
import { CoachingInsights } from './CoachingInsights'

export function GameAnalysisTab() {
  const [state, actions] = useGameAnalysis()
  const { stage, error, gameCount, progress, patterns, insights } = state

  const isWorking = stage === 'fetching' || stage === 'analyzing'

  return (
    <div className="ga-root">
      {/* Always show the filters form so users can re-run without resetting */}
      <div className="ga-sidebar">
        <GameFilters onSubmit={actions.run} disabled={isWorking} />
        {(stage === 'done' || stage === 'error') && (
          <button className="ga-reset" onClick={actions.reset}>
            ← New Analysis
          </button>
        )}
      </div>

      <div className="ga-main">
        {stage === 'idle' && (
          <div className="ga-empty">
            <p>Configure your filters and click <strong>Fetch &amp; Analyze</strong> to begin.</p>
          </div>
        )}

        {stage === 'error' && (
          <div className="ga-error ga-error--block">
            <strong>Error:</strong> {error}
          </div>
        )}

        {(stage === 'fetching' || stage === 'analyzing') && (
          <AnalysisProgress
            stage={stage}
            gameCount={gameCount}
            progress={progress}
          />
        )}

        {stage === 'done' && patterns && insights && (
          <>
            <CoachingInsights insights={insights} />
            <PatternSummary patterns={patterns} />
          </>
        )}
      </div>
    </div>
  )
}
