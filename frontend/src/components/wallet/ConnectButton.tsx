'use client';

import { useWalletModal } from '@solana/wallet-adapter-react-ui';
import { useWallet } from '@/hooks/useWallet';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/cn';
import { isValidWalletIconUrl } from '@/lib/validators';

export interface ConnectButtonProps {
  /** Button size */
  size?: 'sm' | 'md' | 'lg';
  /** Make button full width */
  fullWidth?: boolean;
  /** Custom class names */
  className?: string;
  /** Show wallet icon when connected */
  showIcon?: boolean;
}

/**
 * Wallet connect button
 * Shows connect button when disconnected, wallet info when connected
 */
export function ConnectButton({
  size = 'md',
  fullWidth = false,
  className,
  showIcon = true,
}: ConnectButtonProps) {
  const { connected, connecting, shortAddress, walletIcon, disconnect } =
    useWallet();
  const { setVisible } = useWalletModal();

  // Connecting state
  if (connecting) {
    return (
      <Button
        size={size}
        fullWidth={fullWidth}
        className={className}
        loading
        disabled
      >
        Connecting...
      </Button>
    );
  }

  // Connected state
  if (connected && shortAddress) {
    return (
      <div className={cn('flex items-center gap-2', fullWidth && 'w-full')}>
        {/* Wallet info button */}
        <Button
          variant="secondary"
          size={size}
          className={cn('flex-1', className)}
          onClick={() => setVisible(true)}
        >
          {showIcon && walletIcon && isValidWalletIconUrl(walletIcon) && (
            <img
              src={walletIcon}
              alt=""
              className="w-4 h-4 rounded-sm"
              aria-hidden
            />
          )}
          <span className="font-mono">{shortAddress}</span>
        </Button>

        {/* Disconnect button */}
        <Button
          variant="ghost"
          size={size}
          onClick={disconnect}
          aria-label="Disconnect wallet"
          className="px-2"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
            />
          </svg>
        </Button>
      </div>
    );
  }

  // Disconnected state
  return (
    <Button
      size={size}
      fullWidth={fullWidth}
      className={className}
      onClick={() => setVisible(true)}
    >
      Connect Wallet
    </Button>
  );
}
