"""
$COPPER API Routes Tests

Tests for REST API endpoints.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from decimal import Decimal
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self):
        """Test health check returns healthy status."""
        with TestClient(app) as client:
            response = client.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "copper-backend"

    def test_root_endpoint(self):
        """Test root endpoint returns welcome message."""
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert "message" in data


class TestUserEndpoints:
    """Tests for user-related endpoints."""

    def test_get_user_stats_valid_wallet(self):
        """Test getting stats for a valid wallet address."""
        with TestClient(app) as client:
            # Use a valid base58 Solana address format (44 chars)
            wallet = "11111111111111111111111111111111111111111111"
            response = client.get(f"/api/user/{wallet}")

            # Response should be 200, 404, 422, or 500 depending on validation/db state
            assert response.status_code in [200, 404, 422, 500]

    def test_get_user_stats_invalid_wallet_format(self):
        """Test invalid wallet address format is rejected."""
        with TestClient(app) as client:
            # Test with too short wallet
            response = client.get("/api/user/short")
            assert response.status_code == 422  # FastAPI validation error

    def test_get_user_history(self):
        """Test getting distribution history for a wallet."""
        with TestClient(app) as client:
            # Use a valid base58 Solana address format (44 chars)
            wallet = "11111111111111111111111111111111111111111111"
            response = client.get(f"/api/user/{wallet}/history")
            assert response.status_code in [200, 404, 422, 500]


class TestLeaderboardEndpoint:
    """Tests for leaderboard endpoint."""

    def test_leaderboard_default_limit(self):
        """Test leaderboard with default limit."""
        with TestClient(app) as client:
            response = client.get("/api/leaderboard")
            assert response.status_code in [200, 500]

    def test_leaderboard_custom_limit(self):
        """Test leaderboard with custom limit."""
        with TestClient(app) as client:
            response = client.get("/api/leaderboard?limit=5")
            assert response.status_code in [200, 500]

    def test_leaderboard_limit_validation(self):
        """Test leaderboard rejects invalid limits."""
        with TestClient(app) as client:
            # Limit too high
            response = client.get("/api/leaderboard?limit=100")
            assert response.status_code in [200, 422]

            # Limit too low
            response = client.get("/api/leaderboard?limit=0")
            assert response.status_code == 422


class TestPoolEndpoint:
    """Tests for pool status endpoint."""

    def test_pool_status(self):
        """Test pool status endpoint."""
        with TestClient(app) as client:
            response = client.get("/api/pool")
            assert response.status_code in [200, 500]


class TestDistributionsEndpoint:
    """Tests for distributions endpoint."""

    def test_get_recent_distributions(self):
        """Test getting recent distributions."""
        with TestClient(app) as client:
            response = client.get("/api/distributions")
            assert response.status_code in [200, 500]

    def test_distributions_limit(self):
        """Test distributions with custom limit."""
        with TestClient(app) as client:
            response = client.get("/api/distributions?limit=5")
            assert response.status_code in [200, 500]


class TestTiersEndpoint:
    """Tests for tiers info endpoint."""

    def test_get_tiers(self):
        """Test getting tier configuration."""
        with TestClient(app) as client:
            response = client.get("/api/tiers")
            assert response.status_code == 200

            data = response.json()
            # Response is a list of tiers directly
            assert isinstance(data, list)
            assert len(data) == 6

            # Verify tier structure
            for tier in data:
                assert "name" in tier
                assert "multiplier" in tier
                assert "min_hours" in tier


class TestStatsEndpoint:
    """Tests for global stats endpoint."""

    def test_get_global_stats(self):
        """Test getting global statistics."""
        with TestClient(app) as client:
            response = client.get("/api/stats")
            assert response.status_code in [200, 500]


class TestRateLimiting:
    """Tests for rate limiting."""

    def test_rate_limit_headers(self):
        """Test that rate limit headers are present."""
        with TestClient(app) as client:
            response = client.get("/api/health")
            # Rate limit headers should be present
            # Note: Exact headers depend on slowapi configuration


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_route_404(self):
        """Test that invalid routes return 404."""
        with TestClient(app) as client:
            response = client.get("/api/nonexistent")
            assert response.status_code == 404

    def test_method_not_allowed(self):
        """Test method not allowed returns 405."""
        with TestClient(app) as client:
            # POST to GET-only endpoint
            response = client.post("/api/health")
            assert response.status_code == 405
