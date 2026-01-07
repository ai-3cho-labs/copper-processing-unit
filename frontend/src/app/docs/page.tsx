'use client';

import { PageContainer } from '@/components/layout';
import { TerminalCard } from '@/components/ui';
import { TierExplainer } from '@/components/landing';
import { cn } from '@/lib/cn';

export default function DocsPage() {
  return (
    <PageContainer>
      <div className="space-y-8 max-w-4xl mx-auto">
        {/* Header */}
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-zinc-100 lg:font-mono">
            <span className="hidden lg:inline text-copper-dim">&gt; </span>
            DOCUMENTATION
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Everything you need to know about $COPPER mining
          </p>
        </div>

        {/* Table of Contents */}
        <TerminalCard title="CONTENTS">
          <nav className="space-y-2 text-sm">
            <TOCLink href="#overview" number="01">
              Overview
            </TOCLink>
            <TOCLink href="#how-it-works" number="02">
              How It Works
            </TOCLink>
            <TOCLink href="#twab" number="03">
              TWAB Calculation
            </TOCLink>
            <TOCLink href="#tiers" number="04">
              Tier System
            </TOCLink>
            <TOCLink href="#distributions" number="05">
              Distributions
            </TOCLink>
            <TOCLink href="#faq" number="06">
              FAQ
            </TOCLink>
          </nav>
        </TerminalCard>

        {/* Overview */}
        <Section id="overview" title="01. OVERVIEW">
          <p>
            $COPPER is a Solana memecoin that simulates crypto mining through holding.
            Instead of running hardware, you mine rewards by simply holding tokens
            in your wallet.
          </p>
          <p>
            Trading volume generates creator fees on Pump.fun, which are used to
            buy back $COPPER tokens and airdrop them to holders based on their
            &quot;Hash Power&quot;.
          </p>
          <Highlight>
            Hash Power = TWAB × Streak Multiplier
          </Highlight>
        </Section>

        {/* How It Works */}
        <Section id="how-it-works" title="02. HOW IT WORKS">
          <ol className="space-y-4 list-decimal list-inside">
            <li>
              <strong className="text-zinc-200">Buy & Hold</strong> - Purchase $COPPER
              and hold it in your wallet. No staking required.
            </li>
            <li>
              <strong className="text-zinc-200">Build Your Streak</strong> - Every hour
              you hold without selling increases your streak and tier level.
            </li>
            <li>
              <strong className="text-zinc-200">Earn Hash Power</strong> - Your Time-Weighted
              Average Balance (TWAB) multiplied by your tier bonus equals your mining power.
            </li>
            <li>
              <strong className="text-zinc-200">Receive Distributions</strong> - When
              the reward pool hits $250 or 24 hours pass, rewards are distributed
              proportionally based on Hash Power.
            </li>
          </ol>
        </Section>

        {/* TWAB */}
        <Section id="twab" title="03. TWAB CALCULATION">
          <p>
            TWAB (Time-Weighted Average Balance) measures your average token holding
            over a period of time. It prevents gaming the system by buying right
            before distributions.
          </p>
          <CodeBlock>
            {`TWAB = Σ(balance × time_held) / total_time

Example:
- Hold 1,000 tokens for 12 hours
- Hold 2,000 tokens for 12 hours
- TWAB = (1000×12 + 2000×12) / 24 = 1,500`}
          </CodeBlock>
          <p className="text-sm text-zinc-500">
            Snapshots are taken randomly 3-6 times per day to calculate TWAB fairly.
          </p>
        </Section>

        {/* Tiers */}
        <Section id="tiers" title="04. TIER SYSTEM">
          <p>
            Hold without selling to climb the tier ladder. Each tier provides a
            higher reward multiplier:
          </p>
          <TierExplainer className="py-0" />
          <div className="mt-4 p-4 bg-terminal-amber/10 border border-terminal-amber/30 rounded">
            <p className="text-sm text-terminal-amber">
              <strong>Warning:</strong> Selling tokens drops you down by one tier
              and resets your streak to that tier&apos;s minimum. Transfers to other
              wallets don&apos;t count as sells.
            </p>
          </div>
        </Section>

        {/* Distributions */}
        <Section id="distributions" title="05. DISTRIBUTIONS">
          <p>Distributions are triggered when either condition is met:</p>
          <ul className="space-y-2 list-disc list-inside">
            <li>
              <strong className="text-terminal-green">Threshold:</strong> Pool
              value reaches $250 USD
            </li>
            <li>
              <strong className="text-terminal-amber">Time:</strong> 24 hours
              pass since the last distribution
            </li>
          </ul>
          <CodeBlock>
            {`Your Reward = (Your Hash Power / Total Hash Power) × Pool Amount

Example:
- Pool: 100,000 $COPPER
- Your HP: 5,000
- Total HP: 100,000
- Your Reward: (5,000 / 100,000) × 100,000 = 5,000 $COPPER`}
          </CodeBlock>
          <p>
            Rewards are automatically airdropped to your wallet and compound into
            your balance for future calculations.
          </p>
        </Section>

        {/* FAQ */}
        <Section id="faq" title="06. FAQ">
          <div className="space-y-6">
            <FAQ question="Do I need to stake my tokens?">
              No! Just hold them in your wallet. There&apos;s no staking contract
              or lock-up period.
            </FAQ>
            <FAQ question="What happens if I sell some tokens?">
              Selling triggers a tier drop. You&apos;ll go down one tier and your
              streak resets to that tier&apos;s minimum hours. Your TWAB will also
              adjust based on your new balance.
            </FAQ>
            <FAQ question="Are transfers counted as sells?">
              No. Only DEX swaps where you sell $COPPER for SOL or USDC are
              detected as sells. Wallet-to-wallet transfers are ignored.
            </FAQ>
            <FAQ question="How often are snapshots taken?">
              Randomly 3-6 times per day with a 40% chance each hour. This prevents
              predictable timing manipulation.
            </FAQ>
            <FAQ question="Which wallets are excluded?">
              Creator wallets, liquidity pool addresses, CEX deposit addresses,
              and system wallets are excluded from rewards.
            </FAQ>
            <FAQ question="Where do the rewards come from?">
              80% of Pump.fun creator fees are used for buybacks. The purchased
              tokens go into the distribution pool. 20% goes to team operations.
            </FAQ>
          </div>
        </Section>
      </div>
    </PageContainer>
  );
}

