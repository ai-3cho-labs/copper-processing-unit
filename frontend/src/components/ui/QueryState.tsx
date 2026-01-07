'use client';

import { ReactNode } from 'react';
import { LoadingSpinner } from './LoadingSpinner';
import { ErrorDisplay } from './ErrorDisplay';
import { EmptyState } from './EmptyState';
import { Skeleton, SkeletonCard, SkeletonListItem } from './Skeleton';

export interface QueryStateProps<T> {
  /** Query data */
  data: T | null | undefined;
  /** Is loading */
  isLoading: boolean;
  /** Is error */
  isError: boolean;
  /** Error object */
  error: Error | null | unknown;
  /** Refetch function */
  refetch?: () => void;
  /** Condition to check if data is empty */
  isEmpty?: (data: T) => boolean;
  /** Custom empty state component */
  emptyState?: ReactNode;
  /** Loading variant */
  loadingVariant?: 'spinner' | 'skeleton' | 'skeleton-card' | 'skeleton-list';
  /** Number of skeleton items to show */
  skeletonCount?: number;
  /** Render children with data */
  children: (data: T) => ReactNode;
}

/**
 * Query state handler component
 * Handles loading, error, and empty states for data queries
 */
export function QueryState<T>({
  data,
  isLoading,
  isError,
  error,
  refetch,
  isEmpty,
  emptyState,
  loadingVariant = 'spinner',
  skeletonCount = 3,
  children,
}: QueryStateProps<T>) {
  // Loading state
  if (isLoading) {
    switch (loadingVariant) {
      case 'skeleton':
        return (
          <div className="space-y-3">
            {Array.from({ length: skeletonCount }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" rounded />
            ))}
          </div>
        );
      case 'skeleton-card':
        return (
          <div className="space-y-4">
            {Array.from({ length: skeletonCount }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        );
      case 'skeleton-list':
        return (
          <div className="space-y-1">
            {Array.from({ length: skeletonCount }).map((_, i) => (
              <SkeletonListItem key={i} />
            ))}
          </div>
        );
      default:
        return (
          <div className="flex justify-center py-8">
            <LoadingSpinner size="lg" />
          </div>
        );
    }
  }

  // Error state
  if (isError) {
    return (
      <ErrorDisplay
        error={error}
        onRetry={refetch}
        compact
      />
    );
  }

  // Empty state - data is null/undefined or meets empty condition
  if (!data || (isEmpty && isEmpty(data))) {
    return (
      <>
        {emptyState || (
          <EmptyState title="No data" description="Check back later" />
        )}
      </>
    );
  }

  // Success state - render children with data
  return <>{children(data)}</>;
}

/**
 * Simple conditional rendering based on query state
 */
export function QueryContent<T>({
  data,
  isLoading,
  isError,
  children,
  fallback,
}: {
  data: T | null | undefined;
  isLoading: boolean;
  isError: boolean;
  children: (data: T) => ReactNode;
  fallback?: ReactNode;
}) {
  if (isLoading || isError || !data) {
    return <>{fallback}</>;
  }
  return <>{children(data)}</>;
}
