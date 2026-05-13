/**
 * Root application component for Chess Tutor.
 *
 * Layout: a fixed header, then a two-column main area:
 * - Left  (55 %): evaluation bar + interactive chess board.
 * - Right (45 %): move history table + teaching panel.
 *
 * State is split across two hooks:
 * - {@link useGameState} — board position, history, orientation.
 * - {@link useAnalysis}  — opening book, Stockfish candidates, opponent replies.
 */

import { useCallback, useState } from 'react'
import { Chess } from 'chess.js'
import { ChessBoardPanel } from './components/ChessBoard'
import { TeachingPanel } from './components/TeachingPanel'
import { MoveHistory } from './components/MoveHistory'
import { EvalBar } from './components/EvalBar'
import { GameAnalysisTab } from './components/GameAnalysis/GameAnalysisTab'
import { useGameState } from './hooks/useGameState'
import { useAnalysis } from './hooks/useAnalysis'
import './App.css'

type AppTab = 'tutor' | 'my-games'

/** Root application component. */
export default function App() {
  const [activeTab, setActiveTab] = useState<AppTab>('tutor')

  const {
    state,
    makeMove,
    navigate,
    flipBoard,
    reset,
    lastMoveSquares,
  } = useGameState()

  const {
    opening,
    analysis,
    opponentResponses,
    loadingAnalysis,
    loadingResponses,
  } = useAnalysis(state.fen, state.lastMoveUci)

  const playFromSan = useCallback(
    (san: string) => {
      const chess = new Chess(state.fen)
      try {
        const move = chess.move(san)
        if (move) makeMove(move.from, move.to, move.promotion)
      } catch {}
    },
    [state.fen, makeMove],
  )

  return (
    <div className="app-root">
      <header className="app-header">
        <span className="app-title">♟ Chess Tutor</span>
        <nav className="app-tabs">
          <button
            className={`app-tab ${activeTab === 'tutor' ? 'app-tab--active' : ''}`}
            onClick={() => setActiveTab('tutor')}
          >
            Tutor
          </button>
          <button
            className={`app-tab ${activeTab === 'my-games' ? 'app-tab--active' : ''}`}
            onClick={() => setActiveTab('my-games')}
          >
            My Games
          </button>
        </nav>
        {activeTab === 'tutor' && (
          <div className="header-actions">
            <button onClick={flipBoard}>Flip Board</button>
            <button onClick={reset}>New Game</button>
          </div>
        )}
      </header>

      {activeTab === 'tutor' && (
        <main className="app-main">
          <div className="board-area">
            <EvalBar evalCp={analysis?.eval_cp ?? null} />
            <ChessBoardPanel
              fen={state.fen}
              orientation={state.orientation}
              onMove={makeMove}
              customSquareStyles={lastMoveSquares}
            />
          </div>

          <div className="panel-area">
            <MoveHistory
              history={state.history}
              currentIndex={state.currentIndex}
              onNavigate={navigate}
            />
            <TeachingPanel
              opening={opening}
              analysis={analysis}
              opponentResponses={opponentResponses}
              loadingAnalysis={loadingAnalysis}
              loadingResponses={loadingResponses}
              onPlayMove={makeMove}
              onPlaySan={playFromSan}
            />
          </div>
        </main>
      )}

      {activeTab === 'my-games' && (
        <main className="app-main app-main--full">
          <GameAnalysisTab />
        </main>
      )}
    </div>
  )
}
