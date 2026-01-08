#!/usr/bin/env python3
"""Simple standalone distribution test using correct field names."""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from collections import defaultdict
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import String, Integer, BigInteger, DateTime, Numeric, select, and_, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    pass


class Snapshot(Base):
    __tablename__ = "snapshots"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # Correct field name
    total_holders: Mapped[int] = mapped_column(Integer)
    total_supply: Mapped[int] = mapped_column(BigInteger)


class Balance(Base):
    __tablename__ = "balances"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    wallet: Mapped[str] = mapped_column(String(44))  # Correct field name
    balance: Mapped[int] = mapped_column(BigInteger)


class HoldStreak(Base):
    __tablename__ = "hold_streaks"
    wallet: Mapped[str] = mapped_column(String(44), primary_key=True)
    streak_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_tier: Mapped[int] = mapped_column(Integer)


class Distribution(Base):
    __tablename__ = "distributions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pool_amount: Mapped[int] = mapped_column(BigInteger)
    pool_value_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    total_hashpower: Mapped[Decimal] = mapped_column(Numeric(24, 2))
    recipient_count: Mapped[int] = mapped_column(Integer)
    trigger_type: Mapped[str] = mapped_column(String(20))
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class DistributionRecipient(Base):
    __tablename__ = "distribution_recipients"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    distribution_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("distributions.id"))
    wallet: Mapped[str] = mapped_column(String(44))
    twab: Mapped[int] = mapped_column(BigInteger)
    multiplier: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    hash_power: Mapped[Decimal] = mapped_column(Numeric(24, 2))
    amount_received: Mapped[int] = mapped_column(BigInteger)
    tx_signature: Mapped[Optional[str]] = mapped_column(String(88), nullable=True)


DATABASE_URL = 'postgresql+asyncpg://neondb_owner:npg_JGm7BUDuO9kY@ep-wandering-firefly-a4uhb6aw-pooler.us-east-1.aws.neon.tech/neondb?ssl=require'

TIER_CONFIG = {
    1: {"name": "Ore", "multiplier": 1.0},
    2: {"name": "Coal", "multiplier": 1.5},
    3: {"name": "Iron", "multiplier": 2.0},
    4: {"name": "Gold", "multiplier": 3.0},
    5: {"name": "Platinum", "multiplier": 4.0},
    6: {"name": "Diamond Hands", "multiplier": 5.0},
}


@dataclass
class HashPowerInfo:
    wallet: str
    twab: int
    multiplier: float
    hash_power: Decimal
    tier: int
    tier_name: str


@dataclass
class RecipientShare:
    wallet: str
    twab: int
    multiplier: float
    hash_power: Decimal
    share_percentage: Decimal
    amount: int


def compute_twab(balances: list[tuple[datetime, int]], start: datetime, end: datetime) -> int:
    """Compute TWAB from balance snapshots."""
    if not balances:
        return 0

    total_duration = (end - start).total_seconds()
    if total_duration <= 0:
        return 0

    if len(balances) == 1:
        return balances[0][1]

    weighted_sum = Decimal(0)

    for i in range(len(balances)):
        timestamp, balance = balances[i]

        if i == 0:
            seg_start = start
            if len(balances) > 1:
                next_time = balances[i + 1][0]
                seg_end = timestamp + (next_time - timestamp) / 2
            else:
                seg_end = end
        elif i == len(balances) - 1:
            prev_time = balances[i - 1][0]
            seg_start = prev_time + (timestamp - prev_time) / 2
            seg_end = end
        else:
            prev_time = balances[i - 1][0]
            next_time = balances[i + 1][0]
            seg_start = prev_time + (timestamp - prev_time) / 2
            seg_end = timestamp + (next_time - timestamp) / 2

        seg_start = max(seg_start, start)
        seg_end = min(seg_end, end)

        duration = (seg_end - seg_start).total_seconds()
        if duration > 0:
            weighted_sum += Decimal(balance) * Decimal(duration)

    twab = weighted_sum / Decimal(total_duration)
    return int(twab)


