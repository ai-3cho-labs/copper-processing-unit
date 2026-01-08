'use client';

import { PageContainer } from '@/components/layout/PageContainer';
import { Hero, LiveStatsBar, HowItWorks, WebGLBackground } from '@/components/landing';
import { useGlobalStats, usePoolStatus } from '@/hooks/api';

export default function HomePage() {
  const globalStats = useGlobalStats();
  const poolStatus = usePoolStatus();

  return (
    <PageContainer>
      {/* WebGL Background (landing page only) */}
      <WebGLBackground />

      {/* Hero Section */}
      <Hero
        stats={
          globalStats.data
            ? {
                totalHolders: globalStats.data.total_holders,
                totalDistributed: globalStats.data.total_distributed,
              }
            : undefined
        }
        isLoading={globalStats.isLoading}
      />

      {/* Live Stats Ticker */}
      <LiveStatsBar
        holders={globalStats.data?.total_holders ?? 0}
        volume24h={globalStats.data?.total_volume_24h ?? 0}
        poolValueUsd={poolStatus.data?.valueUsd ?? 0}
        hoursUntilNext={poolStatus.data?.hoursUntilTrigger ?? null}
        isLoading={globalStats.isLoading || poolStatus.isLoading}
      />

      {/* How It Works */}
      <HowItWorks />
    </PageContainer>
  );
}
