"""
$COPPER Helius Service

Interacts with Helius API for token holder data and webhooks.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass

from app.utils.http_client import get_http_client
from app.config import get_settings, SOL_MINT, USDC_MINT, TOKEN_MULTIPLIER, LAMPORTS_PER_SOL

logger = logging.getLogger(__name__)
settings = get_settings()

HELIUS_API_BASE = "https://api.helius.xyz/v0"


def _get_rpc_url() -> str:
    """Get Helius RPC URL (computed at call time, not module load)."""
    return settings.helius_rpc_url


@dataclass
class TokenAccount:
    """Token account holder data."""
    wallet: str
    balance: int  # Raw token amount (with decimals)


@dataclass
class ParsedTransaction:
    """Parsed webhook transaction data."""
    signature: str
    tx_type: str  # SWAP, TRANSFER, etc.
    source_wallet: str
    token_in: Optional[str] = None
    token_out: Optional[str] = None
    amount_in: Optional[int] = None
    amount_out: Optional[int] = None
    is_sell: bool = False  # True if COPPER sold for SOL/USDC


class HeliusService:
    """Service for Helius API interactions."""

    def __init__(self):
        self.api_key = settings.helius_api_key
        self.token_mint = settings.copper_token_mint

    @property
    def client(self):
        """Get shared HTTP client."""
        return get_http_client()

    async def get_token_accounts(self, mint: Optional[str] = None) -> list[TokenAccount]:
        """
        Fetch all token holders for the given mint.

        Uses DAS API getTokenAccounts for efficient holder fetching.

        Args:
            mint: Token mint address. Defaults to COPPER_TOKEN_MINT.

        Returns:
            List of TokenAccount with wallet addresses and balances.

        Raises:
            ValueError: If mint not configured.
            Exception: On API errors after retries.
        """
        mint = mint or self.token_mint
        if not mint:
            raise ValueError("Token mint address not configured")

        holders: list[TokenAccount] = []
        page = 1
        max_pages = 100  # Safety limit

        while page <= max_pages:
            try:
                response = await self.client.post(
                    _get_rpc_url(),
                    json={
                        "jsonrpc": "2.0",
                        "id": f"copper-snapshot-{page}",
                        "method": "getTokenAccounts",
                        "params": {
                            "mint": mint,
                            "page": page,
                            "limit": 1000,
                            "displayOptions": {
                                "showZeroBalance": False
                            }
                        }
                    }
                )
                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    error_msg = data["error"].get("message", str(data["error"]))
                    logger.error(f"Helius API error: {error_msg}")
                    raise Exception(f"Helius API error: {error_msg}")

                result = data.get("result", {})
                accounts = result.get("token_accounts", [])

                if not accounts:
                    break

                for account in accounts:
                    owner = account.get("owner")
                    amount = account.get("amount")

                    if owner and amount and int(amount) > 0:
                        holders.append(TokenAccount(
                            wallet=owner,
                            balance=int(amount)
                        ))

                # Check if more pages
                if len(accounts) < 1000:
                    break

                page += 1

            except Exception as e:
                logger.error(f"Error fetching token accounts (page {page}): {e}")
                raise

        logger.info(f"Fetched {len(holders)} token holders for mint {mint[:8]}...")
        return holders

    async def get_token_supply(self, mint: Optional[str] = None) -> int:
        """
        Get total token supply.

        Args:
            mint: Token mint address. Defaults to COPPER_TOKEN_MINT.

        Returns:
            Total supply in raw token amount.

        Raises:
            ValueError: If mint not configured.
        """
        mint = mint or self.token_mint
        if not mint:
            raise ValueError("Token mint address not configured")

        try:
            response = await self.client.post(
                _get_rpc_url(),
                json={
                    "jsonrpc": "2.0",
                    "id": "copper-supply",
                    "method": "getTokenSupply",
                    "params": [mint]
                }
            )
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                error_msg = data["error"].get("message", str(data["error"]))
                logger.error(f"Helius API error: {error_msg}")
                raise Exception(f"Helius API error: {error_msg}")

            result = data.get("result", {}).get("value", {})
            return int(result.get("amount", 0))

        except Exception as e:
            logger.error(f"Error fetching token supply: {e}")
            raise

    def parse_webhook_transaction(self, payload: dict) -> Optional[ParsedTransaction]:
        """
        Parse incoming Helius webhook transaction.

        Detects if transaction is a sell (COPPER → SOL/USDC swap).

        A sell is when the fee payer (transaction initiator):
        - SENDS COPPER out (to a DEX or liquidity pool)
        - RECEIVES SOL or USDC in return

        A buy (SOL → COPPER) is NOT a sell and returns None.

        Args:
            payload: Raw webhook payload from Helius.

        Returns:
            ParsedTransaction if valid sell swap, None otherwise.
        """
        try:
            # Helius enhanced transaction format
            tx_type = payload.get("type", "")
            signature = payload.get("signature", "")

            # Get source wallet (fee payer is the user initiating the transaction)
            fee_payer = payload.get("feePayer", "")
            if not fee_payer:
                return None

            # Check token transfers
            token_transfers = payload.get("tokenTransfers", [])

            # Look for the fee payer SENDING COPPER out (selling)
            copper_out = None
            sol_or_usdc_in = None

            for transfer in token_transfers:
                mint = transfer.get("mint", "")
                from_user = transfer.get("fromUserAccount", "")
                to_user = transfer.get("toUserAccount", "")
                amount = transfer.get("tokenAmount", 0)

                # COPPER being sent OUT by the fee payer (user selling)
                if mint == self.token_mint and from_user == fee_payer:
                    copper_out = {
                        "wallet": from_user,
                        "amount": int(Decimal(str(amount)) * Decimal(str(TOKEN_MULTIPLIER)))
                    }

                # SOL or USDC being received BY the fee payer
                # SOL uses 9 decimals (1e9), USDC uses 6 decimals (1e6)
                if mint in [SOL_MINT, USDC_MINT] and to_user == fee_payer:
                    multiplier = Decimal(str(LAMPORTS_PER_SOL)) if mint == SOL_MINT else Decimal("1e6")
                    sol_or_usdc_in = {
                        "mint": mint,
                        "amount": int(Decimal(str(amount)) * multiplier)
                    }

            # Check native SOL transfers to the fee payer
            native_transfers = payload.get("nativeTransfers", [])
            for transfer in native_transfers:
                to_user = transfer.get("toUserAccount", "")
                amount = transfer.get("amount", 0)

                # SOL being received BY the fee payer (the seller)
                if to_user == fee_payer and copper_out:
                    sol_or_usdc_in = {
                        "mint": SOL_MINT,
                        "amount": int(amount)
                    }

            # Determine if this is a sell:
            # Fee payer sent COPPER out AND received SOL/USDC back
            is_sell = bool(copper_out and sol_or_usdc_in)

            if is_sell:
                return ParsedTransaction(
                    signature=signature,
                    tx_type=tx_type or "SWAP",
                    source_wallet=fee_payer,
                    token_in=sol_or_usdc_in["mint"] if sol_or_usdc_in else None,
                    token_out=self.token_mint,
                    amount_in=sol_or_usdc_in["amount"] if sol_or_usdc_in else None,
                    amount_out=copper_out["amount"] if copper_out else None,
                    is_sell=True
                )

            return None

        except Exception as e:
            logger.error(f"Error parsing webhook transaction: {e}")
            return None

    def _get_auth_headers(self) -> dict:
        """
        Get authorization headers for Helius API requests.

        SECURITY: Uses Authorization header instead of query parameters
        to prevent API key exposure in logs, referer headers, and browser history.
        """
        return {"Authorization": f"Bearer {self.api_key}"}

    async def setup_webhook(self, webhook_url: str) -> Optional[str]:
        """
        Create or update Helius webhook for token monitoring.

        Args:
            webhook_url: URL to receive webhook callbacks.

        Returns:
            Webhook ID if successful, None otherwise.
        """
        if not self.token_mint:
            raise ValueError("Token mint address not configured")

        try:
            response = await self.client.post(
                f"{HELIUS_API_BASE}/webhooks",
                headers=self._get_auth_headers(),
                json={
                    "webhookURL": webhook_url,
                    "transactionTypes": ["SWAP"],
                    "accountAddresses": [self.token_mint],
                    "webhookType": "enhanced",
                    "txnStatus": "success"
                }
            )
            response.raise_for_status()
            data = response.json()

            webhook_id = data.get("webhookID")
            logger.info(f"Webhook created/updated: {webhook_id}")
            return webhook_id

        except Exception as e:
            logger.error(f"Error setting up webhook: {e}")
            raise

    async def get_webhooks(self) -> list[dict]:
        """
        Get all configured webhooks.

        Returns:
            List of webhook configurations.
        """
        try:
            response = await self.client.get(
                f"{HELIUS_API_BASE}/webhooks",
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching webhooks: {e}")
            raise

    async def delete_webhook(self, webhook_id: str) -> bool:
        """
        Delete a webhook.

        Args:
            webhook_id: ID of webhook to delete.

        Returns:
            True if successful.
        """
        try:
            response = await self.client.delete(
                f"{HELIUS_API_BASE}/webhooks/{webhook_id}",
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            logger.info(f"Webhook deleted: {webhook_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")
            raise


# Thread-safe singleton using module-level initialization
_helius_service: Optional[HeliusService] = None
_lock = None

try:
    import threading
    _lock = threading.Lock()
except ImportError:
    pass


def get_helius_service() -> HeliusService:
    """Get or create Helius service instance (thread-safe)."""
    global _helius_service

    if _helius_service is not None:
        return _helius_service

    if _lock:
        with _lock:
            if _helius_service is None:
                _helius_service = HeliusService()
    else:
        _helius_service = HeliusService()

    return _helius_service
