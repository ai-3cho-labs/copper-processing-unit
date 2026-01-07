"""
$COPPER Streak Service

Tracks holding streaks and tier multipliers.
Sells drop tier by one and reset streak to that tier's minimum.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HoldStreak
from app.config import TIER_CONFIG, TIER_THRESHOLDS

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


@dataclass
class StreakInfo:
    """Complete streak information for a wallet."""
    wallet: str
    tier: int
    tier_name: str
    tier_emoji: str
    multiplier: float
    streak_hours: float
    streak_start: datetime
    next_tier: Optional[int]
    next_tier_name: Optional[str]
    hours_to_next_tier: Optional[float]
    last_sell_at: Optional[datetime]


class StreakService:
    """Service for managing holding streaks and tiers."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_streak(self, wallet: str) -> Optional[HoldStreak]:
        """
        Get streak record for a wallet.

        Args:
            wallet: Wallet address.

        Returns:
            HoldStreak record if exists, None otherwise.
        """
        result = await self.db.execute(
            select(HoldStreak).where(HoldStreak.wallet == wallet)
        )
        return result.scalar_one_or_none()

    async def get_streak_info(self, wallet: str) -> Optional[StreakInfo]:
        """
        Get complete streak information for a wallet.

        Args:
            wallet: Wallet address.

        Returns:
            StreakInfo with tier, multiplier, and progress info.
        """
        streak = await self.get_streak(wallet)

        if not streak:
            return None

        # Calculate streak duration
        now = utc_now()
        streak_duration = now - streak.streak_start
        streak_hours = streak_duration.total_seconds() / 3600

        # Get tier info
        tier = streak.current_tier
        tier_info = TIER_CONFIG[tier]

        # Calculate next tier progress
        next_tier = tier + 1 if tier < 6 else None
        next_tier_name = TIER_CONFIG[next_tier]["name"] if next_tier else None
        hours_to_next = None

        if next_tier:
            next_threshold = TIER_THRESHOLDS[next_tier]
            hours_to_next = max(0, next_threshold - streak_hours)

        return StreakInfo(
            wallet=wallet,
            tier=tier,
            tier_name=tier_info["name"],
            tier_emoji=tier_info["emoji"],
            multiplier=tier_info["multiplier"],
            streak_hours=streak_hours,
            streak_start=streak.streak_start,
            next_tier=next_tier,
            next_tier_name=next_tier_name,
            hours_to_next_tier=hours_to_next,
            last_sell_at=streak.last_sell_at
        )

    async def start_streak(self, wallet: str) -> HoldStreak:
        """
        Start a new streak for a wallet (first-time holder).

        Args:
            wallet: Wallet address.

        Returns:
            Created HoldStreak record.
        """
        streak = HoldStreak(
            wallet=wallet,
            streak_start=utc_now(),
            current_tier=1
        )
        self.db.add(streak)
        await self.db.commit()

        logger.info(f"Started new streak for wallet: {wallet}")
        return streak

    async def get_or_create_streak(self, wallet: str) -> HoldStreak:
        """
        Get existing streak or create a new one.

        Args:
            wallet: Wallet address.

        Returns:
            HoldStreak record.
        """
        streak = await self.get_streak(wallet)
        if not streak:
            streak = await self.start_streak(wallet)
        return streak

    async def process_sell(self, wallet: str) -> Optional[HoldStreak]:
        """
        Process a sell event for a wallet.

        Drops tier by one (minimum tier 1) and resets streak
        to that tier's minimum hours.

        Args:
            wallet: Wallet address that sold.

        Returns:
            Updated HoldStreak record, or None if wallet has no streak.
        """
        streak = await self.get_streak(wallet)

        if not streak:
            logger.warning(f"Sell detected for unknown wallet: {wallet}")
            return None

        old_tier = streak.current_tier
        now = utc_now()

        # Drop tier by one (minimum 1)
        new_tier = max(1, old_tier - 1)

        # Reset streak to new tier's minimum hours
        new_tier_min_hours = TIER_THRESHOLDS[new_tier]
        new_streak_start = now - timedelta(hours=new_tier_min_hours)

        streak.current_tier = new_tier
        streak.streak_start = new_streak_start
        streak.last_sell_at = now
        streak.updated_at = now

        await self.db.commit()

        logger.info(
            f"Processed sell for {wallet}: "
            f"tier {old_tier} → {new_tier}, "
            f"streak reset to {new_tier_min_hours}h"
        )
        return streak

    def get_multiplier(self, tier: int) -> float:
        """
        Get multiplier for a tier.

        Args:
            tier: Tier number (1-6).

        Returns:
            Multiplier value.
        """
        if tier < 1 or tier > 6:
            tier = 1
        return TIER_CONFIG[tier]["multiplier"]

    async def get_wallet_multiplier(self, wallet: str) -> float:
        """
        Get current multiplier for a wallet.

        Args:
            wallet: Wallet address.

        Returns:
            Multiplier value (1.0 if no streak exists).
        """
        streak = await self.get_streak(wallet)
        if not streak:
            return 1.0
        return self.get_multiplier(streak.current_tier)

    def get_tier_name(self, tier: int) -> str:
        """
        Get name for a tier.

        Args:
            tier: Tier number (1-6).

        Returns:
            Tier name.
        """
        if tier < 1 or tier > 6:
            tier = 1
        return TIER_CONFIG[tier]["name"]

    def get_tier_emoji(self, tier: int) -> str:
        """
        Get emoji for a tier.

        Args:
            tier: Tier number (1-6).

        Returns:
            Tier emoji.
        """
        if tier < 1 or tier > 6:
            tier = 1
        return TIER_CONFIG[tier]["emoji"]

    def calculate_tier_from_hours(self, hours: float) -> int:
        """
        Calculate tier based on streak hours.

        Args:
            hours: Total hours held.

        Returns:
            Tier number (1-6).
        """
        tier = 1
        for t, min_hours in TIER_THRESHOLDS.items():
            if hours >= min_hours:
                tier = t
        return tier

    async def update_tier_if_needed(self, wallet: str) -> Optional[HoldStreak]:
        """
        Check and update tier based on current streak duration.

        Should be called periodically or before calculations.

        Args:
            wallet: Wallet address.

        Returns:
            Updated HoldStreak if tier changed, None otherwise.
        """
        streak = await self.get_streak(wallet)
        if not streak:
            return None

        # Calculate current streak hours
        now = utc_now()
        streak_hours = (now - streak.streak_start).total_seconds() / 3600

        # Calculate what tier should be
        calculated_tier = self.calculate_tier_from_hours(streak_hours)

        # Only upgrade, never downgrade (downgrades happen via sells)
        if calculated_tier > streak.current_tier:
            old_tier = streak.current_tier
            streak.current_tier = calculated_tier
            streak.updated_at = now
            await self.db.commit()

            logger.info(
                f"Tier upgrade for {wallet}: "
                f"{old_tier} → {calculated_tier} "
                f"(after {streak_hours:.1f}h)"
            )
            return streak

        return None

    async def get_all_streaks(self, min_tier: int = 1) -> list[HoldStreak]:
        """
        Get all streaks, optionally filtered by minimum tier.

        Args:
            min_tier: Minimum tier to include.

        Returns:
            List of HoldStreak records.
        """
        result = await self.db.execute(
            select(HoldStreak)
            .where(HoldStreak.current_tier >= min_tier)
            .order_by(HoldStreak.current_tier.desc())
        )
        return list(result.scalars().all())

    async def get_tier_distribution(self) -> dict[int, int]:
        """
        Get count of wallets in each tier.

        Returns:
            Dict mapping tier number to wallet count.
        """
        result = await self.db.execute(
            select(HoldStreak.current_tier, HoldStreak.wallet)
        )
        rows = result.fetchall()

        distribution = {i: 0 for i in range(1, 7)}
        for row in rows:
            tier = row[0]
            distribution[tier] = distribution.get(tier, 0) + 1

        return distribution
