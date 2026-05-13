import type { CoachingInsightsResult } from '../../types'

interface Props {
  insights?: CoachingInsightsResult;
}

function renderInsights(text: string): React.ReactNode {
  // Render **bold** and newlines as simple HTML
  if (!text) return <p className="ga-insight-line">No insights available.</p>
  const lines = text.split('\n')
  return lines.map((line, i) => {
    if (!line.trim()) return <br key={i} />
    // Bold: **text**
    const parts = line.split(/(\*\*[^*]+\*\*)/)
    const rendered = parts.map((p, j) =>
      p.startsWith('**') ? <strong key={j}>{p.slice(2, -2)}</strong> : p,
    )
    return <p key={i} className="ga-insight-line">{rendered}</p>
  })
}

export function CoachingInsights({ insights }: Props) {
  if (!insights || !insights.insights) {
    return <section className="ga-card ga-card--insights">
      <div className="ga-insights-header">
        <h3 className="ga-card-title">Coaching Insights</h3>
      </div>
      <div className="ga-insights-body">
        <p className="ga-insight-line">No insights available.</p>
      </div>
    </section>
  }

  return (
    <section className="ga-card ga-card--insights">
      <div className="ga-insights-header">
        <h3 className="ga-card-title">Coaching Insights</h3>
        <span className={`ga-badge ${insights.llm_used ? 'ga-badge--claude' : 'ga-badge--engine'}`}>
          {insights.llm_used ? 'Powered by Claude' : 'Engine Analysis'}
        </span>
      </div>
      <div className="ga-insights-body">
        {renderInsights(insights.insights)}
      </div>
    </section>
  )
}