async def calculate_all_hash_powers(session: AsyncSession, start: datetime, end: datetime) -> list[HashPowerInfo]:
    """Calculate hash power for all wallets."""
    # Get all balances using correct field names
    result = await session.execute(
        select(Balance.wallet, Snapshot.timestamp, Balance.balance)
        .join(Snapshot, Balance.snapshot_id == Snapshot.id)
        .where(and_(
            Snapshot.timestamp >= start,
            Snapshot.timestamp <= end
        ))
        .order_by(Balance.wallet, Snapshot.timestamp.asc())
    )
    all_balances = result.fetchall()

    if not all_balances:
        return []

    # Group balances by wallet
    wallet_balances: dict[str, list[tuple[datetime, int]]] = defaultdict(list)
    for wallet, timestamp, balance in all_balances:
        wallet_balances[wallet].append((timestamp, balance))

    # Get all streaks
    wallets_list = list(wallet_balances.keys())
    result = await session.execute(
        select(HoldStreak.wallet, HoldStreak.current_tier)
        .where(HoldStreak.wallet.in_(wallets_list))
    )
    wallet_tiers = {row[0]: row[1] for row in result.fetchall()}

    # Calculate hash powers
    hash_powers = []
    for wallet, balances in wallet_balances.items():
        twab = compute_twab(balances, start, end)
        if twab == 0:
            continue

        tier = wallet_tiers.get(wallet, 1)
        multiplier = TIER_CONFIG[tier]["multiplier"]
        tier_name = TIER_CONFIG[tier]["name"]
        hash_power = Decimal(twab) * Decimal(str(multiplier))

        hash_powers.append(HashPowerInfo(
            wallet=wallet,
            twab=twab,
            multiplier=multiplier,
            hash_power=hash_power,
            tier=tier,
            tier_name=tier_name
        ))

    hash_powers.sort(key=lambda x: x.hash_power, reverse=True)
    return hash_powers


async def test_distribution():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    now = datetime.now(timezone.utc)

    # Test pool: 1,000,000 tokens (in raw units with 9 decimals)
    POOL_AMOUNT = 1_000_000 * 10**9  # 1M tokens

    async with async_session() as session:
        # Calculate period (last 48h to capture our snapshot)
        end = now
        start = end - timedelta(hours=48)

        print("=== Distribution Test ===")
        print(f"Pool: 1,000,000 COPPER")
        print(f"Period: {start.strftime('%Y-%m-%d %H:%M')} to {end.strftime('%Y-%m-%d %H:%M')}")
        print()

        # Calculate hash powers
        hash_powers = await calculate_all_hash_powers(session, start, end)

        if not hash_powers:
            print("No eligible wallets found!")
            print("Make sure you have run a snapshot first.")
            await engine.dispose()
            return

        total_hp = sum(hp.hash_power for hp in hash_powers)
        print(f"Eligible wallets: {len(hash_powers)}")
        print(f"Total Hash Power: {total_hp:,.0f}")
        print()

        # Calculate shares
        print("=== Distribution Plan ===")
        recipients = []
        for hp in hash_powers:
            share_pct = hp.hash_power / total_hp
            amount = int(Decimal(POOL_AMOUNT) * share_pct)
            amount_tokens = amount / 10**9

            recipients.append(RecipientShare(
                wallet=hp.wallet,
                twab=hp.twab,
                multiplier=hp.multiplier,
                hash_power=hp.hash_power,
                share_percentage=share_pct * 100,
                amount=amount
            ))

            twab_tokens = hp.twab / 10**9
            print(f"  {hp.wallet[:16]}...")
            print(f"    Tier: {hp.tier} ({hp.tier_name}) - {hp.multiplier}x")
            print(f"    TWAB: {twab_tokens:,.0f} tokens")
            print(f"    Hash Power: {hp.hash_power:,.0f}")
            print(f"    Share: {share_pct * 100:.2f}% = {amount_tokens:,.0f} COPPER")
            print()

        # Execute distribution (record to database)
        print("=== Recording Distribution ===")

        distribution = Distribution(
            id=uuid.uuid4(),
            pool_amount=POOL_AMOUNT,
            pool_value_usd=Decimal("100.00"),  # Mock value
            total_hashpower=total_hp,
            recipient_count=len(recipients),
            trigger_type="time",  # 24h trigger
            executed_at=now,
            created_at=now
        )
        session.add(distribution)
        await session.flush()

        # Create recipient records
        for r in recipients:
            recipient = DistributionRecipient(
                id=uuid.uuid4(),
                distribution_id=distribution.id,
                wallet=r.wallet,
                twab=r.twab,
                multiplier=Decimal(str(r.multiplier)),
                hash_power=r.hash_power,
                amount_received=r.amount,
                tx_signature=None
            )
            session.add(recipient)

        await session.commit()

        print(f"Distribution ID: {distribution.id}")
        print(f"Recipients: {len(recipients)}")
        print(f"Pool: {POOL_AMOUNT / 10**9:,.0f} COPPER")
        print()

        # Verify distribution was saved
        result = await session.execute(
            select(Distribution).where(Distribution.id == distribution.id)
        )
        saved_dist = result.scalar_one_or_none()

        if saved_dist:
            print("=== DISTRIBUTION TEST PASSED ===")
            print(f"Distribution recorded: {saved_dist.id}")
            print(f"Total distributed: {saved_dist.pool_amount / 10**9:,.0f} COPPER to {saved_dist.recipient_count} recipients")
        else:
            print("ERROR: Distribution not saved!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_distribution())
