#!/usr/bin/env python3
"""Verify database contents after snapshot - standalone version."""

import asyncio
import uuid
from datetime import datetime

from sqlalchemy import String, Integer, BigInteger, DateTime, select, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column, DeclarativeBase


# Standalone model definitions
class Base(DeclarativeBase):
    pass


class Snapshot(Base):
    __tablename__ = "snapshots"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    total_holders: Mapped[int] = mapped_column(Integer)
    total_supply: Mapped[int] = mapped_column(BigInteger)


class Balance(Base):
    __tablename__ = "balances"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("snapshots.id"))
    wallet: Mapped[str] = mapped_column(String(44))
    balance: Mapped[int] = mapped_column(BigInteger)


class HoldStreak(Base):
    __tablename__ = "hold_streaks"
    wallet: Mapped[str] = mapped_column(String(44), primary_key=True)
    streak_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_tier: Mapped[int] = mapped_column(Integer)


DATABASE_URL = 'postgresql+asyncpg://neondb_owner:npg_JGm7BUDuO9kY@ep-wandering-firefly-a4uhb6aw-pooler.us-east-1.aws.neon.tech/neondb?ssl=require'


async def verify():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

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

        print(f'=== Latest Snapshot ===')
        print(f'ID: {snapshot.id}')
        print(f'Timestamp: {snapshot.timestamp}')
        print(f'Total holders: {snapshot.total_holders}')
        print(f'Total supply: {snapshot.total_supply:,}')
        print()

        # Get balances for this snapshot
        result = await session.execute(
            select(Balance)
            .where(Balance.snapshot_id == snapshot.id)
            .order_by(Balance.balance.desc())
        )
        balances = result.scalars().all()

        print(f'=== Balances ({len(balances)} wallets) ===')
        for b in balances:
            tokens = b.balance / 1e9
            print(f'  {b.wallet[:12]}... : {tokens:,.0f} tokens')
        print()

        # Check streaks
        result = await session.execute(select(HoldStreak))
        streaks = result.scalars().all()
        print(f'=== Hold Streaks ({len(streaks)}) ===')
        for s in streaks:
            print(f'  {s.wallet[:12]}... : Tier {s.current_tier}, started {s.streak_start}')

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(verify())
