/**
 * Rendering tests for Chess Tutor UI components.
 *
 * Tests are focused on user-visible output (text, roles, classes) rather than
 * implementation details so they survive style refactors.
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { EvalBar } from '../components/EvalBar'
import { MoveHistory } from '../components/MoveHistory'
import { CandidateMoves } from '../components/CandidateMoves'
import { OpponentResponses } from '../components/OpponentResponses'
import type { CandidateMove, OpponentResponse, GameMove } from '../types'

// ---------------------------------------------------------------------------
// EvalBar
// ---------------------------------------------------------------------------

describe('EvalBar', () => {
  it('shows "..." when evalCp is null', () => {
    render(<EvalBar evalCp={null} />)
    expect(screen.getByText('...')).toBeInTheDocument()
  })

  it('shows positive score with + prefix', () => {
    render(<EvalBar evalCp={50} />)
    expect(screen.getByText('+0.5')).toBeInTheDocument()
  })

  it('shows negative score without + prefix', () => {
    render(<EvalBar evalCp={-100} />)
    expect(screen.getByText('-1.0')).toBeInTheDocument()
  })

  it('shows +M for large positive score (mate)', () => {
    render(<EvalBar evalCp={9500} />)
    expect(screen.getByText('+M')).toBeInTheDocument()
  })

  it('shows -M for large negative score (mate)', () => {
    render(<EvalBar evalCp={-9500} />)
    expect(screen.getByText('-M')).toBeInTheDocument()
  })

  it('shows 0.0 for equal position', () => {
    render(<EvalBar evalCp={0} />)
    expect(screen.getByText('0.0')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// MoveHistory
// ---------------------------------------------------------------------------

const sampleHistory: GameMove[] = [
  { san: 'e4', uci: 'e2e4', fen_after: 'fen1' },
  { san: 'e5', uci: 'e7e5', fen_after: 'fen2' },
  { san: 'Nf3', uci: 'g1f3', fen_after: 'fen3' },
]

describe('MoveHistory', () => {
  it('shows placeholder when history is empty', () => {
    render(<MoveHistory history={[]} currentIndex={-1} onNavigate={() => {}} />)
    expect(screen.getByText(/no moves yet/i)).toBeInTheDocument()
  })

  it('renders all move SANs', () => {
    render(
      <MoveHistory history={sampleHistory} currentIndex={2} onNavigate={() => {}} />,
    )
    expect(screen.getByText('e4')).toBeInTheDocument()
    expect(screen.getByText('e5')).toBeInTheDocument()
    expect(screen.getByText('Nf3')).toBeInTheDocument()
  })

  it('calls onNavigate with the correct index when a move is clicked', () => {
    const onNavigate = vi.fn()
    render(
      <MoveHistory history={sampleHistory} currentIndex={-1} onNavigate={onNavigate} />,
    )
    fireEvent.click(screen.getByText('e4'))
    expect(onNavigate).toHaveBeenCalledWith(0)
  })

  it('renders move numbers', () => {
    render(
      <MoveHistory history={sampleHistory} currentIndex={0} onNavigate={() => {}} />,
    )
    expect(screen.getByText('1.')).toBeInTheDocument()
    expect(screen.getByText('2.')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// CandidateMoves
// ---------------------------------------------------------------------------

const sampleCandidates: CandidateMove[] = [
  {
    san: 'Nf3',
    uci: 'g1f3',
    score_cp: 30,
    score_label: '+0.3',
    pv_san: ['Nf3', 'Nc6'],
    explanation: 'Develops to a natural square.',
    label: 'Development',
  },
  {
    san: 'e4',
    uci: 'e2e4',
    score_cp: 20,
    score_label: '+0.2',
    pv_san: ['e4', 'e5'],
    explanation: 'Stakes the center.',
    label: '',
  },
]

describe('CandidateMoves', () => {
  it('renders nothing when candidates is empty and not loading', () => {
    const { container } = render(
      <CandidateMoves candidates={[]} loading={false} />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders skeleton rows while loading', () => {
    render(<CandidateMoves candidates={[]} loading={true} />)
    expect(screen.getByText(/candidate moves/i)).toBeInTheDocument()
  })

  it('renders all candidate SANs', () => {
    render(<CandidateMoves candidates={sampleCandidates} loading={false} />)
    expect(screen.getByText('Nf3')).toBeInTheDocument()
    expect(screen.getByText('e4')).toBeInTheDocument()
  })

  it('renders score labels', () => {
    render(<CandidateMoves candidates={sampleCandidates} loading={false} />)
    expect(screen.getByText('+0.3')).toBeInTheDocument()
  })

  it('expands explanation on click', () => {
    render(<CandidateMoves candidates={sampleCandidates} loading={false} />)
    fireEvent.click(screen.getByText('Nf3'))
    expect(screen.getByText('Develops to a natural square.')).toBeInTheDocument()
  })

  it('shows the PV line when expanded', () => {
    render(<CandidateMoves candidates={sampleCandidates} loading={false} />)
    fireEvent.click(screen.getByText('Nf3'))
    expect(screen.getByText(/Nf3 Nc6/)).toBeInTheDocument()
  })

  it('calls onPlayMove with the UCI when Play button is clicked', () => {
    const onPlayMove = vi.fn()
    render(
      <CandidateMoves
        candidates={sampleCandidates}
        loading={false}
        onPlayMove={onPlayMove}
      />,
    )
    fireEvent.click(screen.getByText('Nf3')) // expand
    fireEvent.click(screen.getByText(/play nf3/i))
    expect(onPlayMove).toHaveBeenCalledWith('g1f3')
  })

  it('shows the first-place star badge for the top candidate', () => {
    render(<CandidateMoves candidates={sampleCandidates} loading={false} />)
    expect(screen.getByText('★')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// OpponentResponses
// ---------------------------------------------------------------------------

const sampleResponses: OpponentResponse[] = [
  {
    san: 'Nc6',
    score_cp: -30,
    explanation: 'Develops the knight.',
    label: 'Classical',
    follow_up_idea: 'White plays Nf3 next.',
    resulting_opening: 'Ruy Lopez',
    in_book: true,
  },
]

describe('OpponentResponses', () => {
  it('renders nothing when responses is empty and not loading', () => {
    const { container } = render(
      <OpponentResponses responses={[]} loading={false} />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('shows skeleton while loading with no responses', () => {
    render(<OpponentResponses responses={[]} loading={true} />)
    expect(screen.getByText(/if opponent plays/i)).toBeInTheDocument()
  })

  it('renders the response SAN', () => {
    render(<OpponentResponses responses={sampleResponses} loading={false} />)
    expect(screen.getByText('Nc6')).toBeInTheDocument()
  })

  it('expands explanation on click', () => {
    render(<OpponentResponses responses={sampleResponses} loading={false} />)
    fireEvent.click(screen.getByText('Nc6'))
    expect(screen.getByText('Develops the knight.')).toBeInTheDocument()
  })

  it('shows follow-up idea when expanded', () => {
    render(<OpponentResponses responses={sampleResponses} loading={false} />)
    fireEvent.click(screen.getByText('Nc6'))
    expect(screen.getByText('White plays Nf3 next.')).toBeInTheDocument()
  })

  it('shows resulting opening name when expanded', () => {
    render(<OpponentResponses responses={sampleResponses} loading={false} />)
    fireEvent.click(screen.getByText('Nc6'))
    expect(screen.getByText(/Ruy Lopez/)).toBeInTheDocument()
  })

  it('shows book indicator emoji for in-book responses', () => {
    render(<OpponentResponses responses={sampleResponses} loading={false} />)
    expect(screen.getByText('📖')).toBeInTheDocument()
  })

  it('calls onPlayResponse with the SAN when "Play this line" is clicked', () => {
    const onPlayResponse = vi.fn()
    render(
      <OpponentResponses
        responses={sampleResponses}
        loading={false}
        onPlayResponse={onPlayResponse}
      />,
    )
    fireEvent.click(screen.getByText('Nc6')) // expand
    fireEvent.click(screen.getByText(/play this line/i))
    expect(onPlayResponse).toHaveBeenCalledWith('Nc6')
  })
})
