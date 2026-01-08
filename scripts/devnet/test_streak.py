#!/usr/bin/env python3
"""
Devnet Streak Test

Tests streak tracking and sell detection on devnet.

Usage:
    python -m scripts.devnet.test_streak [command]

Commands:
    status <wallet>     - Show streak status for a wallet
    create <wallet>     - Create new streak for wallet
    upgrade <wallet>    - Check and apply tier upgrades
    sell <wallet>       - Simulate a sell event
    tiers               - Show tier distribution
    list                - List all streaks
    simulate            - Run simulation of tier progression
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import get_settings, TIER_CONFIG, TIER_THRESHOLDS
from app.models.models import HoldStreak
from app.services.streak import StreakService


def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class StreakTester:
    """Tests streak functionality on devnet."""

    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        self.async_session = None

    async def setup(self):
        """Initialize database connection."""
        db_url = self.settings.database_url
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def cleanup(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()

    async def show_status(self, wallet: str):
        """Show streak status for a wallet."""
        print(f"\n=== Streak Status: {wallet[:16]}... ===\n")

        async with self.async_session() as session:
            service = StreakService(session)
            info = await service.get_streak_info(wallet)

            if not info:
                print("  No streak found for this wallet")
                print("  Use 'create <wallet>' to start a streak")
                return

            print(f"  Wallet:      {info.wallet}")
            print(f"  Tier:        {info.tier} - {info.tier_emoji} {info.tier_name}")
            print(f"  Multiplier:  {info.multiplier}x")
            print(f"  Streak:      {info.streak_hours:.1f} hours")
            print(f"  Started:     {info.streak_start}")

            if info.last_sell_at:
                print(f"  Last Sell:   {info.last_sell_at}")

            if info.next_tier:
                print(f"\n  Next Tier:   {info.next_tier} - {info.next_tier_name}")
                print(f"  Hours Left:  {info.hours_to_next_tier:.1f} hours")

                # Progress bar
                current_threshold = TIER_THRESHOLDS[info.tier]
                next_threshold = TIER_THRESHOLDS[info.next_tier]
                progress = (info.streak_hours - current_threshold) / (next_threshold - current_threshold)
                bar_width = 30
                filled = int(bar_width * min(1, progress))
                bar = "█" * filled + "░" * (bar_width - filled)
                print(f"  Progress:    [{bar}] {progress*100:.0f}%")
            else:
                print("\n  Max tier reached!")

    async def create_streak(self, wallet: str):
        """Create a new streak for a wallet."""
        print(f"\n=== Creating Streak: {wallet[:16]}... ===\n")

        async with self.async_session() as session:
            service = StreakService(session)

            # Check if exists
            existing = await service.get_streak(wallet)
            if existing:
                print(f"  Streak already exists!")
                print(f"  Tier: {existing.current_tier}")
                print(f"  Started: {existing.streak_start}")
                return

            # Create new
            streak = await service.start_streak(wallet)
            print(f"  Streak created!")
            print(f"  Tier: {streak.current_tier} - {TIER_CONFIG[1]['name']}")
            print(f"  Started: {streak.streak_start}")

    async def check_upgrade(self, wallet: str):
        """Check and apply tier upgrades for a wallet."""
        print(f"\n=== Checking Tier Upgrade: {wallet[:16]}... ===\n")

        async with self.async_session() as session:
            service = StreakService(session)

            # Get current state
            streak = await service.get_streak(wallet)
            if not streak:
                print("  No streak found")
                return

            old_tier = streak.current_tier
            streak_hours = (utc_now() - streak.streak_start).total_seconds() / 3600

            print(f"  Current tier: {old_tier} - {TIER_CONFIG[old_tier]['name']}")
            print(f"  Streak hours: {streak_hours:.1f}")

            # Check upgrade
            result = await service.update_tier_if_needed(wallet)

            if result:
                new_tier = result.current_tier
                print(f"\n  Tier upgraded!")
                print(f"  New tier: {new_tier} - {TIER_CONFIG[new_tier]['name']}")
                print(f"  New multiplier: {TIER_CONFIG[new_tier]['multiplier']}x")
            else:
                expected_tier = service.calculate_tier_from_hours(streak_hours)
                print(f"\n  No upgrade needed")
                print(f"  Expected tier for {streak_hours:.1f}h: {expected_tier}")

    async def simulate_sell(self, wallet: str):
        """Simulate a sell event for a wallet."""
        print(f"\n=== Simulating Sell: {wallet[:16]}... ===\n")

        async with self.async_session() as session:
            service = StreakService(session)

            # Get current state
            streak = await service.get_streak(wallet)
            if not streak:
                print("  No streak found")
                return

            old_tier = streak.current_tier
            old_multiplier = TIER_CONFIG[old_tier]["multiplier"]

            print(f"  Before sell:")
            print(f"    Tier: {old_tier} - {TIER_CONFIG[old_tier]['name']}")
            print(f"    Multiplier: {old_multiplier}x")

            # Process sell
            result = await service.process_sell(wallet)

            new_tier = result.current_tier
            new_multiplier = TIER_CONFIG[new_tier]["multiplier"]

            print(f"\n  After sell:")
            print(f"    Tier: {new_tier} - {TIER_CONFIG[new_tier]['name']}")
            print(f"    Multiplier: {new_multiplier}x")
            print(f"    Streak reset to: {TIER_THRESHOLDS[new_tier]}h")

            if old_tier > new_tier:
                loss = ((old_multiplier - new_multiplier) / old_multiplier) * 100
                print(f"\n  Impact: -{loss:.0f}% multiplier reduction")

    async def show_tier_distribution(self):
        """Show distribution of wallets across tiers."""
        print("\n=== Tier Distribution ===\n")

        async with self.async_session() as session:
            service = StreakService(session)
            distribution = await service.get_tier_distribution()

            total = sum(distribution.values())

            print(f"  {'Tier':<5} {'Name':<15} {'Mult':>6} {'Count':>8} {'%':>8}")
            print(f"  {'-'*5} {'-'*15} {'-'*6} {'-'*8} {'-'*8}")

            for tier in range(1, 7):
                config = TIER_CONFIG[tier]
                count = distribution.get(tier, 0)
                pct = (count / total * 100) if total > 0 else 0
                bar = "█" * int(pct / 5) if pct > 0 else ""

                print(f"  {tier:<5} {config['name']:<15} {config['multiplier']:>5}x {count:>8} {pct:>7.1f}% {bar}")

            print(f"\n  Total wallets with streaks: {total}")

    async def list_streaks(self, limit: int = 20):
        """List all streaks."""
        print("\n=== All Streaks ===\n")

        async with self.async_session() as session:
            result = await session.execute(
                select(HoldStreak)
                .order_by(HoldStreak.current_tier.desc(), HoldStreak.streak_start.asc())
                .limit(limit)
            )
            streaks = result.scalars().all()

            if not streaks:
                print("  No streaks found")
                return

            print(f"  {'Wallet':<20} {'Tier':>5} {'Name':<15} {'Hours':>10} {'Last Sell':<20}")
            print(f"  {'-'*20} {'-'*5} {'-'*15} {'-'*10} {'-'*20}")

            for s in streaks:
                hours = (utc_now() - s.streak_start).total_seconds() / 3600
                tier_name = TIER_CONFIG[s.current_tier]["name"]
                last_sell = s.last_sell_at.strftime("%Y-%m-%d %H:%M") if s.last_sell_at else "Never"
                print(f"  {s.wallet[:20]:<20} {s.current_tier:>5} {tier_name:<15} {hours:>10.1f} {last_sell:<20}")

    async def simulate_progression(self, wallet: str = None):
        """Simulate tier progression over time."""
        print("\n=== Tier Progression Simulation ===\n")

        print("  Showing how tiers progress over time:\n")
        print(f"  {'Hours':<10} {'Tier':>5} {'Name':<15} {'Multiplier':>10}")
        print(f"  {'-'*10} {'-'*5} {'-'*15} {'-'*10}")

        test_hours = [0, 3, 6, 12, 24, 48, 72, 120, 168, 360, 720, 1000]

        for hours in test_hours:
            tier = 1
            for t, threshold in TIER_THRESHOLDS.items():
                if hours >= threshold:
                    tier = t

            config = TIER_CONFIG[tier]
            print(f"  {hours:<10} {tier:>5} {config['name']:<15} {config['multiplier']:>9}x")

        print("\n  Sell Impact Simulation:\n")
        print(f"  {'From Tier':>10} {'To Tier':>10} {'Mult Loss':>12}")
        print(f"  {'-'*10} {'-'*10} {'-'*12}")

        for tier in range(2, 7):
            old_mult = TIER_CONFIG[tier]["multiplier"]
            new_mult = TIER_CONFIG[tier - 1]["multiplier"]
            loss = ((old_mult - new_mult) / old_mult) * 100
            print(f"  {tier:>10} {tier-1:>10} {loss:>11.1f}%")

    async def set_tier(self, wallet: str, tier: int):
        """Manually set tier for testing (debug command)."""
        print(f"\n=== Setting Tier: {wallet[:16]}... → Tier {tier} ===\n")

        if tier < 1 or tier > 6:
            print("  Error: Tier must be 1-6")
            return

        async with self.async_session() as session:
            # Get or create streak
            service = StreakService(session)
            streak = await service.get_or_create_streak(wallet)

            # Calculate streak start for desired tier
            min_hours = TIER_THRESHOLDS[tier]
            new_start = utc_now() - timedelta(hours=min_hours + 1)

            # Update
            await session.execute(
                update(HoldStreak)
                .where(HoldStreak.wallet == wallet)
                .values(
                    current_tier=tier,
                    streak_start=new_start,
                    updated_at=utc_now()
                )
            )
            await session.commit()

            print(f"  Set tier to: {tier} - {TIER_CONFIG[tier]['name']}")
            print(f"  Multiplier: {TIER_CONFIG[tier]['multiplier']}x")
            print(f"  Streak start: {new_start}")


async def main():
    tester = StreakTester()

    try:
        await tester.setup()

        if len(sys.argv) < 2:
            print(__doc__)
            return

        command = sys.argv[1].lower()

        if command == "status":
            if len(sys.argv) < 3:
                print("Usage: test_streak.py status <wallet>")
                return
            await tester.show_status(sys.argv[2])

        elif command == "create":
            if len(sys.argv) < 3:
                print("Usage: test_streak.py create <wallet>")
                return
            await tester.create_streak(sys.argv[2])

        elif command == "upgrade":
            if len(sys.argv) < 3:
                print("Usage: test_streak.py upgrade <wallet>")
                return
            await tester.check_upgrade(sys.argv[2])

        elif command == "sell":
            if len(sys.argv) < 3:
                print("Usage: test_streak.py sell <wallet>")
                return
            await tester.simulate_sell(sys.argv[2])

        elif command == "tiers":
            await tester.show_tier_distribution()

        elif command == "list":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            await tester.list_streaks(limit)

        elif command == "simulate":
            wallet = sys.argv[2] if len(sys.argv) > 2 else None
            await tester.simulate_progression(wallet)

        elif command == "set-tier":
            if len(sys.argv) < 4:
                print("Usage: test_streak.py set-tier <wallet> <tier>")
                return
            await tester.set_tier(sys.argv[2], int(sys.argv[3]))

        else:
            print(f"Unknown command: {command}")
            print(__doc__)

    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
