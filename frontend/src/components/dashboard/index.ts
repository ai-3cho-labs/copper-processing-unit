/**
 * Dashboard Components exports
 */

export { MiningCard } from './MiningCard';
export type { MiningCardProps } from './MiningCard';

export { TierProgress } from './TierProgress';
export type { TierProgressProps } from './TierProgress';

export { PendingRewards } from './PendingRewards';
export type { PendingRewardsProps } from './PendingRewards';

export { MiniLeaderboard } from './MiniLeaderboard';
export type { MiniLeaderboardProps } from './MiniLeaderboard';

export { RewardActivity } from './RewardActivity';
export type { RewardActivityProps } from './RewardActivity';

export { RewardHistory } from './RewardHistory';
export type {
  RewardHistoryProps,
  RewardHistoryItem,
} from './RewardHistory';

// Legacy exports for backwards compatibility during migration
export { RewardActivity as BuybackFeed } from './RewardActivity';
export { RewardHistory as DistributionHistory } from './RewardHistory';
