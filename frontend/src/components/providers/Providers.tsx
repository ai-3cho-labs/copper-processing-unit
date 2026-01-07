'use client';

import { FC, ReactNode } from 'react';
import { WalletProvider } from './WalletProvider';
import { QueryProvider } from './QueryProvider';

interface ProvidersProps {
  children: ReactNode;
}

/**
 * Combined Providers
 * Wraps the application with all necessary context providers
 *
 * Provider order (outer to inner):
 * 1. QueryProvider - Data fetching and caching
 * 2. WalletProvider - Solana wallet connection
 */
export const Providers: FC<ProvidersProps> = ({ children }) => {
  return (
    <QueryProvider>
      <WalletProvider>{children}</WalletProvider>
    </QueryProvider>
  );
};
