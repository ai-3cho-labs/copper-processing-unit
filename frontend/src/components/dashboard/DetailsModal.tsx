'use client';

import { useEffect, useState, useCallback, useMemo } from 'react';
import { cn } from '@/lib/cn';
import { formatTimeAgo } from '@/lib/utils';
import { useWalletAddress } from '@/hooks/useWallet';
import { useSwipeGesture, useIsMobile, usePrefersReducedMotion } from '@/hooks';
import {
  useUserStats,
  usePoolStatus,
  useLeaderboard,
  useUserHistory,
} from '@/hooks/api';
import { MiningCard } from './MiningCard';
import { TierProgress } from './TierProgress';
import { PendingRewards } from './PendingRewards';
import { MiniLeaderboard } from './MiniLeaderboard';
import { RewardHistory } from './RewardHistory';
import type { RewardHistoryItem } from './RewardHistory';

interface DetailsModalProps {
  open: boolean;
  onClose: () => void;
}

type TabId = 'overview' | 'leaderboard' | 'history' | 'pool';

const TABS: { id: TabId; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'leaderboard', label: 'Leaderboard' },
  { id: 'history', label: 'History' },
  { id: 'pool', label: 'Pool' },
];

/**
 * Full-screen modal with detailed mining stats.
 * Desktop: centered modal with terminal styling
 * Mobile: full-screen slide-up sheet with swipe-to-close
 */
export function DetailsModal({ open, onClose }: DetailsModalProps) {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [isClosing, setIsClosing] = useState(false);
  const wallet = useWalletAddress();
  const isMobile = useIsMobile();
  const prefersReducedMotion = usePrefersReducedMotion();

  // Fetch all data
  const { data: stats, isLoading: statsLoading } = useUserStats(wallet);
  const { data: pool, isLoading: poolLoading } = usePoolStatus();
  const { data: leaderboard, isLoading: leaderboardLoading } = useLeaderboard(25, wallet);
  const { data: rawHistory, isLoading: historyLoading } = useUserHistory(wallet, 20);

  // Transform history data to RewardHistoryItem format
  const history: RewardHistoryItem[] | null = useMemo(() => {
    if (!rawHistory) return null;
    return rawHistory.map((item) => ({
      id: item.distribution_id,
      amount: item.amount_received,
      hashPower: item.hash_power,
      sharePercent: 0, // Not provided by API
      paidAt: new Date(item.executed_at),
      timeAgo: formatTimeAgo(item.executed_at),
      txSignature: item.tx_signature ?? undefined,
    }));
  }, [rawHistory]);

  // Handle animated close
  const handleClose = useCallback(() => {
    if (prefersReducedMotion) {
      onClose();
      return;
    }
    setIsClosing(true);
    setTimeout(() => {
      onClose();
      setIsClosing(false);
    }, 200);
  }, [onClose, prefersReducedMotion]);

  // Swipe gesture for close
  const tabIndex = TABS.findIndex((t) => t.id === activeTab);

  const { handlers: swipeHandlers, dragOffset, isDragging } = useSwipeGesture({
    onSwipeDown: handleClose,
    onSwipeLeft: () => {
      const nextTab = TABS[tabIndex + 1];
      if (nextTab) {
        setActiveTab(nextTab.id);
      }
    },
    onSwipeRight: () => {
      const prevTab = TABS[tabIndex - 1];
      if (prevTab) {
        setActiveTab(prevTab.id);
      }
    },
    threshold: 80,
    velocityThreshold: 0.5,
    enabled: isMobile && open,
  });

  // Handle escape key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleClose();
      }
    },
    [handleClose]
  );

  // Bind escape key and prevent body scroll
  useEffect(() => {
    if (open) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [open, handleKeyDown]);

  // Reset closing state when modal opens
  useEffect(() => {
    if (open) {
      setIsClosing(false);
    }
  }, [open]);

  if (!open) return null;

  // Calculate transform for drag feedback
  const dragTransform = isDragging && dragOffset.y > 0
    ? `translateY(${dragOffset.y}px)`
    : undefined;

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div
        className={cn(
          'absolute inset-0 bg-black/80 backdrop-blur-sm',
          !prefersReducedMotion && 'transition-opacity duration-200',
          isClosing && 'opacity-0'
        )}
        onClick={handleClose}
      />

      {/* Modal Content */}
      <div
        className={cn(
          'absolute bg-bg-dark border border-gray-800 overflow-hidden flex flex-col',
          // Mobile: full-screen from bottom with safe area
          'inset-x-0 bottom-0 top-12 xs:top-14 sm:top-16 rounded-t-2xl pb-safe',
          // Desktop: centered modal (reset mobile positioning)
          'lg:inset-auto lg:top-1/2 lg:left-1/2 lg:-translate-x-1/2 lg:-translate-y-1/2',
          'lg:w-full lg:max-w-2xl lg:h-[80vh] lg:rounded-lg lg:pb-0',
          // Animations
          !prefersReducedMotion && !isDragging && [
            isClosing ? 'animate-slide-down lg:animate-none lg:opacity-0' : 'animate-slide-up lg:animate-fade-in',
          ]
        )}
        style={{
          transform: dragTransform,
          transition: isDragging ? 'none' : undefined,
        }}
        {...swipeHandlers}
      >
        {/* Drag Handle - Mobile only */}
        <div className="lg:hidden flex justify-center pt-3 pb-1">
          <div className="w-10 h-1 rounded-full bg-gray-600" />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2 lg:py-3 border-b border-gray-800">
          <h2 className="text-base sm:text-lg font-mono text-white">Mining Details</h2>
          <button
            onClick={handleClose}
            className="p-3 -mr-1.5 text-gray-400 hover:text-white active:scale-95 transition-all rounded-lg"
            aria-label="Close"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-800">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex-1 py-3 text-sm font-mono transition-colors relative',
                'min-h-[44px]', // Apple HIG minimum touch target
                activeTab === tab.id
                  ? 'text-white'
                  : 'text-gray-500 active:text-gray-300'
              )}
            >
              <span className="truncate">{tab.label}</span>
              {activeTab === tab.id && (
                <div className="absolute bottom-0 left-2 right-2 h-0.5 bg-white rounded-full" />
              )}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-3 xs:p-4">
          <div
            key={activeTab}
            className={cn(!prefersReducedMotion && 'animate-fade-in')}
          >
            {activeTab === 'overview' && (
              <div className="space-y-4">
                <MiningCard data={stats ?? null} isLoading={statsLoading} />
                {stats && (
                  <TierProgress
                    tier={stats.tier}
                    nextTier={stats.nextTier}
                    streakHours={stats.streakHours}
                    progress={stats.progressToNextTier}
                    hoursToNextTier={stats.hoursToNextTier}
                    isLoading={statsLoading}
                    showAllTiers
                  />
                )}
              </div>
            )}

            {activeTab === 'leaderboard' && (
              <MiniLeaderboard
                entries={leaderboard ?? null}
                userRank={stats?.rank}
                userWallet={wallet}
                isLoading={leaderboardLoading}
                showViewAll={false}
                limit={25}
              />
            )}

            {activeTab === 'history' && (
              <RewardHistory
                history={history ?? null}
                isLoading={historyLoading}
                showViewAll={false}
                limit={20}
              />
            )}

            {activeTab === 'pool' && (
              <PendingRewards
                pendingReward={stats?.pendingReward ?? 0}
                pool={pool ?? null}
                isLoading={poolLoading || statsLoading}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
