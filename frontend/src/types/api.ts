/**
 * API Response Types
 * These types match the backend API responses exactly.
 * Reference: backend/app/api/routes.py
 */

// ===========================================
// Core Domain Types
// ===========================================

/** Tier information for a user's current holding tier */
export interface TierInfo {
  /** Tier number (1-6) */
  tier: number;
  /** Tier name (e.g., "Ore", "Diamond Hands") */
  name: string;
  /** Tier emoji */
  emoji: string;
  /** Reward multiplier (1.0x - 5.0x) */
  multiplier: number;
}

/** Full tier configuration including requirements */
export interface TierConfig extends TierInfo {
  /** Minimum hours required to reach this tier */
  min_hours: number;
}

// ===========================================
// API Response Types
// ===========================================

/** GET /api/stats - Global statistics */
export interface GlobalStatsResponse {
  /** Total number of token holders */
  total_holders: number;
  /** 24-hour trading volume */
  total_volume_24h: number;
  /** Total SOL spent on buybacks */
  total_buybacks_sol: number;
  /** Total tokens distributed (human-readable) */
  total_distributed: number;
  /** When last balance snapshot occurred (ISO string) */
  last_snapshot_at: string | null;
  /** When last distribution was executed (ISO string) */
  last_distribution_at: string | null;
}

/** GET /api/user/{wallet} - User mining statistics */
export interface UserStatsResponse {
  /** User's wallet address */
  wallet: string;
  /** Current token balance (human-readable) */
  balance: number;
  /** Current token balance (raw with decimals) */
  balance_raw: number;
  /** Time-weighted average balance (24h, human-readable) */
  twab: number;
  /** TWAB raw value */
  twab_raw: number;
  /** Current holding tier info */
  tier: TierInfo;
  /** Current streak multiplier */
  multiplier: number;
  /** Hash power (TWAB x multiplier) */
  hash_power: number;
  /** Hours since last sell */
  streak_hours: number;
  /** When current streak started (ISO string) */
  streak_start: string | null;
  /** Next tier info (null if at max) */
  next_tier: TierInfo | null;
  /** Hours until next tier (null if at max) */
  hours_to_next_tier: number | null;
  /** Global rank by hash power */
  rank: number | null;
  /** Estimated pending reward from pool */
  pending_reward_estimate: number;
}

/** GET /api/user/{wallet}/history - Distribution history item */
export interface DistributionHistoryItem {
  /** UUID of the distribution */
  distribution_id: string;
  /** When distribution was executed (ISO string) */
  executed_at: string;
  /** User's TWAB at that time */
  twab: number;
  /** User's multiplier at that time */
  multiplier: number;
  /** User's hash power (TWAB x multiplier) */
  hash_power: number;
  /** Tokens received (human-readable) */
  amount_received: number;
  /** Solana transaction signature */
  tx_signature: string | null;
}

/** GET /api/leaderboard - Leaderboard entry */
export interface LeaderboardEntry {
  /** Position on leaderboard (1-indexed) */
  rank: number;
  /** Full wallet address */
  wallet: string;
  /** Shortened wallet format (first 4 + last 4) */
  wallet_short: string;
  /** User's hash power */
  hash_power: number;
  /** Current tier info */
  tier: TierInfo;
  /** Streak multiplier */
  multiplier: number;
}

/** GET /api/pool - Airdrop pool status */
export interface PoolStatusResponse {
  /** Pool balance (human-readable tokens) */
  balance: number;
  /** Pool balance (raw with decimals) */
  balance_raw: number;
  /** Current USD value of pool */
  value_usd: number;
  /** When last distribution occurred (ISO string) */
  last_distribution: string | null;
  /** Hours elapsed since last distribution */
  hours_since_last: number | null;
  /** Hours until 24h time trigger */
  hours_until_time_trigger: number | null;
  /** Is pool >= $250 USD? */
  threshold_met: boolean;
  /** Has 24h elapsed since last distribution? */
  time_trigger_met: boolean;
  /** Next trigger type */
  next_trigger: 'threshold' | 'time' | 'none';
}

/** GET /api/buybacks - Buyback transaction */
export interface BuybackItem {
  /** Solana transaction signature */
  tx_signature: string;
  /** SOL amount used for buyback */
  sol_amount: number;
  /** COPPER tokens purchased (human-readable) */
  copper_amount: number;
  /** Price per token at execution (SOL/COPPER) */
  price_per_token: number | null;
  /** When buyback occurred (ISO string) */
  executed_at: string;
}

/** GET /api/distributions - Distribution record */
export interface DistributionItem {
  /** UUID of distribution */
  id: string;
  /** Total tokens distributed (human-readable) */
  pool_amount: number;
  /** USD value of pool at execution */
  pool_value_usd: number | null;
  /** Sum of all recipients' hash power */
  total_hashpower: number;
  /** Number of wallets that received rewards */
  recipient_count: number;
  /** What triggered the distribution */
  trigger_type: 'threshold' | 'time';
  /** When distribution occurred (ISO string) */
  executed_at: string;
}

// ===========================================
// Error Types
// ===========================================

/** API error response */
export interface ApiError {
  /** HTTP status code */
  status: number;
  /** Error message */
  message: string;
  /** Additional error detail */
  detail?: string;
}

/** Type guard for API errors */
export function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'status' in error &&
    'message' in error
  );
}

// ===========================================
// Request Parameter Types
// ===========================================

/** Pagination parameters */
export interface PaginationParams {
  /** Number of items to return (default: 10) */
  limit?: number;
  /** Offset for pagination */
  offset?: number;
}
