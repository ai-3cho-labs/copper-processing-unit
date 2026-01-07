'use client';

import { useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { useWallet } from '@/hooks/useWallet';
import { LoadingPage } from '@/components/ui/LoadingSpinner';
import { TerminalCard } from '@/components/ui/TerminalCard';
import { ConnectButton } from './ConnectButton';

export interface WalletGuardProps {
  /** Children to render when wallet is connected */
  children: ReactNode;
  /** Redirect path when not connected (if set, redirects instead of showing message) */
  redirectTo?: string;
  /** Custom loading component */
  loadingComponent?: ReactNode;
  /** Custom not connected component */
  notConnectedComponent?: ReactNode;
}

/**
 * Wallet guard component
 * Protects routes that require wallet connection
 */
export function WalletGuard({
  children,
  redirectTo,
  loadingComponent,
  notConnectedComponent,
}: WalletGuardProps) {
  const router = useRouter();
  const { connected, connecting } = useWallet();

  // Handle redirect when not connected
  useEffect(() => {
    if (!connecting && !connected && redirectTo) {
      router.push(redirectTo);
    }
  }, [connected, connecting, redirectTo, router]);

  // Show loading while connecting
  if (connecting) {
    return (
      <>
        {loadingComponent || (
          <LoadingPage text="Connecting wallet..." />
        )}
      </>
    );
  }

  // Not connected - show message or redirect
  if (!connected) {
    // If redirect is set, show loading while redirecting
    if (redirectTo) {
      return (
        <>
          {loadingComponent || <LoadingPage text="Redirecting..." />}
        </>
      );
    }

    // Show not connected message
    return (
      <>
        {notConnectedComponent || <WalletNotConnected />}
      </>
    );
  }

  // Connected - render children
  return <>{children}</>;
}

/**
 * Default not connected component
 */
function WalletNotConnected() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center p-4">
      <TerminalCard
        title="Wallet Required"
        className="max-w-md w-full"
      >
        <div className="text-center py-6">
          {/* Icon */}
          <div className="text-4xl mb-4">🔐</div>

          {/* Title */}
          <h2 className="text-xl font-semibold text-zinc-200 mb-2">
            Connect Your Wallet
          </h2>

          {/* Description */}
          <p className="text-sm text-zinc-400 mb-6">
            Connect your Solana wallet to access your mining dashboard and view
            your rewards.
          </p>

          {/* Connect button */}
          <ConnectButton size="lg" />
        </div>
      </TerminalCard>
    </div>
  );
}

/**
 * Higher-order component version of WalletGuard
 */
export function withWalletGuard<P extends object>(
  Component: React.ComponentType<P>,
  guardProps?: Omit<WalletGuardProps, 'children'>
) {
  return function GuardedComponent(props: P) {
    return (
      <WalletGuard {...guardProps}>
        <Component {...props} />
      </WalletGuard>
    );
  };
}
