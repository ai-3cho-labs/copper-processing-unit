'use client';

import { useCallback, useRef, useState } from 'react';
import { usePrefersReducedMotion } from './useMediaQuery';

export interface SwipeGestureOptions {
  /** Callback when swiping down past threshold */
  onSwipeDown?: () => void;
  /** Callback when swiping left past threshold */
  onSwipeLeft?: () => void;
  /** Callback when swiping right past threshold */
  onSwipeRight?: () => void;
  /** Minimum distance to trigger swipe (default: 80px) */
  threshold?: number;
  /** Velocity to instantly trigger swipe (default: 0.5 px/ms) */
  velocityThreshold?: number;
  /** Resistance factor when dragging opposite direction (default: 0.3) */
  resistance?: number;
  /** Whether to enable the gesture (default: true) */
  enabled?: boolean;
}

export interface SwipeGestureReturn {
  /** Touch event handlers to spread on the element */
  handlers: {
    onTouchStart: (e: React.TouchEvent) => void;
    onTouchMove: (e: React.TouchEvent) => void;
    onTouchEnd: (e: React.TouchEvent) => void;
  };
  /** Current drag offset in pixels */
  dragOffset: { x: number; y: number };
  /** Whether user is currently dragging */
  isDragging: boolean;
}

/**
 * Hook for handling swipe gestures on touch devices.
 * Supports swipe-down-to-close and horizontal tab swiping.
 */
export function useSwipeGesture(options: SwipeGestureOptions = {}): SwipeGestureReturn {
  const {
    onSwipeDown,
    onSwipeLeft,
    onSwipeRight,
    threshold = 80,
    velocityThreshold = 0.5,
    resistance = 0.3,
    enabled = true,
  } = options;

  const prefersReducedMotion = usePrefersReducedMotion();

  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  // Refs to track touch state
  const touchStartRef = useRef<{ x: number; y: number; time: number } | null>(null);
  const isScrollingRef = useRef<'vertical' | 'horizontal' | null>(null);

  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      if (!enabled) return;

      const touch = e.touches[0];
      if (!touch) return;

      touchStartRef.current = {
        x: touch.clientX,
        y: touch.clientY,
        time: Date.now(),
      };
      isScrollingRef.current = null;
      setIsDragging(true);
    },
    [enabled]
  );

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      if (!enabled || !touchStartRef.current) return;

      const touch = e.touches[0];
      if (!touch) return;

      const deltaX = touch.clientX - touchStartRef.current.x;
      const deltaY = touch.clientY - touchStartRef.current.y;

      // Determine scroll direction on first significant movement
      if (isScrollingRef.current === null && (Math.abs(deltaX) > 10 || Math.abs(deltaY) > 10)) {
        isScrollingRef.current = Math.abs(deltaX) > Math.abs(deltaY) ? 'horizontal' : 'vertical';
      }

      // Calculate offset with resistance for negative values
      let offsetY = 0;
      let offsetX = 0;

      if (isScrollingRef.current === 'vertical' && onSwipeDown) {
        // Only allow dragging down (positive Y)
        offsetY = deltaY > 0 ? deltaY : deltaY * resistance;
      }

      if (isScrollingRef.current === 'horizontal' && (onSwipeLeft || onSwipeRight)) {
        offsetX = deltaX;
      }

      setDragOffset({ x: offsetX, y: offsetY });
    },
    [enabled, onSwipeDown, onSwipeLeft, onSwipeRight, resistance]
  );

  const handleTouchEnd = useCallback(
    (e: React.TouchEvent) => {
      if (!enabled || !touchStartRef.current) {
        setIsDragging(false);
        setDragOffset({ x: 0, y: 0 });
        return;
      }

      const touch = e.changedTouches[0];
      if (!touch) {
        setIsDragging(false);
        setDragOffset({ x: 0, y: 0 });
        return;
      }

      const deltaX = touch.clientX - touchStartRef.current.x;
      const deltaY = touch.clientY - touchStartRef.current.y;
      const elapsed = Date.now() - touchStartRef.current.time;

      // Calculate velocity (px/ms)
      const velocityX = Math.abs(deltaX) / elapsed;
      const velocityY = Math.abs(deltaY) / elapsed;

      // Check for swipe down
      if (
        onSwipeDown &&
        isScrollingRef.current === 'vertical' &&
        deltaY > 0 &&
        (deltaY > threshold || velocityY > velocityThreshold)
      ) {
        onSwipeDown();
      }

      // Check for swipe left (negative X)
      if (
        onSwipeLeft &&
        isScrollingRef.current === 'horizontal' &&
        deltaX < 0 &&
        (Math.abs(deltaX) > threshold || velocityX > velocityThreshold)
      ) {
        if (!prefersReducedMotion) {
          onSwipeLeft();
        }
      }

      // Check for swipe right (positive X)
      if (
        onSwipeRight &&
        isScrollingRef.current === 'horizontal' &&
        deltaX > 0 &&
        (Math.abs(deltaX) > threshold || velocityX > velocityThreshold)
      ) {
        if (!prefersReducedMotion) {
          onSwipeRight();
        }
      }

      // Reset state
      touchStartRef.current = null;
      isScrollingRef.current = null;
      setIsDragging(false);
      setDragOffset({ x: 0, y: 0 });
    },
    [enabled, onSwipeDown, onSwipeLeft, onSwipeRight, threshold, velocityThreshold, prefersReducedMotion]
  );

  return {
    handlers: {
      onTouchStart: handleTouchStart,
      onTouchMove: handleTouchMove,
      onTouchEnd: handleTouchEnd,
    },
    dragOffset,
    isDragging,
  };
}
