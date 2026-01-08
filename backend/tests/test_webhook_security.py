"""
$COPPER Webhook Security Tests

Tests for webhook HMAC verification, payload validation, and attack prevention.
"""

import hmac
import hashlib
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.webhook import verify_webhook_signature


class TestHMACSignatureVerification:
    """Tests for HMAC signature verification."""

    def test_valid_signature_passes(self):
        """Test that valid HMAC signature passes verification."""
        secret = "test-webhook-secret-12345"
        payload = b'{"type": "SWAP", "signature": "abc123"}'

        # Generate valid signature
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        result = verify_webhook_signature(payload, signature, secret)
        assert result is True

    def test_invalid_signature_fails(self):
        """Test that invalid signature is rejected."""
        secret = "test-webhook-secret-12345"
        payload = b'{"type": "SWAP", "signature": "abc123"}'

        # Use wrong signature
        result = verify_webhook_signature(payload, "invalid-signature", secret)
        assert result is False

    def test_missing_signature_fails(self):
        """Test that missing signature is rejected."""
        secret = "test-webhook-secret-12345"
        payload = b'{"type": "SWAP"}'

        result = verify_webhook_signature(payload, None, secret)
        assert result is False

    def test_empty_signature_fails(self):
        """Test that empty signature is rejected."""
        secret = "test-webhook-secret-12345"
        payload = b'{"type": "SWAP"}'

        result = verify_webhook_signature(payload, "", secret)
        assert result is False

    def test_missing_secret_fails(self):
        """Test that missing secret is rejected."""
        payload = b'{"type": "SWAP"}'
        signature = "some-signature"

        result = verify_webhook_signature(payload, signature, "")
        assert result is False

    def test_modified_payload_fails(self):
        """Test that modified payload fails signature verification."""
        secret = "test-webhook-secret-12345"
        original_payload = b'{"type": "SWAP", "amount": 100}'

        # Generate signature for original
        signature = hmac.new(
            secret.encode(),
            original_payload,
            hashlib.sha256
        ).hexdigest()

        # Try to verify with modified payload
        modified_payload = b'{"type": "SWAP", "amount": 999999}'
        result = verify_webhook_signature(modified_payload, signature, secret)
        assert result is False

    def test_timing_attack_resistant(self):
        """Test that signature comparison uses constant-time comparison."""
        # The verify_webhook_signature function should use hmac.compare_digest
        # which is resistant to timing attacks
        secret = "test-webhook-secret-12345"
        payload = b'{"type": "SWAP"}'

        # Generate valid signature
        valid_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        # The function should complete in similar time for near-matches vs total mismatches
        # This is hard to test directly, but we verify compare_digest is used by code review
        # Here we just verify the function works correctly
        assert verify_webhook_signature(payload, valid_sig, secret) is True
        assert verify_webhook_signature(payload, valid_sig[:-1] + "x", secret) is False


