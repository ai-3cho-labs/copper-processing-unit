#!/usr/bin/env python3
"""Initialize hold streaks for all snapshot holders."""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import String, Integer, BigInteger, DateTime, select, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column, DeclarativeBase


# Standalone model definitions
class Base(DeclarativeBase):
    pass


class Balance(Base):
    __tablename__ = "balances"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    wallet: Mapped[str] = mapped_column(String(44))
    balance: Mapped[int] = mapped_column(BigInteger)


class Snapshot(Base):
    __tablename__ = "snapshots"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    total_holders: Mapped[int] = mapped_column(Integer)


class HoldStreak(Base):
    __tablename__ = "hold_streaks"
    wallet: Mapped[str] = mapped_column(String(44), primary_key=True)
    streak_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_tier: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_sell_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


DATABASE_URL = 'postgresql+asyncpg://neondb_owner:npg_JGm7BUDuO9kY@ep-wandering-firefly-a4uhb6aw-pooler.us-east-1.aws.neon.tech/neondb?ssl=require'

# Tier configuration matching the app
TIER_THRESHOLDS = {
    1: 0,      # Ore: 0h
    2: 24,     # Coal: 24h
    3: 72,     # Iron: 72h (3 days)
    4: 168,    # Gold: 168h (7 days)
    5: 336,    # Platinum: 336h (14 days)
    6: 720,    # Diamond: 720h (30 days)
}


async def init_streaks():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    now = datetime.now(timezone.utc)

    async with async_session() as session:
        # Get latest snapshot
        result = await session.execute(
            select(Snapshot).order_by(Snapshot.timestamp.desc()).limit(1)
        )
        snapshot = result.scalar_one_or_none()

        if not snapshot:
            print('No snapshots found')
            await engine.dispose()
            return

        # Get all wallets from snapshot
        result = await session.execute(
            select(Balance.wallet).where(Balance.snapshot_id == snapshot.id)
        )
        wallets = [row[0] for row in result.fetchall()]

        print(f'Found {len(wallets)} wallets in snapshot')
        print()

        # Create/update streaks for each wallet
        created = 0
        updated = 0

        for i, wallet in enumerate(wallets):
            # Check if streak exists
            result = await session.execute(
                select(HoldStreak).where(HoldStreak.wallet == wallet)
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f'  [{i+1}] {wallet[:16]}... already has streak (Tier {existing.current_tier})')
                updated += 1
            else:
                # Create new streak - start time varies to test different tiers
                # Vary start times: holder-1 gets longer streak, holder-5 gets shortest
                hours_ago = max(1, (len(wallets) - i) * 24)  # 24h, 48h, 72h, etc.

                streak = HoldStreak(
                    wallet=wallet,
                    streak_start=now - timedelta(hours=hours_ago),
                    current_tier=1,  # Start at tier 1
                    updated_at=now
                )
                session.add(streak)
                created += 1
                print(f'  [{i+1}] {wallet[:16]}... created streak ({hours_ago}h ago)')

        await session.commit()
        print()
        print(f'Created {created} new streaks, {updated} already existed')

        # Now update tiers based on streak duration
        print()
        print('Updating tiers based on streak duration...')

        result = await session.execute(select(HoldStreak))
        all_streaks = result.scalars().all()

        for streak in all_streaks:
            streak_hours = (now - streak.streak_start).total_seconds() / 3600

            # Calculate tier
            tier = 1
            for t, min_hours in sorted(TIER_THRESHOLDS.items()):
                if streak_hours >= min_hours:
                    tier = t

            if tier != streak.current_tier:
                old_tier = streak.current_tier
                streak.current_tier = tier
                streak.updated_at = now
                print(f'  {streak.wallet[:16]}... upgraded Tier {old_tier} -> {tier} ({streak_hours:.1f}h)')

        await session.commit()

        # Final status
        print()
        print('=== Final Streak Status ===')
        result = await session.execute(
            select(HoldStreak).order_by(HoldStreak.current_tier.desc())
        )
        all_streaks = result.scalars().all()

        for streak in all_streaks:
            hours = (now - streak.streak_start).total_seconds() / 3600
            print(f'  {streak.wallet[:16]}... : Tier {streak.current_tier} ({hours:.1f}h)')

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_streaks())
