/**
 * Domain Models
 * Transformed/computed types for UI consumption.
 * These extend API types with additional computed properties.
 */

import type { TierInfo } from './api';

// ===========================================
// User Models
// ===========================================

/** Transformed user mining statistics for UI */
export interface UserMiningStats {
  /** Wallet address */
  wallet: string;
  /** Current balance (human-readable) */
  balance: number;
  /** Current balance (raw) */
  balanceRaw: number;
  /** Time-weighted average balance */
  twab: number;
  /** Current tier info */
  tier: TierInfo;
  /** Current multiplier */
  multiplier: number;
  /** Hash power (TWAB x multiplier) */
  hashPower: number;
  /** Streak in hours */
  streakHours: number;
  /** Streak in days (computed) */
  streakDays: number;
  /** When streak started */
  streakStart: Date | null;
  /** Next tier info (null if at max) */
  nextTier: TierInfo | null;
  /** Hours until next tier */
  hoursToNextTier: number | null;
  /** Progress to next tier (0-100 percentage) */
  progressToNextTier: number;
  /** Global rank */
  rank: number | null;
  /** Pending reward estimate */
  pendingReward: number;
}

// ===========================================
// Pool Models
// ===========================================

/** Payout threshold in USD */
export const PAYOUT_THRESHOLD_USD = 250;

/** Max hours between payouts */
export const PAYOUT_MAX_HOURS = 24;

// Legacy aliases for backwards compatibility
export const DISTRIBUTION_THRESHOLD_USD = PAYOUT_THRESHOLD_USD;
export const DISTRIBUTION_MAX_HOURS = PAYOUT_MAX_HOURS;

/** Transformed pool information for UI */
export interface PoolInfo {
  /** Pool balance (human-readable) */
  balance: number;
  /** Pool balance (raw) */
  balanceRaw: number;
  /** Current USD value */
  valueUsd: number;
  /** Last payout timestamp */
  lastPayout: Date | null;
  /** Hours since last payout */
  hoursSinceLast: number | null;
  /** Hours until time trigger */
  hoursUntilTrigger: number | null;
  /** Progress to $250 threshold (0-100 percentage) */
  progressToThreshold: number;
  /** Is threshold met? */
  thresholdMet: boolean;
  /** Is time trigger met? */
  timeTriggerMet: boolean;
  /** Next trigger type */
  nextTrigger: 'threshold' | 'time' | 'none';
}

// ===========================================
// Tier Models
// ===========================================

/** Tier ID type (1-6) */
export type TierId = 1 | 2 | 3 | 4 | 5 | 6;

/** Static tier configuration */
export const TIER_CONFIG: Record<TierId, { name: string; emoji: string; multiplier: number; minHours: number }> = {
  1: { name: 'Ore', emoji: '🪨', multiplier: 1.0, minHours: 0 },
  2: { name: 'Raw Copper', emoji: '🔶', multiplier: 1.25, minHours: 6 },
  3: { name: 'Refined', emoji: '⚡', multiplier: 1.5, minHours: 12 },
  4: { name: 'Industrial', emoji: '🏭', multiplier: 2.5, minHours: 72 },
  5: { name: 'Master Miner', emoji: '👑', multiplier: 3.5, minHours: 168 },
  6: { name: 'Diamond Hands', emoji: '💎', multiplier: 5.0, minHours: 720 },
};

/** Get tier by ID */
export function getTierById(id: TierId) {
  return TIER_CONFIG[id];
}

/** Get all tiers as an array */
export function getAllTiers() {
  return Object.entries(TIER_CONFIG).map(([id, config]) => ({
    tier: parseInt(id) as TierId,
    ...config,
  }));
}

// ===========================================
// Leaderboard Models
// ===========================================

/** Leaderboard entry with formatted data */
export interface LeaderboardUser {
  /** Position on leaderboard */
  rank: number;
  /** Full wallet address */
  wallet: string;
  /** Shortened wallet (4...4) */
  walletShort: string;
  /** Hash power */
  hashPower: number;
  /** Tier info */
  tier: TierInfo;
  /** Multiplier */
  multiplier: number;
  /** Is this the connected user? */
  isCurrentUser: boolean;
}

// ===========================================
// Transaction Models
// ===========================================

/** Reward activity with formatted data */
export interface FormattedRewardActivity {
  /** Transaction signature */
  txSignature: string;
  /** SOL amount */
  solAmount: number;
  /** COPPER amount */
  copperAmount: number;
  /** Price per token */
  pricePerToken: number | null;
  /** Execution timestamp */
  executedAt: Date;
  /** Relative time (e.g., "2 min ago") */
  timeAgo: string;
}

/** Payout with formatted data */
export interface FormattedPayout {
  /** Payout ID */
  id: string;
  /** Pool amount */
  poolAmount: number;
  /** USD value */
  poolValueUsd: number | null;
  /** Total hash power */
  totalHashpower: number;
  /** Recipient count */
  recipientCount: number;
  /** Trigger type */
  triggerType: 'threshold' | 'time';
  /** Execution timestamp */
  executedAt: Date;
  /** Relative time */
  timeAgo: string;
}

// Legacy type aliases for backwards compatibility
export type FormattedBuyback = FormattedRewardActivity;
export type FormattedDistribution = FormattedPayout;
