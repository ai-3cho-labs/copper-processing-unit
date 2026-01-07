'use client';

import { cn } from '@/lib/cn';
import { Header } from './Header';
import { Footer } from './Footer';
import { MobileNav } from './MobileNav';

export interface PageContainerProps {
  /** Page content */
  children: React.ReactNode;
  /** Show header */
  showHeader?: boolean;
  /** Show footer */
  showFooter?: boolean;
  /** Show mobile nav */
  showMobileNav?: boolean;
  /** Max width constraint */
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
  /** Additional class names for content */
  className?: string;
  /** Full height mode */
  fullHeight?: boolean;
}

/**
 * Page container component
 * Provides consistent layout with header, footer, and navigation
 */
export function PageContainer({
  children,
  showHeader = true,
  showFooter = true,
  showMobileNav = true,
  maxWidth = 'xl',
  className,
  fullHeight = false,
}: PageContainerProps) {
  const maxWidthClasses = {
    sm: 'max-w-screen-sm',
    md: 'max-w-screen-md',
    lg: 'max-w-screen-lg',
    xl: 'max-w-screen-xl',
    '2xl': 'max-w-screen-2xl',
    full: 'max-w-full',
  };

  return (
    <div
      className={cn(
        'min-h-screen flex flex-col',
        // Desktop: Terminal background
        'lg:bg-terminal-gradient',
        // Mobile: Clean gradient
        'bg-mobile-gradient'
      )}
    >
      {/* Desktop Header */}
      {showHeader && <Header />}

      {/* Main Content */}
      <main
        className={cn(
          'flex-1 relative z-10',
          // Desktop: Container with padding
          'lg:container lg:mx-auto lg:px-6 lg:py-8',
          // Mobile: Full width with bottom padding for nav
          'px-4 py-4',
          showMobileNav && 'pb-20 lg:pb-8',
          // Max width
          maxWidthClasses[maxWidth],
          // Full height for centered content
          fullHeight && 'flex flex-col',
          className
        )}
      >
        {children}
      </main>

      {/* Desktop Footer */}
      {showFooter && <Footer />}

      {/* Mobile Bottom Navigation */}
      {showMobileNav && <MobileNav />}
    </div>
  );
}

/**
 * Simple page wrapper without navigation
 */
export function SimplePage({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'min-h-screen bg-terminal-gradient lg:bg-terminal-gradient bg-mobile-gradient',
        className
      )}
    >
      {children}
    </div>
  );
}

/**
 * Centered content wrapper
 */
export function CenteredContent({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'flex-1 flex items-center justify-center p-4',
        className
      )}
    >
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
}
