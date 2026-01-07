'use client';

import { useWallet } from '@solana/wallet-adapter-react';
import { PageContainer } from '@/components/layout';
import { WalletGuard } from '@/components/wallet/WalletGuard';
import { ConnectWalletEmpty } from '@/components/ui';
import {
  MiningCard,
  TierProgress,
  PendingRewards,
  MiniLeaderboard,
  BuybackFeed,
  DistributionHistory,
} from '@/components/dashboard';
import {
  useUserStats,
  usePoolStatus,
  useLeaderboard,
  useBuybacks,
  useUserHistory,
} from '@/hooks/api';
import type { DistributionHistoryItem as ApiDistributionHistoryItem } from '@/types/api';
import type { DistributionHistoryItem } from '@/components/dashboard';
import { formatTimeAgo } from '@/lib/utils';

export default function DashboardPage() {
  return (
    <PageContainer>
      <WalletGuard
        notConnectedComponent={
          <div className="flex items-center justify-center min-h-[60vh]">
            <ConnectWalletEmpty />
          </div>
        }
      >
        <DashboardContent />
      </WalletGuard>
    </PageContainer>
  );
}

function DashboardContent() {
  const { publicKey } = useWallet();
  const wallet = publicKey?.toBase58() ?? null;

  // Fetch data
  const userStats = useUserStats(wallet);
  const pool = usePoolStatus();
  const leaderboard = useLeaderboard(5, wallet);
  const buybacks = useBuybacks(5);
  const history = useUserHistory(wallet, 5);

  // Transform history data to match component interface
  const historyItems: DistributionHistoryItem[] | null = history.data
    ? history.data.map((item: ApiDistributionHistoryItem) => ({
        id: item.distribution_id,
        amount: item.amount_received,
        hashPower: item.hash_power,
        sharePercent: 0, // Not provided by API, could calculate if needed
        distributedAt: new Date(item.executed_at),
        timeAgo: formatTimeAgo(item.executed_at),
        txSignature: item.tx_signature ?? undefined,
      }))
    : null;

  return (
    <div className="space-y-4 lg:space-y-6">
      {/* Page Header */}
      <div className="hidden lg:block">
        <h1 className="text-2xl text-copper">
          MINING DASHBOARD
        </h1>
        <p className="text-sm text-text-muted mt-1">
          Track your mining operation and rewards
        </p>
      </div>

      {/* Mobile Header */}
      <div className="lg:hidden pt-2">
        <h1 className="text-xl font-bold text-text-primary">Dashboard</h1>
      </div>

      {/* Main Grid */}
      <div className="grid gap-4 lg:gap-6 lg:grid-cols-2">
        {/* Mining Card - Full width on mobile, left column on desktop */}
        <MiningCard
          data={userStats.data}
          isLoading={userStats.isLoading}
          className="lg:row-span-1"
        />

        {/* Pending Rewards - Right column on desktop */}
        <PendingRewards
          pendingReward={userStats.data?.pendingReward ?? 0}
          pool={pool.data}
          isLoading={userStats.isLoading || pool.isLoading}
        />

        {/* Tier Progress - Full width */}
        <TierProgress
          tier={userStats.data?.tier ?? { tier: 1, name: 'Ore', emoji: '🪨', multiplier: 1 }}
          nextTier={userStats.data?.nextTier ?? null}
          streakHours={userStats.data?.streakHours ?? 0}
          progress={userStats.data?.progressToNextTier ?? 0}
          hoursToNextTier={userStats.data?.hoursToNextTier ?? null}
          isLoading={userStats.isLoading}
          showAllTiers
          className="lg:col-span-2"
        />

        {/* Mini Leaderboard - Left column */}
        <MiniLeaderboard
          entries={leaderboard.data}
          userRank={userStats.data?.rank}
          userWallet={wallet}
          isLoading={leaderboard.isLoading}
        />

        {/* Buyback Feed - Right column */}
        <BuybackFeed
          buybacks={buybacks.data}
          isLoading={buybacks.isLoading}
          poolBalance={pool.data?.balance}
          poolValueUsd={pool.data?.valueUsd}
        />

        {/* Distribution History - Full width */}
        <DistributionHistory
          history={historyItems}
          isLoading={history.isLoading}
          className="lg:col-span-2"
        />
      </div>
    </div>
  );
}
