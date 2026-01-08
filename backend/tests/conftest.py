"""
$COPPER Backend Test Configuration

Pytest fixtures and configuration for testing.
"""

import asyncio
import uuid
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio
from sqlalchemy import event, String, TypeDecorator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.database import Base
from app.models import Snapshot, Balance, HoldStreak, Distribution, DistributionRecipient
from app.config import Settings


# Test database URL (in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# UUID compatibility for SQLite
class UUIDString(TypeDecorator):
    """Platform-independent UUID type that stores as String for SQLite."""
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return uuid.UUID(value)
        return value


def adapt_uuid_columns_for_sqlite():
    """Modify UUID columns to use String for SQLite compatibility."""
    from sqlalchemy import inspect

    for mapper in Base.registry.mappers:
        for column in mapper.columns:
            if isinstance(column.type, PG_UUID):
                column.type = UUIDString()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    """Create test database engine."""
    # Adapt UUID columns for SQLite before creating tables
    adapt_uuid_columns_for_sqlite()

    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.test_mode = False
    settings.is_production = False
    settings.is_devnet = True
    settings.copper_token_mint = "TestTokenMint111111111111111111111111111"
    settings.team_wallet_public_key = "TestTeamWallet1111111111111111111111111"
    settings.creator_wallet_private_key = "TestPrivateKey111111111111111111111111111111111111111111111111111111"
    settings.airdrop_pool_private_key = "TestPoolKey1111111111111111111111111111111111111111111111111111111"
    settings.helius_api_key = "test-api-key"
    settings.helius_rpc_url = "https://devnet.helius-rpc.com"
    settings.distribution_threshold_usd = Decimal("250")
    settings.distribution_max_hours = 24
    settings.min_balance_usd = Decimal("50")
    settings.redis_url = None
    settings.sentry_dsn = None
    return settings


@pytest.fixture
def sample_snapshot_data():
    """Generate sample snapshot data for testing."""
    now = datetime.now(timezone.utc)
    return {
        "timestamp": now,
        "total_holders": 100,  # Correct column name
        "total_supply": 1_000_000_000_000_000,  # 1M tokens with 9 decimals
    }


@pytest.fixture
def sample_balances():
    """Generate sample balance data for testing."""
    return [
        {"wallet": "11111111111111111111111111111111111111111111", "balance": 100_000_000_000},  # 100 tokens
        {"wallet": "22222222222222222222222222222222222222222222", "balance": 50_000_000_000},   # 50 tokens
        {"wallet": "33333333333333333333333333333333333333333333", "balance": 25_000_000_000},   # 25 tokens
    ]


@pytest.fixture
def sample_streaks():
    """Generate sample hold streak data for testing."""
    now = datetime.now(timezone.utc)
    return [
        {"wallet": "11111111111111111111111111111111111111111111", "current_tier": 3, "streak_start": now - timedelta(hours=24)},
        {"wallet": "22222222222222222222222222222222222222222222", "current_tier": 2, "streak_start": now - timedelta(hours=12)},
        {"wallet": "33333333333333333333333333333333333333333333", "current_tier": 1, "streak_start": now - timedelta(hours=1)},
    ]


@pytest_asyncio.fixture
async def populated_db(db_session, sample_snapshot_data, sample_balances, sample_streaks):
    """Populate database with sample data for testing."""
    now = datetime.now(timezone.utc)

    # Create snapshots
    for i in range(3):
        snapshot = Snapshot(
            timestamp=now - timedelta(hours=i * 8),
            total_holders=100 - i * 5,
            total_supply=1_000_000_000_000_000
        )
        db_session.add(snapshot)
        await db_session.flush()

        # Add balances for each snapshot
        for bal_data in sample_balances:
            balance = Balance(
                snapshot_id=snapshot.id,
                wallet=bal_data["wallet"],
                balance=bal_data["balance"]
            )
            db_session.add(balance)

    # Add streaks
    for streak_data in sample_streaks:
        streak = HoldStreak(
            wallet=streak_data["wallet"],
            current_tier=streak_data["current_tier"],
            streak_start=streak_data["streak_start"]
        )
        db_session.add(streak)

    await db_session.commit()

    return db_session


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)