function TOCLink({
  href,
  number,
  children,
}: {
  href: string;
  number: string;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      className={cn(
        'flex items-center gap-3 py-1.5 px-2 -mx-2 rounded',
        'hover:bg-zinc-800/50 transition-colors',
        'text-zinc-300 hover:text-copper'
      )}
    >
      <span className="text-copper-dim font-mono text-xs">{number}</span>
      <span>{children}</span>
    </a>
  );
}

function Section({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-24">
      <TerminalCard title={title}>
        <div className="space-y-4 text-zinc-400">{children}</div>
      </TerminalCard>
    </section>
  );
}

function Highlight({ children }: { children: React.ReactNode }) {
  return (
    <div className="p-4 bg-copper/10 border border-copper/30 rounded font-mono text-copper text-center">
      {children}
    </div>
  );
}

function CodeBlock({ children }: { children: string }) {
  return (
    <pre className="p-4 bg-terminal-bg border border-terminal-border rounded overflow-x-auto">
      <code className="text-sm font-mono text-zinc-300">{children}</code>
    </pre>
  );
}

function FAQ({
  question,
  children,
}: {
  question: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="text-zinc-200 font-medium mb-2 lg:font-mono">{question}</h3>
      <p className="text-sm text-zinc-400">{children}</p>
    </div>
  );
}
