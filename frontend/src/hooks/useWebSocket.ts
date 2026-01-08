'use client';

/**
 * WebSocket hook for real-time updates
 *
 * Connects when wallet is connected, disconnects when wallet disconnects.
 * Updates React Query cache on WebSocket events.
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useWalletAddress, useIsConnected } from './useWallet';
import {
  getSocket,
  disconnectSocket,
  subscribeToWallet,
  type DistributionExecutedPayload,
  type PoolUpdatedPayload,
  type TierChangedPayload,
  type SellDetectedPayload,
} from '@/lib/socket';
import {
  POOL_STATUS_QUERY_KEY,
  userStatsQueryKey,
} from './api';

// ============================================================================
// Types
// ============================================================================

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected';

export interface UseWebSocketReturn {
  status: ConnectionStatus;
  forceReconnect: () => void;
}

// ============================================================================
// Helpers
// ============================================================================

/**
 * Check if running in browser (not SSR)
 */
function isBrowser(): boolean {
  return typeof window !== 'undefined';
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useWebSocket(): UseWebSocketReturn {
  const queryClient = useQueryClient();
  const walletAddress = useWalletAddress();
  const isWalletConnected = useIsConnected();
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');

  // Use refs to avoid stale closures in event handlers
  const walletAddressRef = useRef<string | null>(walletAddress);
  const subscribedWalletRef = useRef<string | null>(null);

  // Keep ref in sync with current wallet address
  useEffect(() => {
    walletAddressRef.current = walletAddress;
  }, [walletAddress]);

  // ========================================================================
  // Event Handlers
  // ========================================================================

  /**
   * Handle pool:updated - update cache directly
   */
  const handlePoolUpdated = useCallback(
    (payload: PoolUpdatedPayload) => {
      queryClient.setQueryData(POOL_STATUS_QUERY_KEY, (old: unknown) => {
        if (!old) return old;
        return {
          ...(old as object),
          balance: payload.balance,
          value_usd: payload.value_usd,
          progress_to_threshold: payload.progress_to_threshold,
          threshold_met: payload.threshold_met,
          hours_until_time_trigger: payload.hours_until_time_trigger,
        };
      });
    },
    [queryClient]
  );

  /**
   * Handle distribution:executed - invalidate queries and show toast
   */
  const handleDistributionExecuted = useCallback(
    (payload: DistributionExecutedPayload) => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: POOL_STATUS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: ['distributions'] });
      queryClient.invalidateQueries({ queryKey: ['leaderboard'] });
      queryClient.invalidateQueries({ queryKey: ['globalStats'] });

      // Invalidate user stats if wallet is connected (use ref for fresh value)
      const currentWallet = walletAddressRef.current;
      if (currentWallet) {
        queryClient.invalidateQueries({
          queryKey: userStatsQueryKey(currentWallet),
        });
      }

      // Log for now - could trigger a toast/modal in SocketProvider
      console.log(
        '[WebSocket] Distribution executed:',
        payload.recipient_count,
        'recipients'
      );
    },
    [queryClient]
  );

  /**
   * Handle leaderboard:updated - signal only, refetch
   */
  const handleLeaderboardUpdated = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['leaderboard'] });
  }, [queryClient]);

  /**
   * Handle snapshot:taken - invalidate user stats
   */
  const handleSnapshotTaken = useCallback(() => {
    const currentWallet = walletAddressRef.current;
    if (currentWallet) {
      queryClient.invalidateQueries({
        queryKey: userStatsQueryKey(currentWallet),
      });
    }
    queryClient.invalidateQueries({ queryKey: ['globalStats'] });
  }, [queryClient]);

  /**
   * Handle tier:changed - invalidate user stats
   */
  const handleTierChanged = useCallback(
    (payload: TierChangedPayload) => {
      const currentWallet = walletAddressRef.current;
      if (currentWallet && payload.wallet === currentWallet) {
        queryClient.invalidateQueries({
          queryKey: userStatsQueryKey(currentWallet),
        });
      }
    },
    [queryClient]
  );

  /**
   * Handle sell:detected - invalidate user stats
   */
  const handleSellDetected = useCallback(
    (payload: SellDetectedPayload) => {
      const currentWallet = walletAddressRef.current;
      if (currentWallet && payload.wallet === currentWallet) {
        queryClient.invalidateQueries({
          queryKey: userStatsQueryKey(currentWallet),
        });
      }
    },
    [queryClient]
  );

  // ========================================================================
  // Force Reconnect
  // ========================================================================

  const forceReconnect = useCallback(() => {
    if (!isBrowser()) return;

    try {
      const socket = getSocket();
      if (socket.connected) {
        socket.disconnect();
      }
      setStatus('connecting');
      socket.connect();
    } catch {
      // getSocket throws during SSR
    }
  }, []);

  // ========================================================================
  // Main Connection Effect
  // ========================================================================

  useEffect(() => {
    // Don't run during SSR
    if (!isBrowser()) return;

    // Don't connect if wallet is not connected
    if (!isWalletConnected || !walletAddress) {
      disconnectSocket();
      setStatus('disconnected');
      subscribedWalletRef.current = null;
      return;
    }

    let socket: ReturnType<typeof getSocket>;
    try {
      socket = getSocket();
    } catch {
      // getSocket throws during SSR
      return;
    }

    // Connection handlers
    const onConnect = () => {
      setStatus('connected');
      // Subscribe to wallet room
      subscribeToWallet(walletAddress);
      subscribedWalletRef.current = walletAddress;
      console.log('[WebSocket] Connected');
    };

    const onDisconnect = () => {
      setStatus('disconnected');
      console.log('[WebSocket] Disconnected');
    };

    const onConnectError = (error: Error) => {
      setStatus('disconnected');
      console.warn('[WebSocket] Connection error:', error.message);
    };

    const onReconnect = () => {
      console.log('[WebSocket] Reconnected, refetching queries...');
      // Refetch all queries on reconnect
      queryClient.refetchQueries();
      // Resubscribe to wallet room (use ref for fresh value)
      const currentWallet = walletAddressRef.current;
      if (currentWallet) {
        subscribeToWallet(currentWallet);
      }
    };

    // Register event handlers
    socket.on('connect', onConnect);
    socket.on('disconnect', onDisconnect);
    socket.on('connect_error', onConnectError);
    socket.io.on('reconnect', onReconnect);

    // Register event listeners
    socket.on('pool:updated', handlePoolUpdated);
    socket.on('distribution:executed', handleDistributionExecuted);
    socket.on('leaderboard:updated', handleLeaderboardUpdated);
    socket.on('snapshot:taken', handleSnapshotTaken);
    socket.on('tier:changed', handleTierChanged);
    socket.on('sell:detected', handleSellDetected);

    // Connect
    setStatus('connecting');
    socket.connect();

    // Cleanup
    return () => {
      socket.off('connect', onConnect);
      socket.off('disconnect', onDisconnect);
      socket.off('connect_error', onConnectError);
      socket.io.off('reconnect', onReconnect);

      socket.off('pool:updated', handlePoolUpdated);
      socket.off('distribution:executed', handleDistributionExecuted);
      socket.off('leaderboard:updated', handleLeaderboardUpdated);
      socket.off('snapshot:taken', handleSnapshotTaken);
      socket.off('tier:changed', handleTierChanged);
      socket.off('sell:detected', handleSellDetected);
    };
  }, [
    isWalletConnected,
    walletAddress, // Still needed to trigger reconnect on wallet change
    queryClient,
    handlePoolUpdated,
    handleDistributionExecuted,
    handleLeaderboardUpdated,
    handleSnapshotTaken,
    handleTierChanged,
    handleSellDetected,
  ]);

  return { status, forceReconnect };
}
