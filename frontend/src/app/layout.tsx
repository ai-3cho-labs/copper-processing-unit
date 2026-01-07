import type { Metadata, Viewport } from 'next';
import { Providers } from '@/components/providers/Providers';
import './globals.css';

export const metadata: Metadata = {
  title: '$COPPER - Mine Rewards by Holding',
  description:
    'Earn mining rewards funded by trading fees. Hold tokens, build streaks, get paid.',
  keywords: ['solana', 'memecoin', 'mining', 'crypto', 'rewards', 'defi'],
  authors: [{ name: '$COPPER Team' }],
  openGraph: {
    title: '$COPPER - Mine Rewards by Holding',
    description:
      'Earn mining rewards funded by trading fees. Hold tokens, build streaks, get paid.',
    type: 'website',
    locale: 'en_US',
  },
  twitter: {
    card: 'summary_large_image',
    title: '$COPPER - Mine Rewards by Holding',
    description:
      'Earn mining rewards funded by trading fees. Hold tokens, build streaks, get paid.',
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  themeColor: '#0a0a0a',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
