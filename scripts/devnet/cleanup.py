#!/usr/bin/env python3
"""
Devnet Cleanup Script

Removes test data from the database to reset for fresh testing.

Usage:
    python -m scripts.devnet.cleanup [command]

Commands:
    all             - Delete ALL test data (snapshots, balances, streaks, distributions, buybacks)
    snapshots       - Delete all snapshots and balances
    streaks         - Delete all streak records
    distributions   - Delete all distribution records
    buybacks        - Delete all buyback and reward records
    dry-run         - Show what would be deleted without deleting

CAUTION: This permanently deletes data. Use with care!
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models.models import (
    Snapshot, Balance, HoldStreak, Distribution, DistributionRecipient,
    Buyback, CreatorReward, SystemStats
)


class Cleanup:
    """Handles database cleanup for devnet testing."""

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

    async def count_records(self) -> dict:
        """Count all records in tables."""
        async with self.async_session() as session:
            counts = {}

            for model, name in [
                (Snapshot, "snapshots"),
                (Balance, "balances"),
                (HoldStreak, "streaks"),
                (Distribution, "distributions"),
                (DistributionRecipient, "distribution_recipients"),
                (Buyback, "buybacks"),
                (CreatorReward, "creator_rewards"),
            ]:
                result = await session.execute(select(func.count()).select_from(model))
                counts[name] = result.scalar_one()

            return counts

    async def dry_run(self):
        """Show what would be deleted without actually deleting."""
        print("\n=== DRY RUN - No data will be deleted ===\n")

        counts = await self.count_records()

        print("  Records that would be deleted:\n")
        total = 0
        for table, count in counts.items():
            print(f"    {table:<25} {count:>8,} records")
            total += count

        print(f"\n    {'TOTAL':<25} {total:>8,} records")
        print("\n  Run with 'all' command to actually delete.")

    async def delete_snapshots(self, confirm: bool = True) -> int:
        """Delete all snapshots and balances."""
        print("\n=== Deleting Snapshots & Balances ===\n")

        async with self.async_session() as session:
            # Get counts
            snap_result = await session.execute(select(func.count(Snapshot.id)))
            snap_count = snap_result.scalar_one()

            bal_result = await session.execute(select(func.count(Balance.id)))
            bal_count = bal_result.scalar_one()

            print(f"  Snapshots: {snap_count:,}")
            print(f"  Balances:  {bal_count:,}")

            if confirm:
                response = input("\n  Delete these records? (yes/no): ")
                if response.lower() != "yes":
                    print("  Cancelled.")
                    return 0

            # Delete balances first (foreign key)
            await session.execute(delete(Balance))
            await session.execute(delete(Snapshot))
            await session.commit()

            print(f"\n  Deleted {snap_count} snapshots and {bal_count} balances")
            return snap_count + bal_count

    async def delete_streaks(self, confirm: bool = True) -> int:
        """Delete all streak records."""
        print("\n=== Deleting Streaks ===\n")

        async with self.async_session() as session:
            result = await session.execute(select(func.count(HoldStreak.id)))
            count = result.scalar_one()

            print(f"  Streaks: {count:,}")

            if confirm:
                response = input("\n  Delete these records? (yes/no): ")
                if response.lower() != "yes":
                    print("  Cancelled.")
                    return 0

            await session.execute(delete(HoldStreak))
            await session.commit()

            print(f"\n  Deleted {count} streaks")
            return count

    async def delete_distributions(self, confirm: bool = True) -> int:
        """Delete all distribution records."""
        print("\n=== Deleting Distributions ===\n")

        async with self.async_session() as session:
            dist_result = await session.execute(select(func.count(Distribution.id)))
            dist_count = dist_result.scalar_one()

            recip_result = await session.execute(select(func.count(DistributionRecipient.id)))
            recip_count = recip_result.scalar_one()

            print(f"  Distributions: {dist_count:,}")
            print(f"  Recipients:    {recip_count:,}")

            if confirm:
                response = input("\n  Delete these records? (yes/no): ")
                if response.lower() != "yes":
                    print("  Cancelled.")
                    return 0

            # Delete recipients first (foreign key)
            await session.execute(delete(DistributionRecipient))
            await session.execute(delete(Distribution))
            await session.commit()

            print(f"\n  Deleted {dist_count} distributions and {recip_count} recipients")
            return dist_count + recip_count

    async def delete_buybacks(self, confirm: bool = True) -> int:
        """Delete all buyback and creator reward records."""
        print("\n=== Deleting Buybacks & Rewards ===\n")

        async with self.async_session() as session:
            buy_result = await session.execute(select(func.count(Buyback.id)))
            buy_count = buy_result.scalar_one()

            reward_result = await session.execute(select(func.count(CreatorReward.id)))
            reward_count = reward_result.scalar_one()

            print(f"  Buybacks: {buy_count:,}")
            print(f"  Rewards:  {reward_count:,}")

            if confirm:
                response = input("\n  Delete these records? (yes/no): ")
                if response.lower() != "yes":
                    print("  Cancelled.")
                    return 0

            await session.execute(delete(Buyback))
            await session.execute(delete(CreatorReward))
            await session.commit()

            print(f"\n  Deleted {buy_count} buybacks and {reward_count} rewards")
            return buy_count + reward_count

    async def delete_all(self, confirm: bool = True) -> int:
        """Delete all test data."""
        print("\n" + "="*60)
        print("  WARNING: This will delete ALL data!")
        print("="*60 + "\n")

        counts = await self.count_records()

        print("  Records to delete:\n")
        total = 0
        for table, count in counts.items():
            print(f"    {table:<25} {count:>8,} records")
            total += count

        print(f"\n    {'TOTAL':<25} {total:>8,} records")

        if confirm:
            print("\n  Type 'DELETE ALL' to confirm:")
            response = input("  > ")
            if response != "DELETE ALL":
                print("  Cancelled.")
                return 0

        # Delete in order (respecting foreign keys)
        async with self.async_session() as session:
            print("\n  Deleting...")

            # Distribution recipients first
            await session.execute(delete(DistributionRecipient))
            print("    - distribution_recipients")

            # Then distributions
            await session.execute(delete(Distribution))
            print("    - distributions")

            # Balances first (references snapshots)
            await session.execute(delete(Balance))
            print("    - balances")

            # Snapshots
            await session.execute(delete(Snapshot))
            print("    - snapshots")

            # Streaks
            await session.execute(delete(HoldStreak))
            print("    - hold_streaks")

            # Buybacks
            await session.execute(delete(Buyback))
            print("    - buybacks")

            # Creator rewards
            await session.execute(delete(CreatorReward))
            print("    - creator_rewards")

            # Reset system stats
            result = await session.execute(select(SystemStats))
            stats = result.scalar_one_or_none()
            if stats:
                stats.total_buybacks = 0
                stats.total_distributed = 0
                stats.last_distribution_at = None
                stats.updated_at = datetime.now(timezone.utc)
                print("    - reset system_stats")

            await session.commit()

        print(f"\n  Deleted {total:,} records total")
        print("\n  Database cleaned! Ready for fresh testing.")
        return total

    async def reset_system_stats(self):
        """Reset system stats to zero."""
        print("\n=== Resetting System Stats ===\n")

        async with self.async_session() as session:
            result = await session.execute(select(SystemStats))
            stats = result.scalar_one_or_none()

            if stats:
                print(f"  Before:")
                print(f"    total_buybacks:    {stats.total_buybacks or 0}")
                print(f"    total_distributed: {stats.total_distributed or 0}")
                print(f"    last_distribution: {stats.last_distribution_at}")

                stats.total_buybacks = 0
                stats.total_distributed = 0
                stats.last_distribution_at = None
                stats.updated_at = datetime.now(timezone.utc)
                await session.commit()

                print(f"\n  After:")
                print(f"    total_buybacks:    0")
                print(f"    total_distributed: 0")
                print(f"    last_distribution: None")
            else:
                print("  No system stats record found")


async def main():
    cleanup = Cleanup()

    try:
        await cleanup.setup()

        if len(sys.argv) < 2:
            print(__doc__)
            return

        command = sys.argv[1].lower()

        # Check for --force flag
        force = "--force" in sys.argv or "-f" in sys.argv

        if command == "all":
            await cleanup.delete_all(confirm=not force)

        elif command == "snapshots":
            await cleanup.delete_snapshots(confirm=not force)

        elif command == "streaks":
            await cleanup.delete_streaks(confirm=not force)

        elif command == "distributions":
            await cleanup.delete_distributions(confirm=not force)

        elif command == "buybacks":
            await cleanup.delete_buybacks(confirm=not force)

        elif command == "dry-run":
            await cleanup.dry_run()

        elif command == "stats":
            await cleanup.reset_system_stats()

        else:
            print(f"Unknown command: {command}")
            print(__doc__)

    finally:
        await cleanup.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
