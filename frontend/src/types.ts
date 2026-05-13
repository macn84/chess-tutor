/**
 * Shared TypeScript types for Chess Tutor.
 *
 * All API response shapes are mirrored here so the frontend stays in sync
 * with the Flask backend without a codegen step.
 */

/** A single Stockfish candidate move with engine score and teaching prose. */
export interface CandidateMove {
  /** Standard algebraic notation (e.g. "Nf3"). */
  san: string;
  /** UCI notation (e.g. "g1f3"). */
  uci: string;
  /** Centipawn score from White's perspective (mate ≈ ±10 000). */
  score_cp: number;
  /** Human-readable score string (e.g. "+0.3", "-M"). */
  score_label: string;
  /** Principal variation in SAN, up to 6 ply. */
  pv_san: string[];
  /** One-sentence prose explanation of why this move is played. */
  explanation: string;
  /** Short opening-book label (e.g. "Sicilian Defense"). Empty when not in book. */
  label: string;
}

/** An opponent move shown in the "If opponent plays…" panel. */
export interface OpponentResponse {
  /** Move in SAN notation. */
  san: string;
  /** Centipawn score from White's perspective. */
  score_cp: number;
  /** One-sentence explanation of the opponent's idea. */
  explanation: string;
  /** Opening-book label for this response. */
  label: string;
  /** Teaching note about what the player should plan after this reply. */
  follow_up_idea: string;
  /** Name of the opening/variation that arises, if the position is in the book. */
  resulting_opening: string;
  /** True when the resulting position is in the opening book. */
  in_book: boolean;
}

/**
 * Opening-book entry returned by ``GET /api/opening``.
 *
 * ``found: false`` when the position is not in the book; all other fields are
 * absent in that case.
 */
export interface OpeningEntry {
  found: boolean;
  /** ECO code (e.g. "B90"). */
  eco?: string;
  /** Opening family name (e.g. "Sicilian Defense"). */
  opening_name?: string;
  /** Variation name within the opening (e.g. "Najdorf Variation"). */
  variation_name?: string;
  /** List of strategic ideas for this position. */
  strategic_ideas?: string[];
  /** Main-line continuations in SAN. */
  main_line_moves?: string[];
}

/** Response from ``POST /api/analyze``. */
export interface AnalysisResult {
  /** Ranked candidate moves, best first. */
  candidates: CandidateMove[];
  /** SAN of the top-ranked move. */
  best_move_san: string;
  /** Centipawn evaluation of the position from White's perspective. */
  eval_cp: number;
}

/** Response from ``POST /api/opponent-responses``. */
export interface OpponentResponsesResult {
  /** Top opponent replies, ranked by engine score. */
  responses: OpponentResponse[];
}

/** One entry in the navigable move history. */
export interface GameMove {
  /** Move in SAN notation. */
  san: string;
  /** Move in UCI notation (used to derive highlighting squares). */
  uci: string;
  /** FEN of the position *after* this move. */
  fen_after: string;
}

// ---------------------------------------------------------------------------
// Game Analysis types
// ---------------------------------------------------------------------------

/** Filters for fetching games from Chess.com. Username comes from server env. */
export interface GameFilter {
  start_date: string;  // YYYY-MM-DD
  end_date: string;    // YYYY-MM-DD
  time_class: 'rapid' | 'blitz' | 'bullet' | 'daily' | 'all';
  color: 'white' | 'black' | 'both';
  result: 'win' | 'loss' | 'draw' | 'all';
  termination: 'all' | 'checkmate' | 'resignation' | 'timeout' | 'abandonment'
    | 'draw_agreement' | 'draw_repetition' | 'draw_stalemate' | 'draw_50move' | 'draw_insufficient';
  rated: 'all' | 'rated' | 'unrated';
  min_opponent_rating: number | null;
  max_opponent_rating: number | null;
  max_games: 5 | 25 | 50 | 100 | 200;
}

/** A game fetched from Chess.com (includes PGN for analysis). */
export interface FetchedGame {
  url: string;
  pgn: string;
  time_class: string;
  color: string;
  result: string;
  eco: string;
  opening_name: string;
  white_username: string;
  black_username: string;
  white_rating: number;
  black_rating: number;
  end_time: number;
  accuracies?: { white: number; black: number } | null;
}

/** A single mistake/blunder found during batch analysis. */
export interface MistakeRecord {
  move_number: number;
  phase: 'opening' | 'middlegame' | 'endgame';
  severity: 'blunder' | 'mistake' | 'inaccuracy';
  move_played_san: string;
  best_move_san: string;
  best_pv_san: string[];
  cp_loss: number;
  fen_before: string;
  game_url?: string;
}

/** Opening performance stat row. */
export interface OpeningStat {
  eco: string;
  opening_name: string;
  color: 'white' | 'black';
  player_move_1: string;
  opponent_move_1: string;
  games: number;
  wins: number;
  win_rate: number;
  avg_cp_loss: number;
}

/** Aggregated patterns across a set of analyzed games. */
export interface AnalysisPatterns {
  username: string;
  total_games: number;
  wins: number;
  losses: number;
  draws: number;
  blunders_per_game: number;
  mistakes_per_game: number;
  inaccuracies_per_game: number;
  avg_cp_loss: number;
  phase_distribution: { opening: number; middlegame: number; endgame: number };
  opening_stats: OpeningStat[];
  top_blunders: MistakeRecord[];
  mistake_move_numbers: { move_number: number; count: number }[];
  severity_totals: { blunder: number; mistake: number; inaccuracy: number };
}

/** LLM or fallback coaching insights. */
export interface CoachingInsightsResult {
  insights: string;
  llm_used: boolean;
}

/** Job status response from /api/games/status. */
export interface AnalysisJobStatus {
  status: 'running' | 'done' | 'error';
  progress: number;
  analyzed_count: number;
  total: number;
  error?: string;
}
