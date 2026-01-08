'use client';

import { cn } from '@/lib/cn';
import { Card, PixelIcon } from '@/components/ui';

export interface HowItWorksProps {
  /** Additional class names */
  className?: string;
}

const STEPS = [
  {
    icon: 'chest' as const,
    title: 'Hold $CPU',
    description: 'Buy tokens and hold them in your wallet. Your average balance over time determines your mining power.',
  },
  {
    icon: 'lightning' as const,
    title: 'Build Your Streak',
    description: 'The longer you hold without selling, the higher your tier. Diamond Hands (30+ days) earn 5x rewards.',
  },
  {
    icon: 'coin' as const,
    title: 'Collect Rewards',
    description: 'Trading fees fill the pool. When it hits $250 or 24 hours pass, rewards drop to all miners automatically.',
  },
];

/**
 * HowItWorks - 3-step explanation of the system
 */
export function HowItWorks({ className }: HowItWorksProps) {
  return (
    <section id="how-it-works" className={cn('py-10 lg:py-12', className)}>
      <div className="max-w-5xl mx-auto px-4">
        {/* Section Header */}
        <div className="text-center mb-8">
          <h2 className="text-heading-1 font-bold text-text-primary mb-2 tracking-tight">
            HOW THE MINE WORKS
          </h2>
          <p className="text-body-sm text-text-secondary max-w-md mx-auto">
            Passive mining rewards, zero hardware. Your tokens work 24/7.
          </p>
        </div>

        {/* Steps Grid */}
        <div className="grid md:grid-cols-3 gap-3 sm:gap-4 lg:gap-6">
          {STEPS.map((step) => (
            <StepCard key={step.title} step={step} />
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
    <Card className="p-3 sm:p-4">
      {/* Icon */}
      <div className="mb-3">
        <PixelIcon name={step.icon} size="lg" variant="default" />
      </div>

      {/* Title */}
      <h3 className="text-heading-3 font-semibold text-text-primary mb-2">
        {step.title}
      </h3>

      {/* Description */}
      <p className="text-body-sm text-text-secondary">{step.description}</p>
    </Card>
  );
}
