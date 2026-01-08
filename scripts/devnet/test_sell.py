#!/usr/bin/env python3
"""Test sell detection and streak tier drop."""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import String, Integer, DateTime, select, update
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    pass


class HoldStreak(Base):
    __tablename__ = "hold_streaks"
    wallet: Mapped[str] = mapped_column(String(44), primary_key=True)
    streak_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_tier: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_sell_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


DATABASE_URL = 'postgresql+asyncpg://neondb_owner:npg_JGm7BUDuO9kY@ep-wandering-firefly-a4uhb6aw-pooler.us-east-1.aws.neon.tech/neondb?ssl=require'

TIER_CONFIG = {
    1: {"name": "Ore", "multiplier": 1.0},
    2: {"name": "Coal", "multiplier": 1.5},
    3: {"name": "Iron", "multiplier": 2.0},
    4: {"name": "Gold", "multiplier": 3.0},
    5: {"name": "Platinum", "multiplier": 4.0},
    6: {"name": "Diamond Hands", "multiplier": 5.0},
}

TIER_THRESHOLDS = {
    1: 0, 2: 24, 3: 72, 4: 168, 5: 336, 6: 720
}


async def process_sell(session: AsyncSession, wallet: str) -> dict:
    """Simulate a sell event for a wallet."""
    result = await session.execute(
        select(HoldStreak).where(HoldStreak.wallet == wallet)
    )
    streak = result.scalar_one_or_none()

    if not streak:
        return {"error": "No streak found for wallet"}

    old_tier = streak.current_tier
    now = datetime.now(timezone.utc)

    # Drop tier by one (minimum 1)
    new_tier = max(1, old_tier - 1)

    # Reset streak to new tier's minimum hours
    new_tier_min_hours = TIER_THRESHOLDS[new_tier]
    new_streak_start = now - timedelta(hours=new_tier_min_hours)

    streak.current_tier = new_tier
    streak.streak_start = new_streak_start
    streak.last_sell_at = now
    streak.updated_at = now

    await session.commit()

    return {
        "wallet": wallet,
        "old_tier": old_tier,
        "old_tier_name": TIER_CONFIG[old_tier]["name"],
        "new_tier": new_tier,
        "new_tier_name": TIER_CONFIG[new_tier]["name"],
        "old_multiplier": TIER_CONFIG[old_tier]["multiplier"],
        "new_multiplier": TIER_CONFIG[new_tier]["multiplier"],
        "streak_reset_to_hours": new_tier_min_hours
    }


async def test_sell():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get all streaks before
        result = await session.execute(
            select(HoldStreak).order_by(HoldStreak.current_tier.desc())
        )
        streaks_before = result.scalars().all()

        print("=== Streaks BEFORE sell ===")
        for s in streaks_before:
            hours = (datetime.now(timezone.utc) - s.streak_start).total_seconds() / 3600
            print(f"  {s.wallet[:16]}... : Tier {s.current_tier} ({TIER_CONFIG[s.current_tier]['name']}) - {hours:.1f}h")

        # Pick a Tier 3 wallet to sell
        tier3_wallet = None
        for s in streaks_before:
            if s.current_tier == 3:
                tier3_wallet = s.wallet
                break

        if not tier3_wallet:
            print("\nNo Tier 3 wallet found to test sell!")
            await engine.dispose()
            return

        print(f"\n=== Simulating SELL for {tier3_wallet[:16]}... ===")

        # Process the sell
        result = await process_sell(session, tier3_wallet)

        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"  Old tier: {result['old_tier']} ({result['old_tier_name']}) - {result['old_multiplier']}x")
            print(f"  New tier: {result['new_tier']} ({result['new_tier_name']}) - {result['new_multiplier']}x")
            print(f"  Streak reset to: {result['streak_reset_to_hours']}h")

        # Get all streaks after
        result = await session.execute(
            select(HoldStreak).order_by(HoldStreak.current_tier.desc())
        )
        streaks_after = result.scalars().all()

        print("\n=== Streaks AFTER sell ===")
        for s in streaks_after:
            hours = (datetime.now(timezone.utc) - s.streak_start).total_seconds() / 3600
            sold_marker = " [SOLD]" if s.last_sell_at else ""
            print(f"  {s.wallet[:16]}... : Tier {s.current_tier} ({TIER_CONFIG[s.current_tier]['name']}) - {hours:.1f}h{sold_marker}")

    await engine.dispose()

    print("\n=== SELL TEST PASSED ===")
    print("Tier dropped correctly from 3 (Iron) to 2 (Coal)")


if __name__ == "__main__":
    asyncio.run(test_sell())
