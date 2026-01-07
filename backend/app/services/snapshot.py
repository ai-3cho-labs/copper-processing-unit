"""
$COPPER Snapshot Service

Handles balance snapshot collection with RNG-based timing.
Target: 3-6 snapshots per day via 40% hourly probability.
"""

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, and_, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Snapshot, Balance, ExcludedWallet, SystemStats
from app.services.helius import get_helius_service
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class SnapshotService:
    """Service for managing balance snapshots."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.helius = get_helius_service()

    def should_take_snapshot(self) -> bool:
        """
        Determine if a snapshot should be taken this hour.

        Uses configurable probability (default 40%) to achieve
        approximately 3-6 snapshots per day.

        Returns:
            True if snapshot should be taken, False otherwise.
        """
        probability = settings.snapshot_probability
        roll = random.random()
        result = roll < probability

        logger.info(
            f"Snapshot RNG: roll={roll:.3f}, threshold={probability}, "
            f"taking_snapshot={result}"
        )
        return result

    async def take_snapshot(self) -> Optional[Snapshot]:
        """
        Take a balance snapshot of all token holders.

        Fetches current balances from Helius, filters excluded wallets,
        and stores the snapshot in the database.

        OPTIMIZED: Uses bulk insert for balance records.

        Returns:
            Snapshot object if successful, None otherwise.
        """
        try:
            # Fetch all token holders
            token_accounts = await self.helius.get_token_accounts()

            if not token_accounts:
                logger.warning("No token accounts found, skipping snapshot")
                return None

            # Get total supply
            total_supply = await self.helius.get_token_supply()

            # Get excluded wallets
            excluded_result = await self.db.execute(
                select(ExcludedWallet.wallet)
            )
            excluded_wallets = {row[0] for row in excluded_result.fetchall()}

            # Filter out excluded wallets
            valid_accounts = [
                acc for acc in token_accounts
                if acc.wallet not in excluded_wallets
            ]

            # Create snapshot
            snapshot = Snapshot(
                timestamp=utc_now(),
                total_holders=len(valid_accounts),
                total_supply=total_supply
            )
            self.db.add(snapshot)
            await self.db.flush()  # Get snapshot ID

            # BULK INSERT: Create all balance records at once
            if valid_accounts:
                balance_data = [
                    {
                        "snapshot_id": snapshot.id,
                        "wallet": account.wallet,
                        "balance": account.balance
                    }
                    for account in valid_accounts
                ]

                await self.db.execute(
                    insert(Balance),
                    balance_data
                )

            # Update system stats
            await self._update_system_stats(snapshot)

            await self.db.commit()

            logger.info(
                f"Snapshot taken: id={snapshot.id}, "
                f"holders={len(valid_accounts)}, supply={total_supply}"
            )
            return snapshot

        except Exception as e:
            logger.error(f"Error taking snapshot: {e}")
            await self.db.rollback()
            raise

    async def get_snapshot(self, snapshot_id: UUID) -> Optional[Snapshot]:
        """Get a snapshot by ID."""
        result = await self.db.execute(
            select(Snapshot).where(Snapshot.id == snapshot_id)
        )
        return result.scalar_one_or_none()

    async def get_latest_snapshot(self) -> Optional[Snapshot]:
        """Get the most recent snapshot."""
        result = await self.db.execute(
            select(Snapshot)
            .order_by(Snapshot.timestamp.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_snapshots_in_range(
        self,
        start: datetime,
        end: datetime
    ) -> list[Snapshot]:
        """Get all snapshots within a time range."""
        result = await self.db.execute(
            select(Snapshot)
            .where(and_(
                Snapshot.timestamp >= start,
                Snapshot.timestamp <= end
            ))
            .order_by(Snapshot.timestamp.asc())
        )
        return list(result.scalars().all())

    async def get_wallet_balances_in_range(
        self,
        wallet: str,
        start: datetime,
        end: datetime
    ) -> list[tuple[datetime, int]]:
        """Get all balance records for a wallet within a time range."""
        result = await self.db.execute(
            select(Snapshot.timestamp, Balance.balance)
            .join(Balance, Balance.snapshot_id == Snapshot.id)
            .where(and_(
                Balance.wallet == wallet,
                Snapshot.timestamp >= start,
                Snapshot.timestamp <= end
            ))
            .order_by(Snapshot.timestamp.asc())
        )
        return [(row[0], row[1]) for row in result.fetchall()]

    async def get_snapshot_count(self, hours: int = 24) -> int:
        """Get number of snapshots taken in the last N hours."""
        cutoff = utc_now() - timedelta(hours=hours)
        result = await self.db.execute(
            select(func.count(Snapshot.id))
            .where(Snapshot.timestamp >= cutoff)
        )
        return result.scalar_one()

    async def interpolate_balance(
        self,
        wallet: str,
        target_time: datetime,
        snapshots: list[Snapshot]
    ) -> int:
        """
        Interpolate wallet balance at a specific time.

        Used when snapshots are missing (e.g., outage).
        """
        if not snapshots:
            return 0

        # Find surrounding snapshots
        before = None
        after = None

        for snapshot in snapshots:
            if snapshot.timestamp <= target_time:
                before = snapshot
            elif after is None:
                after = snapshot
                break

        # Get balances for surrounding snapshots
        before_balance = 0
        after_balance = 0

        if before:
            result = await self.db.execute(
                select(Balance.balance)
                .where(and_(
                    Balance.snapshot_id == before.id,
                    Balance.wallet == wallet
                ))
            )
            before_balance = result.scalar_one_or_none() or 0

        if after:
            result = await self.db.execute(
                select(Balance.balance)
                .where(and_(
                    Balance.snapshot_id == after.id,
                    Balance.wallet == wallet
                ))
            )
            after_balance = result.scalar_one_or_none() or 0

        # If only one snapshot, return its balance
        if before and not after:
            return before_balance
        if after and not before:
            return after_balance

        # Linear interpolation
        if before and after:
            time_range = (after.timestamp - before.timestamp).total_seconds()
            if time_range == 0:
                return before_balance

            progress = (target_time - before.timestamp).total_seconds() / time_range
            return int(before_balance + (after_balance - before_balance) * progress)

        return 0

    async def _update_system_stats(self, snapshot: Snapshot):
        """Update system stats with latest snapshot info."""
        result = await self.db.execute(
            select(SystemStats).where(SystemStats.id == 1)
        )
        stats = result.scalar_one_or_none()

        if stats:
            stats.total_holders = snapshot.total_holders
            stats.last_snapshot_at = snapshot.timestamp
            stats.updated_at = utc_now()
        else:
            stats = SystemStats(
                id=1,
                total_holders=snapshot.total_holders,
                last_snapshot_at=snapshot.timestamp
            )
            self.db.add(stats)

    async def add_excluded_wallet(self, wallet: str, reason: str) -> bool:
        """Add a wallet to the exclusion list."""
        try:
            excluded = ExcludedWallet(wallet=wallet, reason=reason)
            self.db.add(excluded)
            await self.db.commit()
            logger.info(f"Added excluded wallet: {wallet} ({reason})")
            return True
        except Exception as e:
            logger.error(f"Error adding excluded wallet: {e}")
            await self.db.rollback()
            return False

    async def remove_excluded_wallet(self, wallet: str) -> bool:
        """Remove a wallet from the exclusion list."""
        result = await self.db.execute(
            select(ExcludedWallet).where(ExcludedWallet.wallet == wallet)
        )
        excluded = result.scalar_one_or_none()

        if excluded:
            await self.db.delete(excluded)
            await self.db.commit()
            logger.info(f"Removed excluded wallet: {wallet}")
            return True

        return False

    async def get_excluded_wallets(self) -> list[ExcludedWallet]:
        """Get all excluded wallets."""
        result = await self.db.execute(
            select(ExcludedWallet).order_by(ExcludedWallet.added_at.desc())
        )
        return list(result.scalars().all())
