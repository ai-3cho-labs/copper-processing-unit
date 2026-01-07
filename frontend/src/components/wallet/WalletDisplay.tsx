'use client';

import { useWallet } from '@/hooks/useWallet';
import { cn } from '@/lib/cn';
import { getAddressUrl } from '@/lib/constants';

export interface WalletDisplayProps {
  /** Show wallet icon */
  showIcon?: boolean;
  /** Show copy button */
  showCopy?: boolean;
  /** Show explorer link */
  showExplorerLink?: boolean;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Additional class names */
  className?: string;
}

/**
 * Display connected wallet information
 */
export function WalletDisplay({
  showIcon = true,
  showCopy = false,
  showExplorerLink = false,
  size = 'md',
  className,
}: WalletDisplayProps) {
  const { address, shortAddress, walletIcon, walletName, connected } =
    useWallet();

  if (!connected || !address) {
    return null;
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(address);
      // Could add toast notification here
    } catch (error) {
      console.error('Failed to copy address:', error);
    }
  };

  const sizeClasses = {
    sm: 'text-sm gap-1.5',
    md: 'text-base gap-2',
    lg: 'text-lg gap-2.5',
  };

  const iconSizes = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
  };

  return (
    <div
      className={cn(
        'inline-flex items-center font-mono',
        sizeClasses[size],
        className
      )}
    >
      {/* Wallet icon */}
      {showIcon && walletIcon && (
        <img
          src={walletIcon}
          alt={walletName || 'Wallet'}
          className={cn('rounded-sm', iconSizes[size])}
        />
      )}

      {/* Address */}
      <span className="text-zinc-300">{shortAddress}</span>

      {/* Copy button */}
      {showCopy && (
        <button
          onClick={handleCopy}
          className="text-zinc-500 hover:text-zinc-300 transition-colors"
          aria-label="Copy address"
        >
          <svg
            className={iconSizes[size]}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>
        </button>
      )}

      {/* Explorer link */}
      {showExplorerLink && (
        <a
          href={getAddressUrl(address)}
          target="_blank"
          rel="noopener noreferrer"
          className="text-zinc-500 hover:text-white transition-colors"
          aria-label="View on explorer"
        >
          <svg
            className={iconSizes[size]}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
            />
          </svg>
        </a>
      )}
    </div>
  );
}

/**
 * Full wallet address display
 */
export function WalletAddressFull({ className }: { className?: string }) {
  const { address, connected } = useWallet();

  if (!connected || !address) {
    return null;
  }

  return (
    <code
      className={cn(
        'font-mono text-xs text-zinc-400 break-all',
        className
      )}
    >
      {address}
    </code>
  );
}
