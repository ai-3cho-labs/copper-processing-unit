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

// Gesture hooks
export { useSwipeGesture, type SwipeGestureOptions, type SwipeGestureReturn } from './useSwipeGesture';

// API hooks
export {
  useGlobalStats,
  useUserStats,
  useUserHistory,
  useLeaderboard,
  usePoolStatus,
  useDistributions,
  useTiers,
} from './api';

// WebSocket hooks
export { useWebSocket, type ConnectionStatus, type UseWebSocketReturn } from './useWebSocket';
