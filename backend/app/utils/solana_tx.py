"""
$COPPER Solana Transaction Utilities

Handles transaction signing and sending using solders.
"""

import logging
import base64
import base58
from typing import Optional
from dataclasses import dataclass

from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.signature import Signature

from app.utils.http_client import get_http_client
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class TransactionResult:
    """Result of a transaction send."""
    success: bool
    signature: Optional[str] = None
    error: Optional[str] = None


def keypair_from_base58(private_key: str) -> Keypair:
    """
    Create a Keypair from a base58-encoded private key.

    Args:
        private_key: Base58-encoded private key (64 bytes).

    Returns:
        Keypair instance.
    """
    secret_bytes = base58.b58decode(private_key)
    return Keypair.from_bytes(secret_bytes)


async def sign_and_send_transaction(
    serialized_tx: str,
    private_key: str,
    skip_preflight: bool = False
) -> TransactionResult:
    """
    Sign and send a serialized transaction.

    Args:
        serialized_tx: Base64-encoded serialized transaction from Jupiter.
        private_key: Base58-encoded private key.
        skip_preflight: Skip preflight simulation.

    Returns:
        TransactionResult with signature or error.
    """
    try:
        # Decode the transaction
        tx_bytes = base64.b64decode(serialized_tx)
        transaction = VersionedTransaction.from_bytes(tx_bytes)

        # Create keypair and sign
        keypair = keypair_from_base58(private_key)

        # Sign the transaction
        signed_tx = VersionedTransaction(
            transaction.message,
            [keypair]
        )

        # Serialize for sending
        signed_bytes = bytes(signed_tx)
        signed_base64 = base64.b64encode(signed_bytes).decode("utf-8")

        # Send via RPC
        client = get_http_client()
        response = await client.post(
            settings.helius_rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": "copper-tx",
                "method": "sendTransaction",
                "params": [
                    signed_base64,
                    {
                        "encoding": "base64",
                        "skipPreflight": skip_preflight,
                        "preflightCommitment": "confirmed",
                        "maxRetries": 3
                    }
                ]
            }
        )
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            error_msg = data["error"].get("message", str(data["error"]))
            logger.error(f"Transaction send error: {error_msg}")
            return TransactionResult(
                success=False,
                error=error_msg
            )

        signature = data.get("result")
        if signature:
            logger.info(f"Transaction sent: {signature}")
            return TransactionResult(
                success=True,
                signature=signature
            )

        return TransactionResult(
            success=False,
            error="No signature returned"
        )

    except Exception as e:
        logger.error(f"Error signing/sending transaction: {e}", exc_info=True)
        return TransactionResult(
            success=False,
            error=str(e)
        )


