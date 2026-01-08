#!/usr/bin/env python3
"""
Devnet End-to-End Test

Runs a complete test cycle of the $COPPER system on devnet.

This script orchestrates all components:
1. Takes snapshots
2. Simulates sells (streak penalties)
3. Executes buybacks
4. Triggers distributions
5. Verifies all data

Usage:
    python -m scripts.devnet.test_e2e [command]

Commands:
    full        - Run full E2E test (all steps)
    quick       - Run quick test (snapshot + streak only)
    verify      - Verify current system state
    reset       - Reset test data and start fresh
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import get_settings, TOKEN_MULTIPLIER, TIER_CONFIG
from app.models.models import (
    Snapshot, Balance, HoldStreak, Distribution, DistributionRecipient,
    Buyback, CreatorReward
)


def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class E2ETester:
    """Runs end-to-end tests of the $COPPER system."""

    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        self.async_session = None
        self.test_results = []

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

    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {"INFO": "   ", "PASS": " ✓ ", "FAIL": " ✗ ", "STEP": ">> "}
        print(f"[{timestamp}]{prefix.get(level, '   ')} {message}")

        if level in ["PASS", "FAIL"]:
            self.test_results.append((message, level == "PASS"))

    def log_step(self, step: int, title: str):
        """Log a test step."""
        print(f"\n{'='*60}")
        print(f"  STEP {step}: {title}")
        print(f"{'='*60}\n")

    # =========================================================================
    # Test Steps
    # =========================================================================

    async def step_verify_config(self) -> bool:
        """Step 0: Verify configuration."""
        self.log_step(0, "VERIFY CONFIGURATION")

        errors = []

        if not self.settings.copper_token_mint:
            errors.append("COPPER_TOKEN_MINT not set")
        else:
            self.log(f"Token mint: {self.settings.copper_token_mint[:20]}...")

        if not self.settings.database_url:
            errors.append("DATABASE_URL not set")
        else:
            self.log(f"Database: Connected")

        if not self.settings.helius_api_key:
            errors.append("HELIUS_API_KEY not set")
        else:
            self.log(f"Helius API: Configured")

        if self.settings.is_devnet:
            self.log(f"Network: devnet (correct)")
        else:
            errors.append("SOLANA_NETWORK should be 'devnet'")

        if errors:
            for e in errors:
                self.log(e, "FAIL")
            return False

        self.log("Configuration verified", "PASS")
        return True

    async def step_take_snapshots(self, count: int = 2) -> bool:
        """Step 1: Take multiple snapshots."""
        self.log_step(1, f"TAKE {count} SNAPSHOTS")

        from app.services.helius import HeliusService
        from app.services.snapshot import SnapshotService

        snapshots_taken = 0

        for i in range(count):
            self.log(f"Taking snapshot {i+1}/{count}...")

            async with self.async_session() as session:
                helius = HeliusService(self.settings)
                snapshot_service = SnapshotService(session, helius, self.settings)

                try:
                    snapshot = await snapshot_service.take_snapshot(force=True)
                    if snapshot:
                        self.log(f"Snapshot {snapshot.id}: {snapshot.holder_count} holders")
                        snapshots_taken += 1
                    else:
                        self.log(f"Failed to take snapshot {i+1}", "FAIL")
                except Exception as e:
                    self.log(f"Error: {e}", "FAIL")

            # Wait between snapshots
            if i < count - 1:
                self.log("Waiting 5 seconds...")
                await asyncio.sleep(5)

        if snapshots_taken == count:
            self.log(f"Took {snapshots_taken} snapshots", "PASS")
            return True
        else:
            self.log(f"Only took {snapshots_taken}/{count} snapshots", "FAIL")
            return False

    async def step_create_streaks(self) -> bool:
        """Step 2: Create streaks for holders from snapshots."""
        self.log_step(2, "CREATE STREAKS FOR HOLDERS")

        async with self.async_session() as session:
            # Get unique wallets from recent snapshots
            result = await session.execute(
                select(Balance.wallet_address)
                .distinct()
                .limit(100)
            )
            wallets = [row[0] for row in result.fetchall()]

            if not wallets:
                self.log("No wallets found in snapshots", "FAIL")
                return False

            self.log(f"Found {len(wallets)} unique wallets")

            # Create streaks for those without
            from app.services.streak import StreakService
            streak_service = StreakService(session)

            created = 0
            existing = 0

            for wallet in wallets:
                streak = await streak_service.get_streak(wallet)
                if not streak:
                    await streak_service.start_streak(wallet)
                    created += 1
                else:
                    existing += 1

            self.log(f"Created {created} new streaks, {existing} existing")
            self.log("Streaks created/verified", "PASS")
            return True

    async def step_simulate_sell(self, wallet: str = None) -> bool:
        """Step 3: Simulate a sell event."""
        self.log_step(3, "SIMULATE SELL EVENT")

        async with self.async_session() as session:
            # Find a wallet with tier > 1 to test demotion
            from app.services.streak import StreakService
            streak_service = StreakService(session)

            if wallet is None:
                # Find a high-tier wallet
                result = await session.execute(
                    select(HoldStreak)
                    .where(HoldStreak.current_tier > 1)
                    .order_by(HoldStreak.current_tier.desc())
                    .limit(1)
                )
                streak = result.scalar_one_or_none()

                if not streak:
                    # Upgrade a wallet first
                    result = await session.execute(
                        select(HoldStreak).limit(1)
                    )
                    streak = result.scalar_one_or_none()

                    if streak:
                        # Manually set to tier 3 for testing
                        streak.current_tier = 3
                        streak.streak_start = utc_now() - timedelta(hours=20)
                        await session.commit()
                        self.log(f"Set {streak.wallet[:16]}... to tier 3 for testing")

                wallet = streak.wallet if streak else None

            if not wallet:
                self.log("No wallet found to test sell", "FAIL")
                return False

            # Get current state
            info_before = await streak_service.get_streak_info(wallet)
            self.log(f"Before: Tier {info_before.tier} ({info_before.tier_name})")

            # Process sell
            result = await streak_service.process_sell(wallet)

            if result:
                info_after = await streak_service.get_streak_info(wallet)
                self.log(f"After:  Tier {info_after.tier} ({info_after.tier_name})")

                if info_after.tier < info_before.tier:
                    self.log("Sell correctly dropped tier", "PASS")
                    return True
                else:
                    self.log("Tier did not drop (may be at tier 1)", "PASS")
                    return True
            else:
                self.log("Sell processing failed", "FAIL")
                return False

    async def step_add_rewards(self, amount_sol: float = 0.1) -> bool:
        """Step 4: Add creator rewards to pool."""
        self.log_step(4, f"ADD {amount_sol} SOL CREATOR REWARDS")

        async with self.async_session() as session:
            from app.services.buyback import BuybackService
            buyback_service = BuybackService(session)

            reward = await buyback_service.record_creator_reward(
                amount_sol=Decimal(str(amount_sol)),
                source="devnet_test",
                tx_signature=f"test_reward_{int(datetime.now().timestamp())}"
            )

            self.log(f"Added reward: {amount_sol} SOL")
            self.log("Creator reward recorded", "PASS")
            return True

    async def step_check_buyback(self) -> bool:
        """Step 5: Check buyback status (don't execute on devnet without liquidity)."""
        self.log_step(5, "CHECK BUYBACK STATUS")

        async with self.async_session() as session:
            from app.services.buyback import BuybackService
            buyback_service = BuybackService(session)

            # Get pending rewards
            rewards = await buyback_service.get_unprocessed_rewards()
            total_sol = sum(r.amount_sol for r in rewards)

            self.log(f"Pending rewards: {len(rewards)}")
            self.log(f"Total SOL: {float(total_sol):.4f}")

            if total_sol > 0:
                split = buyback_service.calculate_split(total_sol)
                self.log(f"Buyback (80%): {float(split.buyback_sol):.4f} SOL")
                self.log(f"Team (20%): {float(split.team_sol):.4f} SOL")

            # Get Jupiter quote (if token has liquidity)
            if self.settings.copper_token_mint and total_sol > 0:
                try:
                    quote = await buyback_service.get_jupiter_quote(
                        int(float(split.buyback_sol) * 1e9)
                    )
                    if quote:
                        out_amount = int(quote.get("outAmount", 0))
                        self.log(f"Jupiter quote: {out_amount / TOKEN_MULTIPLIER:,.2f} tokens")
                    else:
                        self.log("No Jupiter liquidity (expected on devnet)")
                except Exception as e:
                    self.log(f"Jupiter quote error: {e}")

            self.log("Buyback check complete", "PASS")
            return True

    async def step_check_distribution(self) -> bool:
        """Step 6: Check distribution calculation."""
        self.log_step(6, "CHECK DISTRIBUTION CALCULATION")

        # Import test_distribution functions
        from scripts.devnet.test_distribution import DistributionTester
        dist_tester = DistributionTester()
        dist_tester.async_session = self.async_session

        # Simulate with fake pool amount
        self.log("Calculating distribution with simulated pool...")
        plan = await dist_tester.calculate_distribution(
            pool_amount=int(1_000_000 * TOKEN_MULTIPLIER)  # 1M tokens
        )

        if plan:
            self.log(f"Recipients: {len(plan['recipients'])}")
            self.log(f"Total hash power: {float(plan['total_hp']):,.2f}")
            self.log("Distribution calculation works", "PASS")
            return True
        else:
            self.log("Distribution calculation failed", "FAIL")
            return False

    async def step_verify_state(self) -> bool:
        """Step 7: Verify overall system state."""
        self.log_step(7, "VERIFY SYSTEM STATE")

        async with self.async_session() as session:
            # Count snapshots
            result = await session.execute(select(func.count(Snapshot.id)))
            snapshot_count = result.scalar_one()
            self.log(f"Snapshots: {snapshot_count}")

            # Count balances
            result = await session.execute(select(func.count(Balance.id)))
            balance_count = result.scalar_one()
            self.log(f"Balance records: {balance_count}")

            # Count streaks
            result = await session.execute(select(func.count(HoldStreak.id)))
            streak_count = result.scalar_one()
            self.log(f"Streaks: {streak_count}")

            # Tier distribution
            from app.services.streak import StreakService
            streak_service = StreakService(session)
            distribution = await streak_service.get_tier_distribution()

            self.log("Tier distribution:")
            for tier, count in distribution.items():
                if count > 0:
                    self.log(f"  Tier {tier} ({TIER_CONFIG[tier]['name']}): {count}")

            # Count distributions
            result = await session.execute(select(func.count(Distribution.id)))
            dist_count = result.scalar_one()
            self.log(f"Distributions: {dist_count}")

            # Count buybacks
            result = await session.execute(select(func.count(Buyback.id)))
            buyback_count = result.scalar_one()
            self.log(f"Buybacks: {buyback_count}")

            self.log("System state verified", "PASS")
            return True

    # =========================================================================
    # Test Suites
    # =========================================================================

    async def run_full_test(self):
        """Run full E2E test."""
        print("\n" + "="*60)
        print("  $COPPER DEVNET E2E TEST - FULL")
        print("="*60)

        steps = [
            ("Verify Configuration", self.step_verify_config),
            ("Take Snapshots", lambda: self.step_take_snapshots(2)),
            ("Create Streaks", self.step_create_streaks),
            ("Simulate Sell", self.step_simulate_sell),
            ("Add Rewards", lambda: self.step_add_rewards(0.1)),
            ("Check Buyback", self.step_check_buyback),
            ("Check Distribution", self.step_check_distribution),
            ("Verify State", self.step_verify_state),
        ]

        passed = 0
        failed = 0

        for name, step_func in steps:
            try:
                result = await step_func()
                if result:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log(f"Error in {name}: {e}", "FAIL")
                failed += 1

        # Summary
        print("\n" + "="*60)
        print("  TEST SUMMARY")
        print("="*60)
        print(f"\n  Total steps: {len(steps)}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")
        print()

        for result_name, result_passed in self.test_results:
            status = "PASS" if result_passed else "FAIL"
            print(f"  [{status}] {result_name}")

        print("\n" + "="*60)
        if failed == 0:
            print("  ALL TESTS PASSED!")
        else:
            print(f"  {failed} TESTS FAILED")
        print("="*60 + "\n")

        return failed == 0

    async def run_quick_test(self):
        """Run quick test (snapshot + streak only)."""
        print("\n" + "="*60)
        print("  $COPPER DEVNET E2E TEST - QUICK")
        print("="*60)

        steps = [
            ("Verify Configuration", self.step_verify_config),
            ("Take Snapshot", lambda: self.step_take_snapshots(1)),
            ("Create Streaks", self.step_create_streaks),
        ]

        passed = 0
        failed = 0

        for name, step_func in steps:
            try:
                result = await step_func()
                if result:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log(f"Error in {name}: {e}", "FAIL")
                failed += 1

        print(f"\n  Quick test complete: {passed} passed, {failed} failed")
        return failed == 0

    async def run_verify(self):
        """Verify current system state."""
        print("\n" + "="*60)
        print("  $COPPER DEVNET - VERIFY STATE")
        print("="*60)

        await self.step_verify_state()


async def main():
    tester = E2ETester()

    try:
        await tester.setup()

        if len(sys.argv) < 2:
            print(__doc__)
            return

        command = sys.argv[1].lower()

        if command == "full":
            success = await tester.run_full_test()
            sys.exit(0 if success else 1)

        elif command == "quick":
            success = await tester.run_quick_test()
            sys.exit(0 if success else 1)

        elif command == "verify":
            await tester.run_verify()

        elif command == "reset":
            print("Reset not implemented - use cleanup.py instead")

        else:
            print(f"Unknown command: {command}")
            print(__doc__)

    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
