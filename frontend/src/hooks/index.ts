/**
 * Hooks exports
 */

// Wallet hooks
export { useWallet, useIsConnected, useWalletAddress } from './useWallet';

// Media query hooks
export {
  useMediaQuery,
  useIsDesktop,
  useIsMobile,
  usePrefersReducedMotion,
  usePrefersDarkMode,
} from './useMediaQuery';

// Utility hooks
export { useCountdown, useAnimatedNumber } from './useCountdown';

// API hooks
export {
  useGlobalStats,
  useUserStats,
  useUserHistory,
  useLeaderboard,
  usePoolStatus,
  useBuybacks,
  useDistributions,
  useTiers,
} from './api';
