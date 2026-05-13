/**
 * Vertical evaluation bar component.
 *
 * Displays a white-fills-from-bottom bar clamped to ±600 cp, with a numeric
 * label underneath.  Animates height transitions so the bar moves smoothly
 * as analysis updates.
 */

/** Props for {@link EvalBar}. */
interface Props {
  /** Centipawn score from White's perspective.  Null renders a neutral bar. */
  evalCp: number | null
}

/**
 * Narrow vertical bar showing the engine evaluation of the current position.
 *
 * @param props - {@link Props}
 */
export function EvalBar({ evalCp }: Props) {
  const MAX_CP = 600
  const clampedCp = evalCp === null
    ? 0
    : Math.max(-MAX_CP, Math.min(MAX_CP, evalCp))
  const whitePercent = 50 + (clampedCp / MAX_CP) * 50

  const label =
    evalCp === null
      ? '...'
      : Math.abs(evalCp) > 900
      ? evalCp > 0
        ? '+M'
        : '-M'
      : evalCp > 0
      ? `+${(evalCp / 100).toFixed(1)}`
      : (evalCp / 100).toFixed(1)

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        width: 32,
      }}
    >
      <div
        style={{
          width: 20,
          height: 480,
          borderRadius: 4,
          overflow: 'hidden',
          background: '#333',
          position: 'relative',
          flexShrink: 0,
        }}
      >
        <div
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            height: `${whitePercent}%`,
            background: '#f0f0f0',
            transition: 'height 0.4s ease',
          }}
        />
      </div>
      <div
        style={{
          fontSize: 11,
          color: '#aaa',
          marginTop: 4,
          fontFamily: 'monospace',
        }}
      >
        {label}
      </div>
    </div>
  )
}