async def send_sol_transfer(
    from_private_key: str,
    to_address: str,
    amount_lamports: int
) -> TransactionResult:
    """
    Send SOL from one wallet to another.

    Args:
        from_private_key: Base58-encoded private key of sender.
        to_address: Recipient wallet address.
        amount_lamports: Amount in lamports (1 SOL = 1e9 lamports).

    Returns:
        TransactionResult with signature or error.
    """
    from solders.pubkey import Pubkey
    from solders.system_program import transfer, TransferParams
    from solders.message import MessageV0
    from solders.hash import Hash

    try:
        # Create keypair
        keypair = keypair_from_base58(from_private_key)
        to_pubkey = Pubkey.from_string(to_address)

        # Get recent blockhash
        client = get_http_client()
        blockhash_response = await client.post(
            settings.helius_rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": "copper-blockhash",
                "method": "getLatestBlockhash",
                "params": [{"commitment": "finalized"}]
            }
        )
        blockhash_response.raise_for_status()
        blockhash_data = blockhash_response.json()

        if "error" in blockhash_data:
            return TransactionResult(
                success=False,
                error=blockhash_data["error"].get("message", "Failed to get blockhash")
            )

        blockhash_str = blockhash_data["result"]["value"]["blockhash"]
        recent_blockhash = Hash.from_string(blockhash_str)

        # Create transfer instruction
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=keypair.pubkey(),
                to_pubkey=to_pubkey,
                lamports=amount_lamports
            )
        )

        # Create message and transaction
        message = MessageV0.try_compile(
            payer=keypair.pubkey(),
            instructions=[transfer_ix],
            address_lookup_table_accounts=[],
            recent_blockhash=recent_blockhash
        )

        transaction = VersionedTransaction(message, [keypair])

        # Serialize and send
        tx_bytes = bytes(transaction)
        tx_base64 = base64.b64encode(tx_bytes).decode("utf-8")

        response = await client.post(
            settings.helius_rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": "copper-sol-transfer",
                "method": "sendTransaction",
                "params": [
                    tx_base64,
                    {
                        "encoding": "base64",
                        "skipPreflight": False,
                        "preflightCommitment": "confirmed",
                        "maxRetries": 3
                    }
                ]
            }
        )
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            error_msg = data["error"].get("message", str(data["error"]))
            logger.error(f"SOL transfer error: {error_msg}")
            return TransactionResult(
                success=False,
                error=error_msg
            )

        signature = data.get("result")
        if signature:
            logger.info(f"SOL transfer sent: {signature}")
            return TransactionResult(
                success=True,
                signature=signature
            )

        return TransactionResult(
            success=False,
            error="No signature returned"
        )

    except Exception as e:
        logger.error(f"Error sending SOL transfer: {e}", exc_info=True)
        return TransactionResult(
            success=False,
            error=str(e)
        )


