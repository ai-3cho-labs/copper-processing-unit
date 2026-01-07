'use client';

import Link from 'next/link';
import { cn } from '@/lib/cn';
import { COPPER_TOKEN_MINT, getTokenUrl } from '@/lib/constants';

const FOOTER_LINKS = [
  {
    title: 'Product',
    links: [
      { label: 'Dashboard', href: '/dashboard' },
      { label: 'Leaderboard', href: '/leaderboard' },
      { label: 'Documentation', href: '/docs' },
    ],
  },
  {
    title: 'Community',
    links: [
      { label: 'Twitter', href: 'https://twitter.com', external: true },
      { label: 'Telegram', href: 'https://t.me', external: true },
      { label: 'Discord', href: 'https://discord.gg', external: true },
    ],
  },
  {
    title: 'Resources',
    links: [
      { label: 'Token', href: getTokenUrl(COPPER_TOKEN_MINT), external: true },
      { label: 'GitHub', href: 'https://github.com', external: true },
    ],
  },
] as const;

/**
 * Desktop footer
 */
export function Footer() {
  return (
    <footer className="hidden lg:block border-t border-terminal-border bg-terminal-bg mt-auto">
      <div className="container mx-auto px-6 py-12">
        <div className="grid grid-cols-4 gap-8">
          {/* Brand */}
          <div>
            <Link href="/" className="inline-block mb-4">
              <span className="text-xl font-bold text-copper">$COPPER</span>
            </Link>
            <p className="text-sm text-zinc-500 font-mono">
              Mine rewards by holding.
              <br />
              Build your streak.
              <br />
              Earn airdrops.
            </p>
          </div>

          {/* Link columns */}
          {FOOTER_LINKS.map((section) => (
            <div key={section.title}>
              <h3 className="text-sm font-semibold text-zinc-300 mb-4 font-mono">
                {section.title}
              </h3>
              <ul className="space-y-2">
                {section.links.map((link) => (
                  <li key={link.label}>
                    {'external' in link && link.external ? (
                      <a
                        href={link.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-zinc-500 hover:text-copper transition-colors font-mono"
                      >
                        {link.label}
                        <span className="ml-1 text-xs">↗</span>
                      </a>
                    ) : (
                      <Link
                        href={link.href}
                        className="text-sm text-zinc-500 hover:text-copper transition-colors font-mono"
                      >
                        {link.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="mt-12 pt-6 border-t border-terminal-border flex items-center justify-between">
          <p className="text-xs text-zinc-600 font-mono">
            &copy; {new Date().getFullYear()} $COPPER. All rights reserved.
          </p>
          <p className="text-xs text-zinc-600 font-mono">
            Built on Solana
          </p>
        </div>
      </div>
    </footer>
  );
}

/**
 * Simple footer (for minimal pages)
 */
export function SimpleFooter({ className }: { className?: string }) {
  return (
    <footer
      className={cn(
        'hidden lg:block py-6 text-center text-xs text-zinc-600 font-mono',
        className
      )}
    >
      <p>
        &copy; {new Date().getFullYear()} $COPPER · Built on Solana
      </p>
    </footer>
  );
}
