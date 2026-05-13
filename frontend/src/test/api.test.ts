/**
 * Unit tests for the API client module (src/api.ts).
 *
 * All network calls are intercepted by vitest's global fetch mock so no real
 * server is needed.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchOpening, fetchAnalysis, fetchOpponentResponses } from '../api'

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

/** Build a minimal Response-like mock that resolves to the given data. */
function mockFetch(data: unknown, ok = true) {
  return vi.fn().mockResolvedValue({
    ok,
    json: () => Promise.resolve(data),
  } as unknown as Response)
}

beforeEach(() => {
  vi.restoreAllMocks()
})

// ---------------------------------------------------------------------------
// fetchOpening
// ---------------------------------------------------------------------------

describe('fetchOpening', () => {
  it('returns the parsed JSON on success', async () => {
    const payload = { found: true, eco: 'A00', opening_name: 'Start' }
    global.fetch = mockFetch(payload)

    const result = await fetchOpening(START_FEN)
    expect(result).toEqual(payload)
  })

  it('encodes the FEN in the query string', async () => {
    global.fetch = mockFetch({ found: false })
    await fetchOpening(START_FEN)

    const calledUrl = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0]
    expect(calledUrl).toContain(encodeURIComponent(START_FEN))
  })

  it('throws when the response is not ok', async () => {
    global.fetch = mockFetch(null, false)
    await expect(fetchOpening(START_FEN)).rejects.toThrow('opening fetch failed')
  })

  it('passes the abort signal to fetch', async () => {
    global.fetch = mockFetch({ found: false })
    const ac = new AbortController()
    await fetchOpening(START_FEN, ac.signal)

    const options = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1]
    expect(options.signal).toBe(ac.signal)
  })
})

// ---------------------------------------------------------------------------
// fetchAnalysis
// ---------------------------------------------------------------------------

describe('fetchAnalysis', () => {
  it('POSTs to /api/analyze with the FEN', async () => {
    const payload = { candidates: [], best_move_san: '', eval_cp: 0 }
    global.fetch = mockFetch(payload)

    await fetchAnalysis(START_FEN)
    const [url, options] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(url).toBe('/api/analyze')
    expect(options.method).toBe('POST')
    expect(JSON.parse(options.body).fen).toBe(START_FEN)
  })

  it('returns parsed analysis result', async () => {
    const payload = {
      candidates: [{ san: 'e4', uci: 'e2e4', score_cp: 30, score_label: '+0.3', pv_san: [], explanation: '', label: '' }],
      best_move_san: 'e4',
      eval_cp: 30,
    }
    global.fetch = mockFetch(payload)

    const result = await fetchAnalysis(START_FEN)
    expect(result.candidates).toHaveLength(1)
    expect(result.eval_cp).toBe(30)
  })

  it('throws when not ok', async () => {
    global.fetch = mockFetch(null, false)
    await expect(fetchAnalysis(START_FEN)).rejects.toThrow('analysis fetch failed')
  })
})

// ---------------------------------------------------------------------------
// fetchOpponentResponses
// ---------------------------------------------------------------------------

describe('fetchOpponentResponses', () => {
  it('POSTs to /api/opponent-responses', async () => {
    global.fetch = mockFetch({ responses: [] })
    await fetchOpponentResponses(START_FEN, 'e2e4')

    const [url, options] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(url).toBe('/api/opponent-responses')
    expect(options.method).toBe('POST')
  })

  it('includes fen and your_move_uci in the body', async () => {
    global.fetch = mockFetch({ responses: [] })
    await fetchOpponentResponses(START_FEN, 'e2e4')

    const body = JSON.parse(
      (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body,
    )
    expect(body.fen).toBe(START_FEN)
    expect(body.your_move_uci).toBe('e2e4')
  })

  it('throws when not ok', async () => {
    global.fetch = mockFetch(null, false)
    await expect(fetchOpponentResponses(START_FEN, 'e2e4')).rejects.toThrow(
      'opponent responses fetch failed',
    )
  })
})