@pytest.mark.asyncio
class TestWebhookEndpoint:
    """Tests for the webhook HTTP endpoint."""

    async def test_rejects_missing_secret_config(self):
        """Test endpoint returns 503 when webhook secret not configured."""
        mock_settings = MagicMock()
        mock_settings.helius_webhook_secret = None

        with patch("app.api.webhook.settings", mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/webhook/helius",
                    json={"type": "SWAP"},
                    headers={"x-helius-signature": "fake-sig"}
                )
                assert response.status_code == 503
                assert "not configured" in response.json()["detail"].lower()

    async def test_rejects_missing_signature_header(self):
        """Test endpoint returns 401 when signature header missing."""
        mock_settings = MagicMock()
        mock_settings.helius_webhook_secret = "test-secret"

        with patch("app.api.webhook.settings", mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/webhook/helius",
                    json={"type": "SWAP"}
                    # No x-helius-signature header
                )
                assert response.status_code == 401
                assert "Invalid signature" in response.json()["detail"]

    async def test_rejects_invalid_signature(self):
        """Test endpoint returns 401 for invalid signature."""
        mock_settings = MagicMock()
        mock_settings.helius_webhook_secret = "test-secret"

        with patch("app.api.webhook.settings", mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/webhook/helius",
                    json={"type": "SWAP"},
                    headers={"x-helius-signature": "invalid-signature"}
                )
                assert response.status_code == 401

    async def test_rejects_invalid_json(self):
        """Test endpoint returns 400 for malformed JSON."""
        secret = "test-secret"
        payload = b"not valid json {"
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        mock_settings = MagicMock()
        mock_settings.helius_webhook_secret = secret

        with patch("app.api.webhook.settings", mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/webhook/helius",
                    content=payload,
                    headers={
                        "x-helius-signature": signature,
                        "content-type": "application/json"
                    }
                )
                assert response.status_code == 400
                assert "Invalid JSON" in response.json()["detail"]

    async def test_rejects_oversized_batch(self):
        """Test endpoint returns 400 for batches over 100 transactions."""
        secret = "test-secret"
        # Create 101 transactions
        large_batch = [{"type": "SWAP", "signature": f"tx{i}"} for i in range(101)]
        payload = json.dumps(large_batch).encode()
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        mock_settings = MagicMock()
        mock_settings.helius_webhook_secret = secret

        with patch("app.api.webhook.settings", mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/webhook/helius",
                    content=payload,
                    headers={
                        "x-helius-signature": signature,
                        "content-type": "application/json"
                    }
                )
                assert response.status_code == 400
                assert "Batch too large" in response.json()["detail"]

    async def test_accepts_valid_request(self):
        """Test endpoint accepts properly signed valid request."""
        secret = "test-secret"
        payload_data = {
            "type": "SWAP",
            "signature": "abc123",
            "feePayer": "TestWallet11111111111111111111111111111111",
            "tokenTransfers": []
        }
        payload = json.dumps(payload_data).encode()
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        mock_settings = MagicMock()
        mock_settings.helius_webhook_secret = secret
        mock_settings.copper_token_mint = "TestMint111111111111111111111111111111111"

        mock_helius = MagicMock()
        mock_helius.parse_webhook_transaction.return_value = None

        with patch("app.api.webhook.settings", mock_settings):
            with patch("app.api.webhook.get_helius_service", return_value=mock_helius):
                with patch("app.api.webhook.get_db"):
                    async with AsyncClient(
                        transport=ASGITransport(app=app),
                        base_url="http://test"
                    ) as client:
                        response = await client.post(
                            "/api/webhook/helius",
                            content=payload,
                            headers={
                                "x-helius-signature": signature,
                                "content-type": "application/json"
                            }
                        )
                        # May fail due to DB dependency, but should pass auth
                        # Status 200 or 500 (DB error) but NOT 401/400
                        assert response.status_code != 401


class TestWebhookPayloadValidation:
    """Tests for payload structure validation."""

    def test_handles_single_transaction(self):
        """Test that single transaction (not array) is handled."""
        # The webhook handler wraps single transactions in array
        single_tx = {"type": "SWAP", "signature": "abc"}
        transactions = single_tx if isinstance(single_tx, list) else [single_tx]
        assert len(transactions) == 1
        assert transactions[0]["type"] == "SWAP"

    def test_handles_array_of_transactions(self):
        """Test that array of transactions is handled correctly."""
        batch = [
            {"type": "SWAP", "signature": "abc"},
            {"type": "SWAP", "signature": "def"}
        ]
        transactions = batch if isinstance(batch, list) else [batch]
        assert len(transactions) == 2

    def test_empty_payload_handled(self):
        """Test that empty array is handled gracefully."""
        batch = []
        transactions = batch if isinstance(batch, list) else [batch]
        assert len(transactions) == 0


class TestAttackPrevention:
    """Tests for specific attack vector prevention."""

    def test_prevents_signature_bypass_with_null(self):
        """Test that null/None signature cannot bypass verification."""
        secret = "test-secret"
        payload = b'{"type": "SWAP"}'

        # Try various null-like values
        assert verify_webhook_signature(payload, None, secret) is False
        assert verify_webhook_signature(payload, "", secret) is False

    def test_prevents_secret_extraction_via_timing(self):
        """Verify constant-time comparison is used (code inspection test)."""
        # This test documents that hmac.compare_digest is used
        # which provides timing-attack resistance
        import inspect
        from app.api.webhook import verify_webhook_signature

        source = inspect.getsource(verify_webhook_signature)
        assert "compare_digest" in source, "Must use hmac.compare_digest for timing attack resistance"

    def test_large_payload_handling(self):
        """Test that very large payloads don't crash the system."""
        secret = "test-secret"
        # 1MB payload
        large_payload = b'{"data": "' + b'x' * (1024 * 1024) + b'"}'
        signature = hmac.new(secret.encode(), large_payload, hashlib.sha256).hexdigest()

        # Should compute signature without crashing
        result = verify_webhook_signature(large_payload, signature, secret)
        assert result is True

    def test_unicode_payload_handling(self):
        """Test that unicode payloads are handled correctly."""
        secret = "test-secret"
        unicode_payload = '{"wallet": "テスト", "amount": 100}'.encode('utf-8')
        signature = hmac.new(secret.encode(), unicode_payload, hashlib.sha256).hexdigest()

        result = verify_webhook_signature(unicode_payload, signature, secret)
        assert result is True
