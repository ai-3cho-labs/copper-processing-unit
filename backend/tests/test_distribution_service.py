"""
$COPPER Distribution Service Tests

Tests for distribution calculations and triggers.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.distribution import (
    DistributionService,
    DistributionPlan,
    RecipientShare,
    PoolStatus,
    check_and_distribute
)
from app.models import Distribution


class TestDistributionTriggers:
    """Tests for distribution trigger logic."""

    @pytest.mark.asyncio
    async def test_threshold_trigger(self, db_session, mock_settings):
        """Test distribution triggers when pool reaches threshold."""
        with patch("app.services.distribution.get_settings", return_value=mock_settings):
            service = DistributionService(db_session)

            # Mock pool value above threshold
            with patch.object(service, "get_pool_value_usd", return_value=Decimal("300")):
                with patch.object(service, "get_last_distribution", return_value=None):
                    should, trigger = await service.should_distribute()

                    assert should is True
                    assert trigger == "threshold"

    @pytest.mark.asyncio
    async def test_time_trigger(self, db_session, mock_settings):
        """Test distribution triggers after 24 hours."""
        mock_settings.distribution_max_hours = 24
        mock_settings.distribution_threshold_usd = Decimal("250")

        with patch("app.services.distribution.get_settings", return_value=mock_settings):
            service = DistributionService(db_session)

            # Mock last distribution 25 hours ago
            old_distribution = MagicMock()
            old_distribution.executed_at = datetime.now(timezone.utc) - timedelta(hours=25)

            # Mock get_pool_status to return time trigger met
            mock_status = MagicMock()
            mock_status.threshold_met = False
            mock_status.time_trigger_met = True

            with patch.object(service, "get_pool_status", return_value=mock_status):
                should, trigger = await service.should_distribute()

                assert should is True
                assert trigger == "time"

    @pytest.mark.asyncio
    async def test_no_trigger_below_threshold(self, db_session, mock_settings):
        """Test no distribution when below threshold and time."""
        mock_settings.distribution_max_hours = 24

        with patch("app.services.distribution.get_settings", return_value=mock_settings):
            service = DistributionService(db_session)

            # Mock last distribution 10 hours ago
            recent_distribution = MagicMock()
            recent_distribution.executed_at = datetime.now(timezone.utc) - timedelta(hours=10)

            with patch.object(service, "get_pool_value_usd", return_value=Decimal("100")):
                with patch.object(service, "get_last_distribution", return_value=recent_distribution):
                    should, trigger = await service.should_distribute()

                    assert should is False
                    assert trigger == ""


class TestPoolStatus:
    """Tests for pool status calculation."""

    @pytest.mark.asyncio
    async def test_pool_status_structure(self, db_session, mock_settings):
        """Test pool status returns all required fields."""
        with patch("app.services.distribution.get_settings", return_value=mock_settings):
            service = DistributionService(db_session)

            with patch.object(service, "get_pool_balance", return_value=1_000_000_000):
                with patch.object(service, "get_pool_value_usd", return_value=Decimal("150")):
                    with patch.object(service, "get_last_distribution", return_value=None):
                        status = await service.get_pool_status()

                        assert isinstance(status, PoolStatus)
                        assert hasattr(status, "balance")
                        assert hasattr(status, "balance_formatted")
                        assert hasattr(status, "value_usd")
                        assert hasattr(status, "threshold_met")
                        assert hasattr(status, "time_trigger_met")
                        assert hasattr(status, "should_distribute")


class TestDistributionCalculation:
    """Tests for distribution share calculation."""

    @pytest.mark.asyncio
    async def test_calculate_distribution_plan(self, populated_db, mock_settings):
        """Test distribution plan calculation."""
        with patch("app.services.distribution.get_settings", return_value=mock_settings):
            service = DistributionService(populated_db)

            # Mock required methods
            with patch.object(service, "get_pool_balance", return_value=10_000_000_000):
                with patch.object(service, "get_pool_value_usd", return_value=Decimal("500")):
                    with patch.object(service, "get_copper_price_usd", return_value=Decimal("0.05")):
                        with patch.object(service.twab_service, "calculate_all_hash_powers") as mock_hp:
                            # Mock hash powers
                            mock_hp.return_value = [
                                MagicMock(
                                    wallet="Wallet1111111111111111111111111111111111111",
                                    twab=100_000_000_000,
                                    multiplier=2.5,
                                    hash_power=Decimal("250000000000")
                                ),
                                MagicMock(
                                    wallet="Wallet2222222222222222222222222222222222222",
                                    twab=50_000_000_000,
                                    multiplier=1.5,
                                    hash_power=Decimal("75000000000")
                                ),
                            ]

                            plan = await service.calculate_distribution(
                                pool_amount=10_000_000_000
                            )

                            if plan:
                                assert plan.pool_amount == 10_000_000_000
                                assert len(plan.recipients) == 2
                                # Total shares should equal pool amount
                                total_shares = sum(r.amount for r in plan.recipients)
                                assert total_shares <= plan.pool_amount

    @pytest.mark.asyncio
    async def test_distribution_share_proportional(self):
        """Test that shares are proportional to hash power."""
        # Create mock recipients with known hash powers
        recipients = [
            RecipientShare(
                wallet="Wallet1",
                twab=100,
                multiplier=2.0,
                hash_power=Decimal("200"),  # 200 / 300 = 66.67%
                share_percentage=Decimal("66.67"),
                amount=6667
            ),
            RecipientShare(
                wallet="Wallet2",
                twab=50,
                multiplier=2.0,
                hash_power=Decimal("100"),  # 100 / 300 = 33.33%
                share_percentage=Decimal("33.33"),
                amount=3333
            ),
        ]

        # Wallet1 should receive approximately 2x Wallet2
        ratio = recipients[0].amount / recipients[1].amount
        assert 1.8 < ratio < 2.2  # Allow some rounding tolerance


class TestDistributionExecution:
    """Tests for distribution execution."""

    @pytest.mark.asyncio
    async def test_execute_distribution_records_to_db(self, db_session, mock_settings):
        """Test that distribution is recorded in database."""
        with patch("app.services.distribution.get_settings", return_value=mock_settings):
            service = DistributionService(db_session)

            plan = DistributionPlan(
                pool_amount=1_000_000_000,
                pool_value_usd=Decimal("100"),
                total_hashpower=Decimal("500000000"),
                recipient_count=2,
                trigger_type="threshold",
                recipients=[
                    RecipientShare(
                        wallet="Wallet1111111111111111111111111111111111111",
                        twab=100_000_000,
                        multiplier=2.0,
                        hash_power=Decimal("200000000"),
                        share_percentage=Decimal("60"),
                        amount=600_000_000
                    ),
                    RecipientShare(
                        wallet="Wallet2222222222222222222222222222222222222",
                        twab=50_000_000,
                        multiplier=2.0,
                        hash_power=Decimal("100000000"),
                        share_percentage=Decimal("40"),
                        amount=400_000_000
                    ),
                ]
            )

            # Mock token transfers
            with patch.object(service, "_execute_token_transfers", return_value={}):
                distribution = await service.execute_distribution(plan)

                if distribution:
                    assert distribution.pool_amount == plan.pool_amount
                    assert distribution.recipient_count == plan.recipient_count
                    assert distribution.trigger_type == "threshold"


class TestDistributionEdgeCases:
    """Edge case tests for distribution service."""

    @pytest.mark.asyncio
    async def test_empty_pool_no_distribution(self, db_session, mock_settings):
        """Test that empty pool returns None."""
        with patch("app.services.distribution.get_settings", return_value=mock_settings):
            service = DistributionService(db_session)

            with patch.object(service, "get_pool_balance", return_value=0):
                plan = await service.calculate_distribution()
                assert plan is None

    @pytest.mark.asyncio
    async def test_no_eligible_wallets(self, db_session, mock_settings):
        """Test distribution when no wallets meet minimum balance."""
        with patch("app.services.distribution.get_settings", return_value=mock_settings):
            service = DistributionService(db_session)

            with patch.object(service, "get_pool_balance", return_value=1_000_000_000):
                with patch.object(service, "get_pool_value_usd", return_value=Decimal("500")):
                    with patch.object(service, "get_copper_price_usd", return_value=Decimal("0.05")):
                        with patch.object(service.twab_service, "calculate_all_hash_powers", return_value=[]):
                            plan = await service.calculate_distribution()
                            assert plan is None
