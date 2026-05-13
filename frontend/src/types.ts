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
