"""
$COPPER Sell Detection Tests

Tests for distinguishing DEX swaps (sells) from simple transfers,
and ensuring correct webhook transaction parsing.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app.services.helius import HeliusService, ParsedTransaction
from app.services.streak import StreakService
from app.models import HoldStreak
from app.config import SOL_MINT, USDC_MINT


# Sample token mint for testing
TEST_COPPER_MINT = "TestCopperMint1111111111111111111111111111"


class TestSellDetection:
    """Tests for sell detection logic."""

    @pytest.fixture
    def helius_service(self):
        """Create HeliusService with test config."""
        with patch("app.services.helius.settings") as mock_settings:
            mock_settings.helius_api_key = "test-key"
            mock_settings.copper_token_mint = TEST_COPPER_MINT
            service = HeliusService()
            service.token_mint = TEST_COPPER_MINT
            return service

    def test_detects_copper_to_sol_swap(self, helius_service):
        """Test detection of COPPER -> SOL swap (sell)."""
        payload = {
            "type": "SWAP",
            "signature": "5TBx...abc123",
            "feePayer": "SellerWallet111111111111111111111111111111",
            "tokenTransfers": [
                {
                    "mint": TEST_COPPER_MINT,
                    "fromUserAccount": "SellerWallet111111111111111111111111111111",
                    "toUserAccount": "DexPool1111111111111111111111111111111111",
                    "tokenAmount": 1000.0  # 1000 COPPER out
                }
            ],
            "nativeTransfers": [
                {
                    "fromUserAccount": "DexPool1111111111111111111111111111111111",
                    "toUserAccount": "SellerWallet111111111111111111111111111111",
                    "amount": 500000000  # 0.5 SOL in
                }
            ]
        }

        result = helius_service.parse_webhook_transaction(payload)

        assert result is not None
        assert result.is_sell is True
        assert result.source_wallet == "SellerWallet111111111111111111111111111111"
        assert result.token_out == TEST_COPPER_MINT
        assert result.token_in == SOL_MINT

    def test_detects_copper_to_usdc_swap(self, helius_service):
        """Test detection of COPPER -> USDC swap (sell)."""
        payload = {
            "type": "SWAP",
            "signature": "5TBx...def456",
            "feePayer": "SellerWallet222222222222222222222222222222",
            "tokenTransfers": [
                {
                    "mint": TEST_COPPER_MINT,
                    "fromUserAccount": "SellerWallet222222222222222222222222222222",
                    "toUserAccount": "DexPool2222222222222222222222222222222222",
                    "tokenAmount": 500.0  # 500 COPPER out
                },
                {
                    "mint": USDC_MINT,
                    "fromUserAccount": "DexPool2222222222222222222222222222222222",
                    "toUserAccount": "SellerWallet222222222222222222222222222222",
                    "tokenAmount": 25.0  # 25 USDC in
                }
            ],
            "nativeTransfers": []
        }

        result = helius_service.parse_webhook_transaction(payload)

        assert result is not None
        assert result.is_sell is True
        assert result.token_in == USDC_MINT

    def test_ignores_simple_transfer(self, helius_service):
        """Test that simple wallet-to-wallet transfer is NOT detected as sell."""
        payload = {
            "type": "TRANSFER",
            "signature": "5TBx...ghi789",
            "feePayer": "SenderWallet11111111111111111111111111111",
            "tokenTransfers": [
                {
                    "mint": TEST_COPPER_MINT,
                    "fromUserAccount": "SenderWallet11111111111111111111111111111",
                    "toUserAccount": "ReceiverWallet11111111111111111111111111",
                    "tokenAmount": 100.0  # Just a transfer, no swap
                }
            ],
            "nativeTransfers": []
        }

        result = helius_service.parse_webhook_transaction(payload)

        # Should NOT be detected as a sell (no SOL/USDC received in exchange)
        assert result is None or result.is_sell is False

    def test_ignores_incoming_transfer(self, helius_service):
        """Test that receiving COPPER is not detected as sell."""
        payload = {
            "type": "TRANSFER",
            "signature": "5TBx...jkl012",
            "feePayer": "SenderWallet22222222222222222222222222222",
            "tokenTransfers": [
                {
                    "mint": TEST_COPPER_MINT,
                    "fromUserAccount": "SenderWallet22222222222222222222222222222",
                    "toUserAccount": "ReceiverWallet22222222222222222222222222",
                    "tokenAmount": 200.0
                }
            ],
            "nativeTransfers": []
        }

        result = helius_service.parse_webhook_transaction(payload)

        # Receiver should not be flagged as seller
        if result:
            assert result.source_wallet != "ReceiverWallet22222222222222222222222222"

    def test_ignores_sol_to_copper_buy(self, helius_service):
        """Test that SOL -> COPPER swap (buy) is NOT detected as sell."""
        payload = {
            "type": "SWAP",
            "signature": "5TBx...mno345",
            "feePayer": "BuyerWallet1111111111111111111111111111111",
            "tokenTransfers": [
                {
                    "mint": TEST_COPPER_MINT,
                    "fromUserAccount": "DexPool3333333333333333333333333333333333",
                    "toUserAccount": "BuyerWallet1111111111111111111111111111111",
                    "tokenAmount": 1000.0  # Receiving COPPER
                }
            ],
            "nativeTransfers": [
                {
                    "fromUserAccount": "BuyerWallet1111111111111111111111111111111",
                    "toUserAccount": "DexPool3333333333333333333333333333333333",
                    "amount": 500000000  # Sending SOL
                }
            ]
        }

        result = helius_service.parse_webhook_transaction(payload)

        # Should NOT be a sell (wallet is buying, not selling)
        assert result is None or result.is_sell is False

    def test_handles_empty_token_transfers(self, helius_service):
        """Test handling of payload with empty token transfers."""
        payload = {
            "type": "TRANSFER",
            "signature": "5TBx...pqr678",
            "feePayer": "Wallet1111111111111111111111111111111111111",
            "tokenTransfers": [],
            "nativeTransfers": []
        }

        result = helius_service.parse_webhook_transaction(payload)
        assert result is None or result.is_sell is False

    def test_handles_malformed_payload(self, helius_service):
        """Test graceful handling of malformed payload."""
        # Missing required fields
        payload = {"random": "data"}

        result = helius_service.parse_webhook_transaction(payload)
        assert result is None

    def test_handles_null_amounts(self, helius_service):
        """Test handling of null/zero amounts."""
        payload = {
            "type": "SWAP",
            "signature": "5TBx...stu901",
            "feePayer": "Wallet2222222222222222222222222222222222222",
            "tokenTransfers": [
                {
                    "mint": TEST_COPPER_MINT,
                    "fromUserAccount": "Wallet2222222222222222222222222222222222222",
                    "toUserAccount": "DexPool4444444444444444444444444444444444",
                    "tokenAmount": 0  # Zero amount
                }
            ],
            "nativeTransfers": []
        }

        result = helius_service.parse_webhook_transaction(payload)
        # Zero amount should not trigger sell detection
        assert result is None or result.amount_out == 0


class TestTierDowngradeOnSell:
    """Tests for tier downgrade logic when sell detected."""

    @pytest.mark.asyncio
    async def test_sell_drops_tier_by_one(self, db_session):
        """Test that selling drops tier by exactly one level."""
        service = StreakService(db_session)

        # Patch WebSocket emitters to avoid errors
        with patch("app.services.streak.emit_sell_detected", return_value=None):
            with patch("app.services.streak.emit_tier_changed", return_value=None):
                for start_tier in range(2, 7):
                    wallet = f"Seller{start_tier}111111111111111111111111111111"

                    # Create streak at start_tier
                    streak = HoldStreak(
                        wallet=wallet,
                        current_tier=start_tier,
                        streak_start=datetime.now(timezone.utc) - timedelta(hours=100)
                    )
                    db_session.add(streak)
                    await db_session.commit()

                    # Process sell
                    result = await service.process_sell(wallet)

                    # Should drop exactly one tier
                    assert result.current_tier == start_tier - 1, \
                        f"Tier {start_tier} should drop to {start_tier - 1}, got {result.current_tier}"

    @pytest.mark.asyncio
    async def test_tier_1_cannot_drop_further(self, db_session):
        """Test that tier 1 is the minimum (cannot go to 0)."""
        service = StreakService(db_session)

        wallet = "MinTierWallet1111111111111111111111111111111"

        with patch("app.services.streak.emit_sell_detected", return_value=None):
            with patch("app.services.streak.emit_tier_changed", return_value=None):
                # Create at tier 1
                streak = HoldStreak(
                    wallet=wallet,
                    current_tier=1,
                    streak_start=datetime.now(timezone.utc) - timedelta(hours=5)
                )
                db_session.add(streak)
                await db_session.commit()

                # Process sell
                result = await service.process_sell(wallet)

                # Should stay at tier 1
                assert result.current_tier == 1

    @pytest.mark.asyncio
    async def test_streak_resets_to_new_tier_minimum(self, db_session):
        """Test that streak resets to the new tier's minimum hours."""
        from app.config import TIER_THRESHOLDS

        service = StreakService(db_session)
        wallet = "StreakResetWallet11111111111111111111111111"

        with patch("app.services.streak.emit_sell_detected", return_value=None):
            with patch("app.services.streak.emit_tier_changed", return_value=None):
                # Create at tier 4 (Industrial, min 72h)
                streak = HoldStreak(
                    wallet=wallet,
                    current_tier=4,
                    streak_start=datetime.now(timezone.utc) - timedelta(hours=100)
                )
                db_session.add(streak)
                await db_session.commit()

                # Process sell - should drop to tier 3
                result = await service.process_sell(wallet)

                # Calculate streak hours from streak_start
                now = datetime.now(timezone.utc)
                new_streak_hours = (now - result.streak_start).total_seconds() / 3600

                # Should be at tier 3 minimum (12 hours)
                tier_3_min = TIER_THRESHOLDS[3]
                assert abs(new_streak_hours - tier_3_min) < 0.1, \
                    f"Streak should reset to {tier_3_min}h, got {new_streak_hours:.2f}h"

    @pytest.mark.asyncio
    async def test_last_sell_timestamp_updated(self, db_session):
        """Test that last_sell_at is updated on sell."""
        service = StreakService(db_session)
        wallet = "LastSellWallet111111111111111111111111111111"

        with patch("app.services.streak.emit_sell_detected", return_value=None):
            with patch("app.services.streak.emit_tier_changed", return_value=None):
                # Create streak
                streak = HoldStreak(
                    wallet=wallet,
                    current_tier=3,
                    streak_start=datetime.now(timezone.utc) - timedelta(hours=24),
                    last_sell_at=None  # No previous sell
                )
                db_session.add(streak)
                await db_session.commit()

                before_sell = datetime.now(timezone.utc)
                result = await service.process_sell(wallet)
                after_sell = datetime.now(timezone.utc)

                # last_sell_at should be set
                assert result.last_sell_at is not None
                assert before_sell <= result.last_sell_at <= after_sell

    @pytest.mark.asyncio
    async def test_multiple_sells_compound_tier_drop(self, db_session):
        """Test that multiple sells drop tier multiple times."""
        service = StreakService(db_session)
        wallet = "MultipleSellWallet1111111111111111111111111"

        with patch("app.services.streak.emit_sell_detected", return_value=None):
            with patch("app.services.streak.emit_tier_changed", return_value=None):
                # Create at tier 5
                streak = HoldStreak(
                    wallet=wallet,
                    current_tier=5,
                    streak_start=datetime.now(timezone.utc) - timedelta(hours=200)
                )
                db_session.add(streak)
                await db_session.commit()

                # First sell: 5 -> 4
                result = await service.process_sell(wallet)
                assert result.current_tier == 4

                # Second sell: 4 -> 3
                result = await service.process_sell(wallet)
                assert result.current_tier == 3

                # Third sell: 3 -> 2
                result = await service.process_sell(wallet)
                assert result.current_tier == 2


