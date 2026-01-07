'use client';

import { FC, ReactNode, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DEFAULT_STALE_TIME } from '@/lib/constants';

interface QueryProviderProps {
  children: ReactNode;
}

/**
 * TanStack Query Provider
 * Provides query client for data fetching
 */
export const QueryProvider: FC<QueryProviderProps> = ({ children }) => {
  // Create query client with default options
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Default stale time (30 seconds)
            staleTime: DEFAULT_STALE_TIME,
            // Retry failed requests up to 3 times
            retry: 3,
            // Exponential backoff for retries
            retryDelay: (attemptIndex) =>
              Math.min(1000 * 2 ** attemptIndex, 30000),
            // Refetch on window focus (good for dashboards)
            refetchOnWindowFocus: true,
            // Don't refetch on mount if data is fresh
            refetchOnMount: true,
            // Keep previous data while fetching new data
            placeholderData: (previousData: unknown) => previousData,
          },
          mutations: {
            // Retry mutations once on failure
            retry: 1,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};
