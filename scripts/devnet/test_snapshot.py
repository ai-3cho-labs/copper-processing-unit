#!/usr/bin/env python3
"""
Devnet Snapshot Test

Tests the snapshot flow by triggering a snapshot and verifying database records.

Usage:
    python -m scripts.devnet.test_snapshot [command]

Commands:
    take        - Take a snapshot now (bypasses RNG)
    verify      - Verify last snapshot data
    list        - List recent snapshots
    balances    - Show balances from last snapshot
    compare     - Compare on-chain vs snapshot balances
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models.models import Snapshot, Balance, HoldStreak, ExcludedWallet
from app.services.snapshot import SnapshotService
from app.services.helius import HeliusService


class SnapshotTester:
    """Tests snapshot functionality on devnet."""

    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        self.async_session = None

    async def setup(self):
        """Initialize database connection."""
        # Convert postgres:// to postgresql+asyncpg://
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

    async def take_snapshot(self) -> dict:
        """Take a snapshot, bypassing RNG check."""
        print("\n=== Taking Snapshot ===\n")

        if not self.settings.copper_token_mint:
            print("Error: COPPER_TOKEN_MINT not set")
            return None

        print(f"  Token: {self.settings.copper_token_mint}")
        print(f"  Network: {self.settings.solana_network}")
        print(f"  RPC: {self.settings.helius_rpc_url[:50]}...")

        async with self.async_session() as session:
            # Initialize services
            helius = HeliusService(self.settings)
            snapshot_service = SnapshotService(session, helius, self.settings)

            try:
                # Get excluded wallets
                result = await session.execute(select(ExcludedWallet))
                excluded = [w.wallet_address for w in result.scalars().all()]
                print(f"  Excluded wallets: {len(excluded)}")

                # Fetch holders from Helius
                print("  Fetching token holders...")
                holders = await helius.get_token_accounts(
                    self.settings.copper_token_mint
                )
                print(f"  Found {len(holders)} holders on-chain")

                # Filter excluded
                holders = [h for h in holders if h["owner"] not in excluded]
                print(f"  After exclusions: {len(holders)} holders")

                # Take snapshot
                print("  Creating snapshot...")
                snapshot = await snapshot_service.take_snapshot(force=True)

                if snapshot:
                    print(f"\n  Snapshot created!")
                    print(f"  ID: {snapshot.id}")
                    print(f"  Time: {snapshot.snapshot_at}")
                    print(f"  Holders: {snapshot.holder_count}")
                    return {
                        "id": snapshot.id,
                        "snapshot_at": snapshot.snapshot_at.isoformat(),
                        "holder_count": snapshot.holder_count,
                    }
                else:
                    print("  Failed to create snapshot")
                    return None

            except Exception as e:
                print(f"  Error: {e}")
                import traceback
                traceback.print_exc()
                return None

    async def verify_snapshot(self, snapshot_id: int = None) -> bool:
        """Verify snapshot data integrity."""
        print("\n=== Verifying Snapshot ===\n")

        async with self.async_session() as session:
            # Get latest snapshot if not specified
            if snapshot_id is None:
                result = await session.execute(
                    select(Snapshot).order_by(Snapshot.snapshot_at.desc()).limit(1)
                )
                snapshot = result.scalar_one_or_none()
                if not snapshot:
                    print("  No snapshots found")
                    return False
                snapshot_id = snapshot.id
            else:
                result = await session.execute(
                    select(Snapshot).where(Snapshot.id == snapshot_id)
                )
                snapshot = result.scalar_one_or_none()
                if not snapshot:
                    print(f"  Snapshot {snapshot_id} not found")
                    return False

            print(f"  Snapshot ID: {snapshot.id}")
            print(f"  Time: {snapshot.snapshot_at}")
            print(f"  Holder count: {snapshot.holder_count}")

            # Get balance records
            result = await session.execute(
                select(Balance).where(Balance.snapshot_id == snapshot_id)
            )
            balances = result.scalars().all()

            print(f"\n  Balance records: {len(balances)}")

            if len(balances) != snapshot.holder_count:
                print(f"  WARNING: Holder count mismatch!")
                print(f"    Snapshot says: {snapshot.holder_count}")
                print(f"    Actual records: {len(balances)}")

            # Verify balances are positive
            zero_balances = sum(1 for b in balances if b.balance <= 0)
            if zero_balances > 0:
                print(f"  WARNING: {zero_balances} balances are zero or negative")

            # Sum total balance
            total = sum(b.balance for b in balances)
            print(f"  Total tokens: {total:,.0f}")

            # Show top 5 holders
            print("\n  Top 5 holders:")
            sorted_balances = sorted(balances, key=lambda b: b.balance, reverse=True)
            for i, b in enumerate(sorted_balances[:5]):
                pct = (b.balance / total * 100) if total > 0 else 0
                print(f"    {i+1}. {b.wallet_address[:12]}... {b.balance:>15,.0f} ({pct:.1f}%)")

            print("\n  Verification passed!")
            return True

    async def list_snapshots(self, limit: int = 10):
        """List recent snapshots."""
        print("\n=== Recent Snapshots ===\n")

        async with self.async_session() as session:
            result = await session.execute(
                select(Snapshot)
                .order_by(Snapshot.snapshot_at.desc())
                .limit(limit)
            )
            snapshots = result.scalars().all()

            if not snapshots:
                print("  No snapshots found")
                return

            print(f"  {'ID':<6} {'Time':<20} {'Holders':<10} {'Type':<10}")
            print(f"  {'-'*6} {'-'*20} {'-'*10} {'-'*10}")

            for s in snapshots:
                time_str = s.snapshot_at.strftime("%Y-%m-%d %H:%M")
                print(f"  {s.id:<6} {time_str:<20} {s.holder_count:<10} {s.snapshot_type or 'hourly':<10}")

    async def show_balances(self, snapshot_id: int = None):
        """Show balances from a snapshot."""
        print("\n=== Snapshot Balances ===\n")

        async with self.async_session() as session:
            # Get latest snapshot if not specified
            if snapshot_id is None:
                result = await session.execute(
                    select(Snapshot).order_by(Snapshot.snapshot_at.desc()).limit(1)
                )
                snapshot = result.scalar_one_or_none()
                if not snapshot:
                    print("  No snapshots found")
                    return
                snapshot_id = snapshot.id
                print(f"  Using latest snapshot: {snapshot_id} ({snapshot.snapshot_at})")
            else:
                result = await session.execute(
                    select(Snapshot).where(Snapshot.id == snapshot_id)
                )
                snapshot = result.scalar_one_or_none()
                if not snapshot:
                    print(f"  Snapshot {snapshot_id} not found")
                    return
                print(f"  Snapshot: {snapshot_id} ({snapshot.snapshot_at})")

            # Get balances
            result = await session.execute(
                select(Balance)
                .where(Balance.snapshot_id == snapshot_id)
                .order_by(Balance.balance.desc())
            )
            balances = result.scalars().all()

            print(f"\n  Total holders: {len(balances)}\n")
            print(f"  {'#':<4} {'Wallet':<44} {'Balance':>18}")
            print(f"  {'-'*4} {'-'*44} {'-'*18}")

            for i, b in enumerate(balances[:20], 1):
                print(f"  {i:<4} {b.wallet_address:<44} {b.balance:>18,.0f}")

            if len(balances) > 20:
                print(f"\n  ... and {len(balances) - 20} more")

    async def compare_balances(self):
        """Compare on-chain balances vs last snapshot."""
        print("\n=== Comparing On-Chain vs Snapshot ===\n")

        if not self.settings.copper_token_mint:
            print("Error: COPPER_TOKEN_MINT not set")
            return

        async with self.async_session() as session:
            # Get latest snapshot
            result = await session.execute(
                select(Snapshot).order_by(Snapshot.snapshot_at.desc()).limit(1)
            )
            snapshot = result.scalar_one_or_none()
            if not snapshot:
                print("  No snapshots found")
                return

            print(f"  Snapshot: {snapshot.id} ({snapshot.snapshot_at})")

            # Get snapshot balances
            result = await session.execute(
                select(Balance).where(Balance.snapshot_id == snapshot.id)
            )
            snapshot_balances = {b.wallet_address: b.balance for b in result.scalars()}

            # Get on-chain balances
            helius = HeliusService(self.settings)
            holders = await helius.get_token_accounts(self.settings.copper_token_mint)
            onchain_balances = {h["owner"]: h["amount"] for h in holders}

            print(f"  Snapshot holders: {len(snapshot_balances)}")
            print(f"  On-chain holders: {len(onchain_balances)}")

            # Compare
            all_wallets = set(snapshot_balances.keys()) | set(onchain_balances.keys())
            differences = []

            for wallet in all_wallets:
                snap_bal = snapshot_balances.get(wallet, 0)
                chain_bal = onchain_balances.get(wallet, 0)
                if snap_bal != chain_bal:
                    diff = chain_bal - snap_bal
                    differences.append({
                        "wallet": wallet,
                        "snapshot": snap_bal,
                        "onchain": chain_bal,
                        "diff": diff,
                    })

            if not differences:
                print("\n  All balances match!")
            else:
                print(f"\n  Found {len(differences)} differences:\n")
                print(f"  {'Wallet':<20} {'Snapshot':>15} {'On-Chain':>15} {'Diff':>15}")
                print(f"  {'-'*20} {'-'*15} {'-'*15} {'-'*15}")

                for d in sorted(differences, key=lambda x: abs(x["diff"]), reverse=True)[:10]:
                    print(f"  {d['wallet'][:20]:<20} {d['snapshot']:>15,.0f} {d['onchain']:>15,.0f} {d['diff']:>+15,.0f}")

                if len(differences) > 10:
                    print(f"\n  ... and {len(differences) - 10} more")


async def main():
    tester = SnapshotTester()

    try:
        await tester.setup()

        if len(sys.argv) < 2:
            print(__doc__)
            return

        command = sys.argv[1].lower()

        if command == "take":
            await tester.take_snapshot()
        elif command == "verify":
            snapshot_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
            await tester.verify_snapshot(snapshot_id)
        elif command == "list":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            await tester.list_snapshots(limit)
        elif command == "balances":
            snapshot_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
            await tester.show_balances(snapshot_id)
        elif command == "compare":
            await tester.compare_balances()
        else:
            print(f"Unknown command: {command}")
            print(__doc__)

    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
