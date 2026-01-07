'use client';

import { useQuery } from '@tanstack/react-query';
import { getTiers } from '@/lib/api';
import type { TierConfig } from '@/types/api';

/** Query key for tiers */
export const TIERS_QUERY_KEY = ['tiers'] as const;

/**
 * Hook to fetch tier configurations
 * Cached indefinitely since tiers rarely change
 */
export function useTiers() {
  return useQuery<TierConfig[], Error>({
    queryKey: TIERS_QUERY_KEY,
    queryFn: getTiers,
    staleTime: Infinity, // Never stale
    gcTime: Infinity, // Never garbage collected
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
}
