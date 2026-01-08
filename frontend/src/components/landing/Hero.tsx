'use client';

import { cn } from '@/lib/cn';
import { formatCompactNumber } from '@/lib/utils';
import { ConnectButton } from '@/components/wallet/ConnectButton';
import { Card, PixelIcon } from '@/components/ui';

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
 * Monochrome terminal aesthetic
 */
export function Hero({ stats, isLoading, className }: HeroProps) {
  return (
    <section className={cn('relative py-12 lg:py-20 overflow-hidden', className)}>
      <div className="relative max-w-4xl mx-auto text-center px-4">
        {/* Main Title */}
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-6">
          <span className="text-text-primary">THE WORKING MAN&apos;S</span>
          <br />
          <span className="text-white glow-white">$CPU MINE</span>
        </h1>

        {/* Tagline */}
        <p className="text-lg sm:text-xl text-text-secondary mb-8 max-w-2xl mx-auto">
          Mine $CPU without the machines. Hold tokens, earn mining rewards
          from trading fees. The longer you hold, the more you mine.
        </p>

        {/* Key Points - Desktop Card Style */}
        <div className="hidden lg:block mb-10">
          <Card className="max-w-lg mx-auto text-left" pixelAccent>
            <div className="text-sm space-y-3">
              <FeatureLine icon="pickaxe" text="No hardware required" />
              <FeatureLine icon="coin" text="Rewards from trading fees" />
              <FeatureLine icon="gem" text="5x multiplier for diamond hands" />
              <FeatureLine icon="star" text="Automatic compounding" highlight />
            </div>
          </Card>
        </div>

        {/* Key Points - Mobile Clean Style */}
        <div className="lg:hidden mb-8 grid grid-cols-2 gap-3 max-w-sm mx-auto">
          <FeatureChip icon="pickaxe" text="No hardware" />
          <FeatureChip icon="coin" text="Fee rewards" />
          <FeatureChip icon="gem" text="5x multiplier" />
          <FeatureChip icon="star" text="Auto compound" />
        </div>

        {/* CTA */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-10">
          <ConnectButton size="lg" />
          <a
            href="#how-it-works"
            className="text-sm text-text-secondary hover:text-white transition-colors"
          >
            Learn how it works →
          </a>
        </div>

        {/* Stats (optional) */}
        {stats && !isLoading && (
          <div className="flex items-center justify-center gap-8 text-center">
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
 * Feature line with pixel icon
 * Monochrome design
 */
function FeatureLine({
  icon,
  text,
  highlight = false,
}: {
  icon: 'pickaxe' | 'coin' | 'gem' | 'star';
  text: string;
  highlight?: boolean;
}) {
  return (
    <div className={cn('flex items-center gap-3', highlight && 'text-white glow-white')}>
      <PixelIcon name={icon} size="md" variant={highlight ? 'accent' : 'default'} />
      <span className={highlight ? 'text-white' : 'text-text-primary'}>
        {text}
      </span>
    </div>
  );
}

/**
 * Feature chip for mobile hero
 * Monochrome design
 */
function FeatureChip({ icon, text }: { icon: 'pickaxe' | 'coin' | 'gem' | 'star'; text: string }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-bg-surface rounded-lg border border-border">
      <PixelIcon name={icon} size="sm" variant="default" />
      <span className="text-sm text-text-primary">{text}</span>
    </div>
  );
}

/**
 * Stat display
 * Monochrome design
 */
function StatDisplay({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xl lg:text-2xl font-bold text-white tabular-nums">
        {value}
      </div>
      <div className="text-xs text-text-muted uppercase tracking-wider">{label}</div>
    </div>
  );
}
