"""
$COPPER Webhook Handler

Handles incoming webhooks from Helius for sell detection.
"""

import hmac
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.helius import get_helius_service
from app.services.streak import StreakService
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/webhook", tags=["webhook"])


class WebhookResponse(BaseModel):
    """Webhook response."""
    success: bool
    message: str
    processed: int = 0


def verify_webhook_signature(
    payload: bytes,
    signature: Optional[str],
    secret: str
) -> bool:
    """
    Verify Helius webhook signature.

    Args:
        payload: Raw request body.
        signature: Signature from header.
        secret: Webhook secret.

    Returns:
        True if signature is valid.
    """
    if not signature or not secret:
        return False

    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


@router.post("/helius", response_model=WebhookResponse)
async def helius_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_helius_signature: Optional[str] = Header(None, alias="x-helius-signature")
):
    """
    Handle Helius webhook for transaction monitoring.

    Processes SWAP transactions to detect sells and update streaks.

    SECURITY: Webhook signature verification is MANDATORY.
    Configure HELIUS_WEBHOOK_SECRET in environment.
    """
    # Get raw body for signature verification
    body = await request.body()

    # MANDATORY: Verify webhook signature
    # This prevents attackers from sending fake sell events
    if not settings.helius_webhook_secret:
        logger.error("HELIUS_WEBHOOK_SECRET not configured - rejecting webhook")
        raise HTTPException(
            status_code=503,
            detail="Webhook endpoint not configured. Set HELIUS_WEBHOOK_SECRET."
        )

    if not verify_webhook_signature(
        body,
        x_helius_signature,
        settings.helius_webhook_secret
    ):
        logger.warning(
            f"Invalid webhook signature from {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(status_code=401, detail="Invalid signature")

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

    helius = get_helius_service()
    streak_service = StreakService(db)
    processed = 0
    errors = 0

    for tx in transactions:
        try:
            # Parse transaction
            parsed = helius.parse_webhook_transaction(tx)

            if parsed and parsed.is_sell:
                # Process sell - drop tier
                wallet = parsed.source_wallet
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

    return WebhookResponse(
        success=True,
        message=f"Processed {processed} sell transactions" + (
            f" ({errors} errors)" if errors else ""
        ),
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
