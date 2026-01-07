/**
 * UI Components exports
 * Pixel Art Aesthetic
 */

// Card (new) + backwards compatibility
export { Card, TerminalCard } from './Card';
export type { CardProps, TerminalCardProps } from './Card';

// Text (new) + backwards compatibility
export { Text, Label, TerminalText, TerminalLabel } from './Text';
export type { TextProps, TerminalTextProps } from './Text';

// Pixel Progress (new) + backwards compatibility
export { PixelProgress, ProgressBar, AsciiProgressBar } from './PixelProgress';
export type { PixelProgressProps } from './PixelProgress';

// Pixel Icon (new)
export { PixelIcon, PixelCoin } from './PixelIcon';
export type { PixelIconProps } from './PixelIcon';

// Pixel Toast (new)
export { PixelToast, usePixelToast } from './PixelToast';
export type { PixelToastProps } from './PixelToast';

// Loading
export {
  LoadingSpinner,
  LoadingPage,
  LoadingInline,
} from './LoadingSpinner';
export type { LoadingSpinnerProps } from './LoadingSpinner';

// Skeleton
export {
  Skeleton,
  SkeletonText,
  SkeletonCard,
  SkeletonListItem,
  SkeletonStats,
} from './Skeleton';
export type { SkeletonProps } from './Skeleton';

// Button
export { Button, IconButton } from './Button';
export type { ButtonProps } from './Button';

// Badge
export { Badge, TierBadge, RankBadge, StatusBadge } from './Badge';
export type { BadgeProps } from './Badge';

// Error
export { ErrorDisplay, ErrorInline, ErrorFallback } from './ErrorDisplay';
export type { ErrorDisplayProps } from './ErrorDisplay';

// Empty
export {
  EmptyState,
  NoDataEmpty,
  NoResultsEmpty,
  NoHistoryEmpty,
  NoBuybacksEmpty,
  ConnectWalletEmpty,
} from './EmptyState';
export type { EmptyStateProps } from './EmptyState';

// Query State
export { QueryState, QueryContent } from './QueryState';
export type { QueryStateProps } from './QueryState';
