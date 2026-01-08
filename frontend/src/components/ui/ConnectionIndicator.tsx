'use client';

/**
 * Connection Indicator
 *
 * Displays WebSocket connection status.
 * - Desktop: Terminal-style text [LIVE], [SYNC], [OFFLINE]
 * - Mobile: Simple colored dot
 *
 * Click to force reconnection attempt.
 */

import { FC } from 'react';
import { useSocketContext } from '@/components/providers/SocketProvider';
import { useIsDesktop } from '@/hooks';
import { cn } from '@/lib/cn';

// ============================================================================
// Types
// ============================================================================

export interface ConnectionIndicatorProps {
  /** Additional CSS classes */
  className?: string;
  /** Show in desktop mode regardless of screen size */
  forceDesktop?: boolean;
  /** Show in mobile mode regardless of screen size */
  forceMobile?: boolean;
}

// ============================================================================
// Component
// ============================================================================

export const ConnectionIndicator: FC<ConnectionIndicatorProps> = ({
  className,
  forceDesktop,
  forceMobile,
}) => {
  const { status, forceReconnect } = useSocketContext();
  const isDesktopScreen = useIsDesktop();

  // Determine which mode to render
  const showDesktop = forceDesktop || (!forceMobile && isDesktopScreen);

  const handleClick = () => {
    if (status === 'disconnected') {
      forceReconnect();
    }
  };

  if (showDesktop) {
    return <DesktopIndicator status={status} onClick={handleClick} className={className} />;
  }

  return <MobileIndicator status={status} onClick={handleClick} className={className} />;
};

// ============================================================================
// Desktop Indicator
// ============================================================================

interface IndicatorProps {
  status: 'connected' | 'connecting' | 'disconnected';
  onClick: () => void;
  className?: string;
}

const DesktopIndicator: FC<IndicatorProps> = ({ status, onClick, className }) => {
  const labels = {
    connected: '[LIVE]',
    connecting: '[SYNC]',
    disconnected: '[OFFLINE]',
  };

  const colors = {
    connected: 'text-green-400',
    connecting: 'text-yellow-400 animate-pulse',
    disconnected: 'text-gray-500 hover:text-gray-400',
  };

  const canClick = status === 'disconnected';

  return (
    <button
      onClick={onClick}
      disabled={!canClick}
      className={cn(
        'font-mono text-xs transition-colors',
        colors[status],
        canClick && 'cursor-pointer',
        !canClick && 'cursor-default',
        className
      )}
      title={canClick ? 'Click to reconnect' : `Status: ${status}`}
    >
      {labels[status]}
    </button>
  );
};

// ============================================================================
// Mobile Indicator
// ============================================================================

const MobileIndicator: FC<IndicatorProps> = ({ status, onClick, className }) => {
  const colors = {
    connected: 'bg-green-400',
    connecting: 'bg-yellow-400 animate-pulse',
    disconnected: 'bg-gray-500',
  };

  const canClick = status === 'disconnected';

  return (
    <button
      onClick={onClick}
      disabled={!canClick}
      className={cn(
        'inline-flex items-center justify-center w-6 h-6 rounded-full transition-colors',
        canClick && 'cursor-pointer hover:bg-gray-700',
        !canClick && 'cursor-default',
        className
      )}
      title={canClick ? 'Click to reconnect' : `Status: ${status}`}
    >
      <span
        className={cn(
          'w-2 h-2 rounded-full',
          colors[status]
        )}
      />
    </button>
  );
};
