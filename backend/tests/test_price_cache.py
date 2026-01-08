"""
$COPPER Price Cache Tests

Tests for price fetching, caching, fallback logic, and cache expiry.
"""

import pytest
import time
from decimal import Decimal
from unittest.mock import patch, MagicMock, AsyncMock

from app.utils.price_cache import (
    get_copper_price_usd,
    get_cached_price,
    clear_price_cache,
    warm_price_cache,
    _price_cache,
    CachedPrice,
    CACHE_TTL_SECONDS,
    STALE_TTL_SECONDS
)


class TestPriceFetching:
    """Tests for price fetching from APIs."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear price cache before each test."""
        clear_price_cache()
        yield
        clear_price_cache()

    @pytest.mark.asyncio
    async def test_fetches_from_jupiter_first(self):
        """Test that Jupiter API is tried first."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "TestMint111": {"price": 0.05}
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.utils.price_cache.get_http_client", return_value=mock_client):
            with patch("app.utils.price_cache.settings") as mock_settings:
                mock_settings.copper_token_mint = "TestMint111"

                price = await get_copper_price_usd()

                assert price == Decimal("0.05")
                # Verify Jupiter was called
                mock_client.get.assert_called_once()
                call_args = mock_client.get.call_args
                assert "jup.ag" in str(call_args)

    @pytest.mark.asyncio
    async def test_falls_back_to_birdeye(self):
        """Test fallback to Birdeye when Jupiter fails."""
        # Jupiter fails
        jupiter_response = MagicMock()
        jupiter_response.raise_for_status = MagicMock(side_effect=Exception("Jupiter down"))

        # Birdeye succeeds
        birdeye_response = MagicMock()
        birdeye_response.json.return_value = {
            "success": True,
            "data": {"value": 0.042}
        }
        birdeye_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=[jupiter_response, birdeye_response])

        with patch("app.utils.price_cache.get_http_client", return_value=mock_client):
            with patch("app.utils.price_cache.settings") as mock_settings:
                mock_settings.copper_token_mint = "TestMint222"

                price = await get_copper_price_usd()

                assert price == Decimal("0.042")
                assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_zero_when_all_fail(self):
        """Test returns 0 when all price feeds fail and no cache."""
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("All APIs down"))

        with patch("app.utils.price_cache.get_http_client", return_value=mock_client):
            with patch("app.utils.price_cache.settings") as mock_settings:
                mock_settings.copper_token_mint = "TestMint333"

                price = await get_copper_price_usd(use_fallback=False)

                assert price == Decimal(0)

    @pytest.mark.asyncio
    async def test_returns_zero_without_token_mint(self):
        """Test returns 0 when token mint not configured."""
        with patch("app.utils.price_cache.settings") as mock_settings:
            mock_settings.copper_token_mint = None

            price = await get_copper_price_usd()

            assert price == Decimal(0)


class TestPriceCaching:
    """Tests for price caching behavior."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear price cache before each test."""
        clear_price_cache()
        yield
        clear_price_cache()

    @pytest.mark.asyncio
    async def test_caches_successful_fetch(self):
        """Test that successful price fetch is cached."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {"TestMint444": {"price": 0.123}}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.utils.price_cache.get_http_client", return_value=mock_client):
            with patch("app.utils.price_cache.settings") as mock_settings:
                mock_settings.copper_token_mint = "TestMint444"

                # First call - fetches from API
                price1 = await get_copper_price_usd()
                assert price1 == Decimal("0.123")
                assert mock_client.get.call_count == 1

                # Second call - should use cache
                price2 = await get_copper_price_usd()
                assert price2 == Decimal("0.123")
                # Should NOT make another API call
                assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(self):
        """Test that cache expires after TTL."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {"TestMint555": {"price": 0.5}}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.utils.price_cache.get_http_client", return_value=mock_client):
            with patch("app.utils.price_cache.settings") as mock_settings:
                mock_settings.copper_token_mint = "TestMint555"

                # First fetch
                await get_copper_price_usd()
                assert mock_client.get.call_count == 1

                # Manually expire cache
                cache_key = "price:TestMint555"
                if cache_key in _price_cache:
                    _price_cache[cache_key] = CachedPrice(
                        price=Decimal("0.5"),
                        timestamp=time.time() - CACHE_TTL_SECONDS - 1,  # Expired
                        source="jupiter"
                    )

                # Second fetch - should hit API again
                await get_copper_price_usd()
                assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_uses_stale_cache_on_api_failure(self):
        """Test that stale cache is used when API fails."""
        # Pre-populate cache with stale but valid data
        cache_key = "price:TestMint666"
        _price_cache[cache_key] = CachedPrice(
            price=Decimal("0.333"),
            timestamp=time.time() - CACHE_TTL_SECONDS - 10,  # Expired but within stale TTL
            source="jupiter"
        )

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("API down"))

        with patch("app.utils.price_cache.get_http_client", return_value=mock_client):
            with patch("app.utils.price_cache.settings") as mock_settings:
                mock_settings.copper_token_mint = "TestMint666"

                # Should use stale cache
                price = await get_copper_price_usd(use_fallback=True)
                assert price == Decimal("0.333")

    @pytest.mark.asyncio
    async def test_stale_cache_expires_after_stale_ttl(self):
        """Test that even stale cache expires after STALE_TTL."""
        # Pre-populate with very old cache
        cache_key = "price:TestMint777"
        _price_cache[cache_key] = CachedPrice(
            price=Decimal("0.999"),
            timestamp=time.time() - STALE_TTL_SECONDS - 100,  # Beyond stale TTL
            source="jupiter"
        )

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("API down"))

        with patch("app.utils.price_cache.get_http_client", return_value=mock_client):
            with patch("app.utils.price_cache.settings") as mock_settings:
                mock_settings.copper_token_mint = "TestMint777"

                # Should NOT use old stale cache
                price = await get_copper_price_usd(use_fallback=True)
                assert price == Decimal(0)