async def send_spl_token_transfer(
    from_private_key: str,
    to_address: str,
    token_mint: str,
    amount: int
) -> TransactionResult:
    """
    Send SPL tokens from one wallet to another.

    Args:
        from_private_key: Base58-encoded private key of sender.
        to_address: Recipient wallet address.
        token_mint: Token mint address.
        amount: Raw token amount (with decimals).

    Returns:
        TransactionResult with signature or error.
    """
    from solders.pubkey import Pubkey
    from solders.message import MessageV0
    from solders.hash import Hash
    from solders.instruction import Instruction, AccountMeta

    try:
        # SPL Token Program ID
        TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
        ASSOCIATED_TOKEN_PROGRAM_ID = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")

        # Create keypair
        keypair = keypair_from_base58(from_private_key)
        mint_pubkey = Pubkey.from_string(token_mint)
        to_pubkey = Pubkey.from_string(to_address)

        # Derive ATAs (Associated Token Accounts)
        def get_ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
            seeds = [bytes(owner), bytes(TOKEN_PROGRAM_ID), bytes(mint)]
            ata, _ = Pubkey.find_program_address(seeds, ASSOCIATED_TOKEN_PROGRAM_ID)
            return ata

        from_ata = get_ata(keypair.pubkey(), mint_pubkey)
        to_ata = get_ata(to_pubkey, mint_pubkey)

        # Get recent blockhash
        client = get_http_client()
        blockhash_response = await client.post(
            settings.helius_rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": "copper-blockhash",
                "method": "getLatestBlockhash",
                "params": [{"commitment": "finalized"}]
            }
        )
        blockhash_response.raise_for_status()
        blockhash_data = blockhash_response.json()

        if "error" in blockhash_data:
            return TransactionResult(
                success=False,
                error=blockhash_data["error"].get("message", "Failed to get blockhash")
            )

        blockhash_str = blockhash_data["result"]["value"]["blockhash"]
        recent_blockhash = Hash.from_string(blockhash_str)

        # Check if recipient ATA exists
        ata_check_response = await client.post(
            settings.helius_rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": "copper-ata-check",
                "method": "getAccountInfo",
                "params": [str(to_ata), {"encoding": "base64"}]
            }
        )
        ata_check_response.raise_for_status()
        ata_check_data = ata_check_response.json()
        ata_exists = ata_check_data.get("result", {}).get("value") is not None

        instructions = []

        # Create ATA if it doesn't exist
        if not ata_exists:
            create_ata_ix = Instruction(
                program_id=ASSOCIATED_TOKEN_PROGRAM_ID,
                accounts=[
                    AccountMeta(keypair.pubkey(), is_signer=True, is_writable=True),  # Payer
                    AccountMeta(to_ata, is_signer=False, is_writable=True),  # ATA
                    AccountMeta(to_pubkey, is_signer=False, is_writable=False),  # Owner
                    AccountMeta(mint_pubkey, is_signer=False, is_writable=False),  # Mint
                    AccountMeta(Pubkey.from_string("11111111111111111111111111111111"), is_signer=False, is_writable=False),  # System
                    AccountMeta(TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),  # Token Program
                ],
                data=bytes()  # No data for create ATA
            )
            instructions.append(create_ata_ix)

        # Transfer instruction data: [3] + amount as u64 little endian
        transfer_data = bytes([3]) + amount.to_bytes(8, "little")

        transfer_ix = Instruction(
            program_id=TOKEN_PROGRAM_ID,
            accounts=[
                AccountMeta(from_ata, is_signer=False, is_writable=True),  # Source
                AccountMeta(to_ata, is_signer=False, is_writable=True),  # Destination
                AccountMeta(keypair.pubkey(), is_signer=True, is_writable=False),  # Authority
            ],
            data=transfer_data
        )
        instructions.append(transfer_ix)

        # Create message and transaction
        message = MessageV0.try_compile(
            payer=keypair.pubkey(),
            instructions=instructions,
            address_lookup_table_accounts=[],
            recent_blockhash=recent_blockhash
        )

        transaction = VersionedTransaction(message, [keypair])

        # Serialize and send
        tx_bytes = bytes(transaction)
        tx_base64 = base64.b64encode(tx_bytes).decode("utf-8")

        response = await client.post(
            settings.helius_rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": "copper-token-transfer",
                "method": "sendTransaction",
                "params": [
                    tx_base64,
                    {
                        "encoding": "base64",
                        "skipPreflight": False,
                        "preflightCommitment": "confirmed",
                        "maxRetries": 3
                    }
                ]
            }
        )
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            error_msg = data["error"].get("message", str(data["error"]))
            logger.error(f"Token transfer error: {error_msg}")
            return TransactionResult(
                success=False,
                error=error_msg
            )

        signature = data.get("result")
        if signature:
            logger.info(f"Token transfer sent: {signature}")
            return TransactionResult(
                success=True,
                signature=signature
            )

        return TransactionResult(
            success=False,
            error="No signature returned"
        )

    except Exception as e:
        logger.error(f"Error sending token transfer: {e}", exc_info=True)
        return TransactionResult(
            success=False,
            error=str(e)
        )


async def confirm_transaction(
    signature: str,
    timeout_seconds: int = 30
) -> bool:
    """
    Wait for transaction confirmation.

    Args:
        signature: Transaction signature.
        timeout_seconds: Maximum wait time.

    Returns:
        True if confirmed, False otherwise.
    """
    import asyncio

    client = get_http_client()
    start_time = asyncio.get_event_loop().time()

    while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
        try:
            response = await client.post(
                settings.helius_rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": "copper-confirm",
                    "method": "getSignatureStatuses",
                    "params": [[signature]]
                }
            )
            response.raise_for_status()
            data = response.json()

            statuses = data.get("result", {}).get("value", [])
            if statuses and statuses[0]:
                status = statuses[0]
                if status.get("confirmationStatus") in ["confirmed", "finalized"]:
                    if status.get("err") is None:
                        logger.info(f"Transaction confirmed: {signature}")
                        return True
                    else:
                        logger.error(f"Transaction failed: {status.get('err')}")
                        return False

            await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error checking transaction status: {e}")
            await asyncio.sleep(1)

    logger.warning(f"Transaction confirmation timeout: {signature}")
    return False
