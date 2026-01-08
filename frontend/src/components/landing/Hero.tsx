'use client';

import { cn } from '@/lib/cn';
import { formatCompactNumber } from '@/lib/utils';
import { ConnectButton } from '@/components/wallet/ConnectButton';

export interface HeroProps {
  /** Global stats for display */
  stats?: {
    totalHolders: number;
    totalDistributed: number;
  };
  /** Is stats loading */
  isLoading?: boolean;
  /** Additional class names */
  className?: string;
}

/**
 * Hero - Main landing page hero section
 * Monochrome terminal aesthetic with entrance animations
 */
export function Hero({ stats, isLoading, className }: HeroProps) {
  return (
    <section className={cn('relative py-12 lg:py-20 overflow-hidden', className)}>
      <div className="relative max-w-4xl mx-auto text-center px-4">
        {/* Main Title - Animated entrance */}
        <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold mb-6 animate-fade-slide-in">
          <span className="text-text-primary">THE WORKING MAN&apos;S</span>
          <br />
          <span className="text-white glow-white">COPPER MINE</span>
        </h1>

        {/* Tagline - Staggered entrance */}
        <p className="text-body lg:text-lg text-text-secondary mb-8 max-w-2xl mx-auto animate-fade-slide-in [animation-delay:150ms]">
          Your tokens mine $CPU around the clock. Trading fees fund the rewards
          pool. Hold longer, earn up to 5x more.
        </p>

        {/* CTA */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-10 animate-fade-slide-in [animation-delay:300ms]">
          <ConnectButton size="lg" />
          <a
            href="https://pump.fun"
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              'px-6 py-3 rounded-lg text-sm font-medium',
              'bg-white/10 hover:bg-white/20 text-white',
              'border border-white/20 hover:border-white/40',
              'transition-all duration-200'
            )}
          >
            Buy $CPU
          </a>
          <a
            href="#how-it-works"
            className="text-body-sm text-text-secondary hover:text-white transition-colors"
          >
            See how the mine works →
          </a>
        </div>

        {/* Stats (optional) */}
        {stats && !isLoading && (
          <div className="flex items-center justify-center gap-4 sm:gap-6 lg:gap-8 text-center animate-fade-slide-in [animation-delay:600ms]">
            <StatDisplay
              label="Miners"
              value={formatCompactNumber(stats.totalHolders)}
            />
            <div className="w-px h-8 bg-border" />
            <StatDisplay
              label="Distributed"
              value={`${formatCompactNumber(stats.totalDistributed)} $CPU`}
            />
          </div>
        )}
      </div>
    </section>
  );
}

/**
 * Stat display
 * Monochrome design
 */
function StatDisplay({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-lg sm:text-xl lg:text-2xl font-bold text-white tabular-nums">
        {value}
      </div>
      <div className="text-xs text-text-muted uppercase tracking-wider">{label}</div>
    </div>
  );
}