class TestCacheManagement:
    """Tests for cache management functions."""

    def test_clear_price_cache(self):
        """Test clearing the price cache."""
        # Add some data
        _price_cache["test"] = CachedPrice(
            price=Decimal("1.0"),
            timestamp=time.time(),
            source="test"
        )

        assert len(_price_cache) > 0

        clear_price_cache()

        assert len(_price_cache) == 0

    def test_get_cached_price(self):
        """Test getting cached price without fetching."""
        # Clear first
        clear_price_cache()

        # No cache - should return None
        result = get_cached_price("NonExistentMint")
        assert result is None

        # Add to cache
        _price_cache["price:TestMint888"] = CachedPrice(
            price=Decimal("0.777"),
            timestamp=time.time(),
            source="birdeye"
        )

        with patch("app.utils.price_cache.settings") as mock_settings:
            mock_settings.copper_token_mint = "TestMint888"

            result = get_cached_price("TestMint888")
            assert result is not None
            assert result.price == Decimal("0.777")
            assert result.source == "birdeye"

    @pytest.mark.asyncio
    async def test_warm_price_cache_success(self):
        """Test warming price cache at startup."""
        clear_price_cache()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {"TestMint999": {"price": 0.111}}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.utils.price_cache.get_http_client", return_value=mock_client):
            with patch("app.utils.price_cache.settings") as mock_settings:
                mock_settings.copper_token_mint = "TestMint999"

                result = await warm_price_cache()

                assert result is True
                # Cache should now be populated
                cached = get_cached_price("TestMint999")
                assert cached is not None

    @pytest.mark.asyncio
    async def test_warm_price_cache_failure(self):
        """Test warm_price_cache returns False on failure."""
        clear_price_cache()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("API unavailable"))

        with patch("app.utils.price_cache.get_http_client", return_value=mock_client):
            with patch("app.utils.price_cache.settings") as mock_settings:
                mock_settings.copper_token_mint = "TestMintFail"

                result = await warm_price_cache()

                assert result is False


