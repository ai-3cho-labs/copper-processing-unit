'use client';

import { cn } from '@/lib/cn';

export interface SkeletonProps {
  /** Additional class names */
  className?: string;
  /** Width (can use Tailwind classes or custom) */
  width?: string;
  /** Height (can use Tailwind classes or custom) */
  height?: string;
  /** Make skeleton rounded */
  rounded?: boolean;
  /** Make skeleton circular */
  circle?: boolean;
}

/**
 * Skeleton loading placeholder with shimmer effect
 */
export function Skeleton({
  className,
  width,
  height,
  rounded = false,
  circle = false,
}: SkeletonProps) {
  return (
    <div
      className={cn(
        'relative overflow-hidden bg-white/[0.06]',
        // Shimmer overlay
        'before:absolute before:inset-0',
        'before:bg-gradient-to-r before:from-transparent before:via-white/[0.08] before:to-transparent',
        'before:animate-shimmer',
        rounded && 'rounded-md',
        circle && 'rounded-full',
        !rounded && !circle && 'rounded',
        className
      )}
      style={{
        width: width,
        height: height,
      }}
    />
  );
}

/**
 * Skeleton for text lines
 */
export function SkeletonText({
  lines = 1,
  className,
}: {
  lines?: number;
  className?: string;
}) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn(
            'h-4',
            // Last line is shorter
            i === lines - 1 && lines > 1 && 'w-3/4'
          )}
          rounded
        />
      ))}
    </div>
  );
}

/**
 * Skeleton for a card
 */
export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'rounded-lg border border-terminal-border bg-terminal-card p-4',
        className
      )}
    >
      <Skeleton className="h-5 w-1/3 mb-4" rounded />
      <div className="space-y-3">
        <Skeleton className="h-4 w-full" rounded />
        <Skeleton className="h-4 w-5/6" rounded />
        <Skeleton className="h-4 w-4/6" rounded />
      </div>
    </div>
  );
}

/**
 * Skeleton for a list item
 */
export function SkeletonListItem({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center gap-3 py-2', className)}>
      <Skeleton className="h-8 w-8" circle />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-1/3" rounded />
        <Skeleton className="h-3 w-1/2" rounded />
      </div>
      <Skeleton className="h-4 w-16" rounded />
    </div>
  );
}

/**
 * Skeleton for stats display
 */
export function SkeletonStats({ className }: { className?: string }) {
  return (
    <div className={cn('space-y-1', className)}>
      <Skeleton className="h-3 w-16" rounded />
      <Skeleton className="h-6 w-24" rounded />
    </div>
  );
}
