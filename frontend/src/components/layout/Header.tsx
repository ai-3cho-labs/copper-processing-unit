'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/cn';
import { ConnectButton } from '@/components/wallet/ConnectButton';

const NAV_LINKS = [
  { href: '/', label: 'Home' },
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/leaderboard', label: 'Leaderboard' },
] as const;

/**
 * Desktop header with navigation
 */
export function Header() {
  const pathname = usePathname();

  return (
    <header className="hidden lg:block border-b border-terminal-border bg-terminal-bg/80 backdrop-blur-sm sticky top-0 z-40">
      <div className="container mx-auto px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link
            href="/"
            className="flex items-center gap-2 group"
          >
            <span className="text-2xl font-bold text-copper glow-copper group-hover:text-copper-glow transition-colors">
              $COPPER
            </span>
            <span className="text-xs text-terminal-green font-mono">
              [MINING]
            </span>
          </Link>

          {/* Navigation */}
          <nav className="flex items-center gap-1">
            {NAV_LINKS.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    'px-4 py-2 text-sm font-mono rounded transition-colors',
                    isActive
                      ? 'text-copper bg-copper/10'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-terminal-border/50'
                  )}
                >
                  {isActive && <span className="text-copper-dim mr-1">&gt;</span>}
                  {link.label}
                </Link>
              );
            })}
          </nav>

          {/* Connect Button */}
          <ConnectButton size="sm" />
        </div>
      </div>
    </header>
  );
}

/**
 * Minimal header (for landing page)
 */
export function MinimalHeader() {
  return (
    <header className="hidden lg:block absolute top-0 left-0 right-0 z-40">
      <div className="container mx-auto px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl font-bold text-copper glow-copper">
              $COPPER
            </span>
          </Link>

          {/* Connect Button */}
          <ConnectButton size="sm" />
        </div>
      </div>
    </header>
  );
}