class TestPriceValidation:
    """Tests for price validation and edge cases."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear price cache before each test."""
        clear_price_cache()
        yield
        clear_price_cache()

    @pytest.mark.asyncio
    async def test_ignores_zero_price(self):
        """Test that zero price is treated as invalid."""
        # Jupiter returns 0
        jupiter_response = MagicMock()
        jupiter_response.json.return_value = {
            "data": {"TestMintZero": {"price": 0}}
        }
        jupiter_response.raise_for_status = MagicMock()

        # Birdeye returns valid price
        birdeye_response = MagicMock()
        birdeye_response.json.return_value = {
            "success": True,
            "data": {"value": 0.05}
        }
        birdeye_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=[jupiter_response, birdeye_response])

        with patch("app.utils.price_cache.get_http_client", return_value=mock_client):
            with patch("app.utils.price_cache.settings") as mock_settings:
                mock_settings.copper_token_mint = "TestMintZero"

                price = await get_copper_price_usd()

                # Should fall through to Birdeye
                assert price == Decimal("0.05")

    @pytest.mark.asyncio
    async def test_ignores_negative_price(self):
        """Test that negative price is treated as invalid."""
        jupiter_response = MagicMock()
        jupiter_response.json.return_value = {
            "data": {"TestMintNeg": {"price": -1.5}}
        }
        jupiter_response.raise_for_status = MagicMock()

        birdeye_response = MagicMock()
        birdeye_response.json.return_value = {
            "success": True,
            "data": {"value": 0.025}
        }
        birdeye_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=[jupiter_response, birdeye_response])

        with patch("app.utils.price_cache.get_http_client", return_value=mock_client):
            with patch("app.utils.price_cache.settings") as mock_settings:
                mock_settings.copper_token_mint = "TestMintNeg"

                price = await get_copper_price_usd()

                # Should fall through to Birdeye
                assert price == Decimal("0.025")

    @pytest.mark.asyncio
    async def test_handles_very_small_price(self):
        """Test handling of very small (but valid) prices."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {"TestMintSmall": {"price": 0.000000001}}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.utils.price_cache.get_http_client", return_value=mock_client):
            with patch("app.utils.price_cache.settings") as mock_settings:
                mock_settings.copper_token_mint = "TestMintSmall"

                price = await get_copper_price_usd()

                assert price > 0
                assert price == Decimal("0.000000001")

    @pytest.mark.asyncio
    async def test_handles_very_large_price(self):
        """Test handling of very large prices."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {"TestMintLarge": {"price": 99999.99}}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.utils.price_cache.get_http_client", return_value=mock_client):
            with patch("app.utils.price_cache.settings") as mock_settings:
                mock_settings.copper_token_mint = "TestMintLarge"

                price = await get_copper_price_usd()

                assert price == Decimal("99999.99")


class TestCacheSource:
    """Tests for tracking cache source (Jupiter vs Birdeye)."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear price cache before each test."""
        clear_price_cache()
        yield
        clear_price_cache()

    @pytest.mark.asyncio
    async def test_tracks_jupiter_source(self):
        """Test that Jupiter source is tracked."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {"TestMintJup": {"price": 0.1}}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.utils.price_cache.get_http_client", return_value=mock_client):
            with patch("app.utils.price_cache.settings") as mock_settings:
                mock_settings.copper_token_mint = "TestMintJup"

                await get_copper_price_usd()

                cached = get_cached_price("TestMintJup")
                assert cached.source == "jupiter"

    @pytest.mark.asyncio
    async def test_tracks_birdeye_source(self):
        """Test that Birdeye source is tracked when Jupiter fails."""
        jupiter_response = MagicMock()
        jupiter_response.raise_for_status = MagicMock(side_effect=Exception("fail"))

        birdeye_response = MagicMock()
        birdeye_response.json.return_value = {
            "success": True,
            "data": {"value": 0.2}
        }
        birdeye_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=[jupiter_response, birdeye_response])

        with patch("app.utils.price_cache.get_http_client", return_value=mock_client):
            with patch("app.utils.price_cache.settings") as mock_settings:
                mock_settings.copper_token_mint = "TestMintBird"

                await get_copper_price_usd()

                cached = get_cached_price("TestMintBird")
                assert cached.source == "birdeye"