class TestSellDetectionEdgeCases:
    """Edge cases for sell detection."""

    @pytest.fixture
    def helius_service(self):
        """Create HeliusService with test config."""
        with patch("app.services.helius.settings") as mock_settings:
            mock_settings.helius_api_key = "test-key"
            mock_settings.copper_token_mint = TEST_COPPER_MINT
            service = HeliusService()
            service.token_mint = TEST_COPPER_MINT
            return service

    def test_partial_sell_detected(self, helius_service):
        """Test that partial sells (not full balance) are detected."""
        payload = {
            "type": "SWAP",
            "signature": "5TBx...partial",
            "feePayer": "PartialSeller111111111111111111111111111",
            "tokenTransfers": [
                {
                    "mint": TEST_COPPER_MINT,
                    "fromUserAccount": "PartialSeller111111111111111111111111111",
                    "toUserAccount": "DexPool5555555555555555555555555555555555",
                    "tokenAmount": 10.0  # Small amount
                }
            ],
            "nativeTransfers": [
                {
                    "fromUserAccount": "DexPool5555555555555555555555555555555555",
                    "toUserAccount": "PartialSeller111111111111111111111111111",
                    "amount": 5000000  # Small SOL amount
                }
            ]
        }

        result = helius_service.parse_webhook_transaction(payload)
        # Even small sells should be detected
        assert result is not None
        assert result.is_sell is True

    def test_multi_hop_swap_detected(self, helius_service):
        """Test detection of multi-hop swaps (COPPER -> X -> SOL)."""
        # In multi-hop swaps, there might be intermediate tokens
        # But we should still detect COPPER leaving and SOL arriving
        payload = {
            "type": "SWAP",
            "signature": "5TBx...multihop",
            "feePayer": "MultiHopSeller11111111111111111111111111",
            "tokenTransfers": [
                {
                    "mint": TEST_COPPER_MINT,
                    "fromUserAccount": "MultiHopSeller11111111111111111111111111",
                    "toUserAccount": "Router111111111111111111111111111111111",
                    "tokenAmount": 100.0
                },
                {
                    "mint": "IntermediateToken11111111111111111111111",
                    "fromUserAccount": "Router111111111111111111111111111111111",
                    "toUserAccount": "Router222222222222222222222222222222222",
                    "tokenAmount": 50.0
                }
            ],
            "nativeTransfers": [
                {
                    "fromUserAccount": "Router222222222222222222222222222222222",
                    "toUserAccount": "MultiHopSeller11111111111111111111111111",
                    "amount": 500000000
                }
            ]
        }

        result = helius_service.parse_webhook_transaction(payload)
        # Should detect as sell since COPPER left and SOL arrived to same wallet
        assert result is not None
        assert result.is_sell is True

    def test_handles_very_large_amounts(self, helius_service):
        """Test handling of very large token amounts."""
        payload = {
            "type": "SWAP",
            "signature": "5TBx...large",
            "feePayer": "WhaleWallet1111111111111111111111111111111",
            "tokenTransfers": [
                {
                    "mint": TEST_COPPER_MINT,
                    "fromUserAccount": "WhaleWallet1111111111111111111111111111111",
                    "toUserAccount": "DexPool6666666666666666666666666666666666",
                    "tokenAmount": 999999999999.0  # Very large amount
                }
            ],
            "nativeTransfers": [
                {
                    "fromUserAccount": "DexPool6666666666666666666666666666666666",
                    "toUserAccount": "WhaleWallet1111111111111111111111111111111",
                    "amount": 999999999999999  # Very large SOL
                }
            ]
        }

        result = helius_service.parse_webhook_transaction(payload)
        assert result is not None
        assert result.is_sell is True

    def test_handles_decimal_amounts(self, helius_service):
        """Test handling of decimal token amounts."""
        payload = {
            "type": "SWAP",
            "signature": "5TBx...decimal",
            "feePayer": "DecimalWallet11111111111111111111111111111",
            "tokenTransfers": [
                {
                    "mint": TEST_COPPER_MINT,
                    "fromUserAccount": "DecimalWallet11111111111111111111111111111",
                    "toUserAccount": "DexPool7777777777777777777777777777777777",
                    "tokenAmount": 0.000001  # Very small decimal
                }
            ],
            "nativeTransfers": [
                {
                    "fromUserAccount": "DexPool7777777777777777777777777777777777",
                    "toUserAccount": "DecimalWallet11111111111111111111111111111",
                    "amount": 1000  # 0.000001 SOL
                }
            ]
        }

        result = helius_service.parse_webhook_transaction(payload)
        assert result is not None
        assert result.is_sell is True
