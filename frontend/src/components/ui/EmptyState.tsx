'use client';

import { cn } from '@/lib/cn';
import { Button } from './Button';

export interface EmptyStateProps {
  /** Icon (emoji or ASCII art) */
  icon?: string;
  /** Title */
  title: string;
  /** Description */
  description?: string;
  /** Action button */
  action?: {
    label: string;
    onClick: () => void;
  };
  /** Additional class names */
  className?: string;
}

/**
 * Empty state component
 * Shown when there's no data to display
 */
export function EmptyState({
  icon = '[ ]',
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-8 text-center',
        className
      )}
    >
      {/* Icon */}
      <div
        className="text-4xl text-copper-dim mb-4 font-mono"
        aria-hidden="true"
      >
        {icon}
      </div>

      {/* Title */}
      <h3 className="text-lg font-semibold text-zinc-300 mb-2">{title}</h3>

      {/* Description */}
      {description && (
        <p className="text-sm text-zinc-500 max-w-sm mb-4">{description}</p>
      )}

      {/* Action */}
      {action && (
        <Button variant="outline" size="sm" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}

/**
 * Preset empty states for common scenarios
 */
export function NoDataEmpty() {
  return (
    <EmptyState
      icon="()"
      title="No data yet"
      description="Check back later for updates"
    />
  );
}

export function NoResultsEmpty({ query }: { query?: string }) {
  return (
    <EmptyState
      icon="?"
      title="No results found"
      description={
        query ? `No results for "${query}"` : 'Try adjusting your search'
      }
    />
  );
}

export function NoHistoryEmpty() {
  return (
    <EmptyState
      icon="[]"
      title="No history yet"
      description="Your distribution history will appear here"
    />
  );
}

export function NoBuybacksEmpty() {
  return (
    <EmptyState
      icon="$"
      title="No buybacks yet"
      description="Buybacks will appear here when executed"
    />
  );
}

export function ConnectWalletEmpty({ onConnect }: { onConnect?: () => void }) {
  return (
    <EmptyState
      icon="🔗"
      title="Connect your wallet"
      description="Connect your Solana wallet to view your mining stats"
      action={onConnect ? { label: 'Connect Wallet', onClick: onConnect } : undefined}
    />
  );
}
