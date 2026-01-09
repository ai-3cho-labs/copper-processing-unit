"""
$COPPER Webhook Handler

Handles incoming webhooks from Helius for sell detection.
"""

import hmac
import logging
import re
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.utils.rate_limiter import limiter
from app.services.helius import get_helius_service
from app.services.streak import StreakService
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

# Solana wallet address validation: 32-44 base58 characters
WALLET_REGEX = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')

# Maximum age for webhook timestamps to prevent replay attacks
# Production: 5 minutes (strict)
# Development: 30 minutes (more lenient for testing)
WEBHOOK_MAX_AGE_SECONDS_PRODUCTION = 300
WEBHOOK_MAX_AGE_SECONDS_DEVELOPMENT = 1800


class WebhookResponse(BaseModel):
    """Webhook response."""
    success: bool
    message: str
    processed: int = 0


def verify_webhook_auth(
    auth_header: Optional[str],
    secret: str
) -> bool:
    """
    Verify Helius webhook authorization.

    Helius sends the authHeader value in the Authorization header.

    Args:
        auth_header: Authorization header value.
        secret: Expected auth header value (HELIUS_WEBHOOK_SECRET).

    Returns:
        True if authorization is valid.
    """
    if not auth_header or not secret:
        return False

    return hmac.compare_digest(auth_header, secret)


def validate_webhook_timestamp(timestamp: Optional[int]) -> bool:
    """
    Validate webhook timestamp to prevent replay attacks.

    SECURITY: Timestamps are ALWAYS required to prevent replay attacks.
    Production uses strict 5-minute window, development uses 30-minute window.

    Args:
        timestamp: Unix timestamp from webhook payload.

    Returns:
        True if timestamp is within acceptable range.
    """
    if timestamp is None:
        # SECURITY: Always require timestamps - replay attacks are possible without them
        logger.warning("Webhook rejected: missing timestamp (replay protection)")
        return False

    current_time = int(time.time())
    age = abs(current_time - timestamp)

    # Use stricter window in production
    max_age = WEBHOOK_MAX_AGE_SECONDS_PRODUCTION if settings.is_production else WEBHOOK_MAX_AGE_SECONDS_DEVELOPMENT

    if age > max_age:
        logger.warning(
            f"Webhook timestamp too old: {age}s (max: {max_age}s)"
        )
        return False

    return True


def validate_wallet_address(wallet: str) -> bool:
    """
    Validate Solana wallet address format.

    Args:
        wallet: Wallet address to validate.

    Returns:
        True if valid Solana address format.
    """
    if not wallet:
        return False
    return bool(WALLET_REGEX.match(wallet))


@router.post("/helius", response_model=WebhookResponse)
@limiter.limit("100/minute")
async def helius_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """
    Handle Helius webhook for transaction monitoring.

    Processes SWAP transactions to detect sells and update streaks.

    SECURITY: Webhook authorization verification is MANDATORY.
    Configure HELIUS_WEBHOOK_SECRET in environment (must match Helius authHeader).
    """
    # MANDATORY: Verify webhook authorization
    # This prevents attackers from sending fake sell events
    if not settings.helius_webhook_secret:
        logger.error("HELIUS_WEBHOOK_SECRET not configured - rejecting webhook")
        raise HTTPException(
            status_code=503,
            detail="Webhook endpoint not configured. Set HELIUS_WEBHOOK_SECRET."
        )

    if not verify_webhook_auth(
        authorization,
        settings.helius_webhook_secret
    ):
        logger.warning(
            f"Invalid webhook authorization from {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(status_code=401, detail="Invalid authorization")

    # Parse payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Handle array of transactions (Helius sends batches)
    transactions = payload if isinstance(payload, list) else [payload]

    if len(transactions) > 100:
        logger.warning(f"Webhook batch too large: {len(transactions)} transactions")
        raise HTTPException(
            status_code=400,
            detail="Batch too large. Maximum 100 transactions per request."
        )

    # Validate webhook timestamp from first transaction
    # SECURITY: Always require timestamps to prevent replay attacks
    # Helius includes timestamp in transaction metadata (blockTime or timestamp)
    if transactions:
        first_tx = transactions[0]
        tx_timestamp = first_tx.get("timestamp") or first_tx.get("blockTime")
        if not validate_webhook_timestamp(tx_timestamp):
            raise HTTPException(
                status_code=400,
                detail="Webhook timestamp missing or too old. Possible replay attack."
            )

    helius = get_helius_service()
    streak_service = StreakService(db)
    processed = 0
    errors = 0
    skipped_invalid_wallet = 0

    for tx in transactions:
        try:
            # Parse transaction
            parsed = helius.parse_webhook_transaction(tx)

            if parsed and parsed.is_sell:
                # Validate wallet address format before processing
                wallet = parsed.source_wallet
                if not validate_wallet_address(wallet):
                    logger.warning(f"Invalid wallet address in webhook: {wallet[:20] if wallet else 'None'}...")
                    skipped_invalid_wallet += 1
                    continue

                logger.info(
                    f"Sell detected: wallet={wallet[:8]}..., "
                    f"tx={parsed.signature[:16]}..., "
                    f"amount={parsed.amount_out}"
                )

                streak = await streak_service.process_sell(wallet)
                if streak:
                    processed += 1
                    logger.info(
                        f"Streak updated for {wallet[:8]}...: "
                        f"tier={streak.current_tier}"
                    )

        except Exception as e:
            logger.error(f"Error processing transaction: {e}")
            errors += 1
            continue

    # Build response message with details
    details = []
    if errors:
        details.append(f"{errors} errors")
    if skipped_invalid_wallet:
        details.append(f"{skipped_invalid_wallet} invalid wallets")
    detail_str = f" ({', '.join(details)})" if details else ""

    return WebhookResponse(
        success=True,
        message=f"Processed {processed} sell transactions{detail_str}",
        processed=processed
    )


@router.get("/helius/status")
async def webhook_status():
    """
    Get webhook configuration status.

    Note: Does not expose sensitive details, only configuration state.
    """
    # Check if webhook secret is configured
    secret_configured = bool(settings.helius_webhook_secret)

    if not secret_configured:
        return {
            "configured": False,
            "error": "HELIUS_WEBHOOK_SECRET not set. Webhook endpoint is disabled."
        }

    helius = get_helius_service()

    try:
        webhooks = await helius.get_webhooks()
        return {
            "configured": True,
            "signature_verification": "enabled",
            "registered_webhooks": len(webhooks),
            # Only show webhook count, not URLs or IDs (security)
        }
    except Exception as e:
        logger.error(f"Error fetching webhook status: {e}")
        return {
            "configured": True,
            "signature_verification": "enabled",
            "registered_webhooks": "unknown",
            "note": "Could not fetch webhook list from Helius"
        }
