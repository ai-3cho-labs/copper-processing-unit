'use client';

import { cn } from '@/lib/cn';
import { Card, PixelIcon } from '@/components/ui';

export interface HowItWorksProps {
  /** Additional class names */
  className?: string;
}

const STEPS = [
  {
    number: '01',
    icon: 'chest' as const,
    title: 'Hold $CPU',
    description: 'Buy and hold tokens. Your TWAB determines mining power.',
  },
  {
    number: '02',
    icon: 'lightning' as const,
    title: 'Earn Hash Power',
    description: 'Hold without selling. Longer streaks unlock up to 5x multiplier.',
  },
  {
    number: '03',
    icon: 'coin' as const,
    title: 'Receive Rewards',
    description: 'Trading fees fill the pool. Rewards paid when pool hits $250 or 24h.',
  },
];

/**
 * HowItWorks - 3-step explanation of the system
 */
export function HowItWorks({ className }: HowItWorksProps) {
  return (
    <section id="how-it-works" className={cn('py-8 lg:py-12', className)}>
      <div className="max-w-5xl mx-auto px-4">
        {/* Section Header */}
        <div className="text-center mb-8">
          <h2 className="text-xl lg:text-2xl font-bold text-text-primary mb-2">
            HOW IT WORKS
          </h2>
          <p className="text-sm text-text-secondary max-w-md mx-auto">
            Mining rewards without hardware. Your tokens work for you 24/7.
          </p>
        </div>

        {/* Steps Grid */}
        <div className="grid md:grid-cols-3 gap-4 lg:gap-6">
          {STEPS.map((step) => (
            <StepCard key={step.number} step={step} />
          ))}
        </div>

        {/* Connection lines - Desktop only */}
        <div className="hidden lg:flex justify-center mt-6">
          <div className="flex items-center gap-3 text-gray-500 text-xs font-mono">
            <span>HOLD</span>
            <span className="text-white">→</span>
            <span>EARN</span>
            <span className="text-white">→</span>
            <span>MINE</span>
            <span className="text-white">→</span>
            <span className="text-white glow-white">REPEAT</span>
          </div>
        </div>
      </div>
    </section>
  );
}

/**
 * Individual step card
 * Compact monochrome design
 */
function StepCard({
  step,
}: {
  step: (typeof STEPS)[0];
}) {
  return (
    <Card className="relative p-4">
      {/* Step number badge */}
      <div
        className={cn(
          'absolute -top-2 left-3',
          'px-1.5 py-0.5 text-xs font-bold rounded',
          'bg-white text-bg-dark'
        )}
      >
        {step.number}
      </div>

      <div className="pt-2">
        {/* Icon */}
        <div className="mb-2">
          <PixelIcon name={step.icon} size="lg" variant="default" />
        </div>

        {/* Title */}
        <h3 className="text-base font-semibold text-text-primary mb-1">
          {step.title}
        </h3>

        {/* Description */}
        <p className="text-xs text-text-secondary">{step.description}</p>
      </div>
    </Card>
  );
}
