'use client';

import { useWallet as useSolanaWallet } from '@solana/wallet-adapter-react';
import { useWalletModal } from '@solana/wallet-adapter-react-ui';
import { useMemo, useCallback } from 'react';
import { shortenAddress } from '@/lib/utils';

/**
 * Custom wallet hook
 * Provides simplified access to wallet state and actions
 */
export function useWallet() {
  const {
    publicKey,
    connected,
    connecting,
    disconnecting,
    disconnect: solanaDisconnect,
    wallet,
    wallets,
    select,
  } = useSolanaWallet();

  const { setVisible } = useWalletModal();

  // Full wallet address
  const address = useMemo(() => {
    return publicKey?.toBase58() || null;
  }, [publicKey]);

  // Shortened address (e.g., "Abc1...xyz9")
  const shortAddress = useMemo(() => {
    if (!address) return null;
    return shortenAddress(address);
  }, [address]);

  // Open wallet modal
  const openModal = useCallback(() => {
    setVisible(true);
  }, [setVisible]);

  // Disconnect with cleanup
  const disconnect = useCallback(async () => {
    try {
      await solanaDisconnect();
    } catch (error) {
      console.error('Failed to disconnect wallet:', error);
    }
  }, [solanaDisconnect]);

  // Check if wallet is ready (connected and not in transition)
  const isReady = connected && !connecting && !disconnecting;

  return {
    // State
    address,
    shortAddress,
    publicKey,
    connected,
    connecting,
    disconnecting,
    isReady,

    // Wallet info
    walletName: wallet?.adapter.name || null,
    walletIcon: wallet?.adapter.icon || null,
    availableWallets: wallets,

    // Actions
    openModal,
    disconnect,
    select,
  };
}

/**
 * Hook to check if a wallet is connected
 * Returns just the connection status for simple checks
 */
export function useIsConnected(): boolean {
  const { connected } = useSolanaWallet();
  return connected;
}

/**
 * Hook to get just the wallet address
 * Returns null if not connected
 */
export function useWalletAddress(): string | null {
  const { publicKey } = useSolanaWallet();
  return useMemo(() => publicKey?.toBase58() || null, [publicKey]);
}
