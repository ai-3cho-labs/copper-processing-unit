'use client';

import { useState, useEffect } from 'react';
import { DESKTOP_BREAKPOINT } from '@/lib/constants';

/**
 * Hook to check if a media query matches
 * @param query - CSS media query string
 * @returns boolean indicating if query matches
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    // Check if window is available (client-side)
    if (typeof window === 'undefined') return;

    const media = window.matchMedia(query);

    // Set initial value
    setMatches(media.matches);

    // Create listener
    const listener = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };

    // Add listener
    media.addEventListener('change', listener);

    // Cleanup
    return () => {
      media.removeEventListener('change', listener);
    };
  }, [query]);

  return matches;
}

/**
 * Hook to check if viewport is desktop size (lg and above)
 * @returns boolean indicating if viewport is >= 1024px
 */
export function useIsDesktop(): boolean {
  return useMediaQuery(`(min-width: ${DESKTOP_BREAKPOINT}px)`);
}

/**
 * Hook to check if viewport is mobile size (below lg)
 * @returns boolean indicating if viewport is < 1024px
 */
export function useIsMobile(): boolean {
  return useMediaQuery(`(max-width: ${DESKTOP_BREAKPOINT - 1}px)`);
}

/**
 * Hook to check if user prefers reduced motion
 * @returns boolean indicating if user prefers reduced motion
 */
export function usePrefersReducedMotion(): boolean {
  return useMediaQuery('(prefers-reduced-motion: reduce)');
}

/**
 * Hook to check if user prefers dark mode
 * @returns boolean indicating if user prefers dark mode
 */
export function usePrefersDarkMode(): boolean {
  return useMediaQuery('(prefers-color-scheme: dark)');
}
