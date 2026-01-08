'use client';

import { cn } from '@/lib/cn';
import { formatMultiplier, formatDuration } from '@/lib/utils';
import { TIER_CONFIG, type TierId } from '@/types/models';
import { Card, PixelProgress } from '@/components/ui';

export interface TierExplainerProps {
  /** Currently highlighted tier (optional) */
  highlightTier?: TierId;
  /** Additional class names */
  className?: string;
}

/**
 * TierExplainer - Visual tier progression table
 */
export function TierExplainer({ highlightTier, className }: TierExplainerProps) {
  const tiers = Object.entries(TIER_CONFIG) as [string, (typeof TIER_CONFIG)[TierId]][];

  return (
    <section className={cn('py-12 lg:py-20', className)}>
      <div className="max-w-4xl mx-auto px-4">
        {/* Section Header */}
        <div className="text-center mb-10">
          <h2 className="text-2xl lg:text-3xl font-bold text-text-primary mb-4 tracking-tight">
            TIER PROGRESSION
          </h2>
          <p className="text-body text-text-secondary max-w-lg mx-auto">
            Hold longer, earn more. Each tier unlocks higher reward multipliers.
            Selling drops you one tier, so diamond hands wins.
          </p>
        </div>

        {/* Desktop: Clean Table */}
        <div className="hidden lg:block">
          <Card noPadding>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-text-muted">
                  <th className="text-left px-4 py-3">TIER</th>
                  <th className="text-left px-4 py-3">NAME</th>
                  <th className="text-right px-4 py-3">MIN HOLD</th>
                  <th className="text-right px-4 py-3">MULTIPLIER</th>
                  <th className="text-right px-4 py-3">BONUS</th>
                </tr>
              </thead>
              <tbody>
                {tiers.map(([id, config], index) => {
                  const tierId = parseInt(id) as TierId;
                  const isHighlighted = tierId === highlightTier;
                  const prevTier = index > 0 ? tiers[index - 1] : null;
                  const prevMultiplier = prevTier ? prevTier[1].multiplier : 1;
                  const bonusVsPrev = (
                    ((config.multiplier - prevMultiplier) / prevMultiplier) *
                    100
                  ).toFixed(0);

                  return (
                    <tr
                      key={id}
                      className={cn(
                        'border-b border-border/50 transition-colors',
                        isHighlighted && 'bg-white/10'
                      )}
                    >
                      <td className="px-4 py-3">
                        <span className="font-mono text-gray-400">[{config.name.toUpperCase().slice(0, 3)}]</span>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={cn(
                            isHighlighted ? 'text-white' : 'text-text-primary'
                          )}
                        >
                          {config.name}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-text-secondary">
                        {config.minHours === 0
                          ? 'Instant'
                          : formatDuration(config.minHours)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span
                          className={cn(
                            'font-semibold',
                            isHighlighted
                              ? 'text-white glow-white'
                              : 'text-gray-200'
                          )}
                        >
                          {formatMultiplier(config.multiplier)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-text-muted">
                        {index > 0 ? `+${bonusVsPrev}%` : '-'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        </div>

        {/* Mobile: Card Stack */}
        <div className="lg:hidden space-y-2 sm:space-y-3">
          {tiers.map(([id, config]) => {
            const tierId = parseInt(id) as TierId;
            const isHighlighted = tierId === highlightTier;
            const progressToMax = (config.multiplier / 5) * 100;

            return (
              <div
                key={id}
                className={cn(
                  'p-3 sm:p-4 rounded-lg border transition-colors',
                  isHighlighted
                    ? 'bg-white/10 border-white/30'
                    : 'bg-bg-card border-border'
                )}
              >
                <div className="flex items-center justify-between mb-1.5 sm:mb-2">
                  <div className="flex items-center gap-2 sm:gap-3">
                    <span className="font-mono text-gray-400">[{config.name.toUpperCase().slice(0, 3)}]</span>
                    <div>
                      <div className="font-medium text-text-primary">
                        {config.name}
                      </div>
                      <div className="text-xs text-text-muted">
                        {config.minHours === 0
                          ? 'Start here'
                          : `After ${formatDuration(config.minHours)}`}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div
                      className={cn(
                        'text-lg font-bold',
                        isHighlighted ? 'text-white glow-white' : 'text-gray-200'
                      )}
                    >
                      {formatMultiplier(config.multiplier)}
                    </div>
                    <div className="text-xs text-text-muted">multiplier</div>
                  </div>
                </div>
                <PixelProgress
                  value={progressToMax}
                  variant={isHighlighted ? 'gradient' : 'default'}
                  size="sm"
                  segments={5}
                />
              </div>
            );
          })}
        </div>

        {/* Bottom Note */}
        <div className="mt-8 text-center">
          <p className="text-body-sm text-text-muted">
            Selling resets your streak by one tier level.{' '}
            <span className="text-white font-semibold glow-white">Diamond Hands</span>{' '}
            who hold 30+ days earn the maximum 5x multiplier.
          </p>
        </div>
      </div>
    </section>
  );
}
