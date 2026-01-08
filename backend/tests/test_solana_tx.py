"""
$COPPER Solana Transaction Tests

Tests for transaction signing, sending, and confirmation logic.
"""

import pytest
import base58
import base64
from decimal import Decimal
from unittest.mock import patch, AsyncMock, MagicMock

from app.utils.solana_tx import (
    keypair_from_base58,
    sign_and_send_transaction,
    send_sol_transfer,
    send_spl_token_transfer,
    confirm_transaction,
    TransactionResult
)


class TestKeypairGeneration:
    """Tests for keypair generation from private keys."""

    def test_valid_keypair_generation(self):
        """Test generating keypair from valid base58 private key."""
        # Generate a test keypair (64 bytes = seed + pubkey)
        from solders.keypair import Keypair

        # Create a real keypair for testing
        real_keypair = Keypair()
        private_key_bytes = bytes(real_keypair)
        private_key_base58 = base58.b58encode(private_key_bytes).decode()

        # Test our function
        result = keypair_from_base58(private_key_base58)

        assert result is not None
        assert result.pubkey() == real_keypair.pubkey()

    def test_invalid_base58_raises_error(self):
        """Test that invalid base58 raises appropriate error."""
        with pytest.raises(Exception):
            keypair_from_base58("not-valid-base58!!!")

    def test_wrong_length_raises_error(self):
        """Test that wrong length private key raises error."""
        # Too short
        short_key = base58.b58encode(b"short").decode()
        with pytest.raises(Exception):
            keypair_from_base58(short_key)


class TestTransactionSigning:
    """Tests for transaction signing and sending."""

    @pytest.mark.asyncio
    async def test_sign_and_send_success(self):
        """Test successful transaction signing and sending."""
        from solders.keypair import Keypair
        from solders.message import MessageV0
        from solders.transaction import VersionedTransaction
        from solders.hash import Hash
        from solders.system_program import transfer, TransferParams

        # Create test keypair
        keypair = Keypair()
        private_key = base58.b58encode(bytes(keypair)).decode()

        # Create a simple transaction
        blockhash = Hash.new_unique()
        ix = transfer(TransferParams(
            from_pubkey=keypair.pubkey(),
            to_pubkey=keypair.pubkey(),
            lamports=1000
        ))
        message = MessageV0.try_compile(
            payer=keypair.pubkey(),
            instructions=[ix],
            address_lookup_table_accounts=[],
            recent_blockhash=blockhash
        )
        tx = VersionedTransaction(message, [keypair])
        serialized = base64.b64encode(bytes(tx)).decode()

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": "5TBx123456789abcdef"
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.utils.solana_tx.get_http_client", return_value=mock_client):
            with patch("app.utils.solana_tx.settings") as mock_settings:
                mock_settings.helius_rpc_url = "https://test-rpc.com"

                result = await sign_and_send_transaction(
                    serialized_tx=serialized,
                    private_key=private_key
                )

                assert result.success is True
                assert result.signature == "5TBx123456789abcdef"

    @pytest.mark.asyncio
    async def test_sign_and_send_rpc_error(self):
        """Test handling of RPC error response."""
        from solders.keypair import Keypair
        from solders.message import MessageV0
        from solders.transaction import VersionedTransaction
        from solders.hash import Hash
        from solders.system_program import transfer, TransferParams

        keypair = Keypair()
        private_key = base58.b58encode(bytes(keypair)).decode()

        blockhash = Hash.new_unique()
        ix = transfer(TransferParams(
            from_pubkey=keypair.pubkey(),
            to_pubkey=keypair.pubkey(),
            lamports=1000
        ))
        message = MessageV0.try_compile(
            payer=keypair.pubkey(),
            instructions=[ix],
            address_lookup_table_accounts=[],
            recent_blockhash=blockhash
        )
        tx = VersionedTransaction(message, [keypair])
        serialized = base64.b64encode(bytes(tx)).decode()

        # Mock error response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": {"message": "Insufficient funds"}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.utils.solana_tx.get_http_client", return_value=mock_client):
            with patch("app.utils.solana_tx.settings") as mock_settings:
                mock_settings.helius_rpc_url = "https://test-rpc.com"

                result = await sign_and_send_transaction(
                    serialized_tx=serialized,
                    private_key=private_key
                )

                assert result.success is False
                assert "Insufficient funds" in result.error


class TestSOLTransfer:
    """Tests for native SOL transfers."""

    @pytest.mark.asyncio
    async def test_sol_transfer_success(self):
        """Test successful SOL transfer."""
        from solders.keypair import Keypair

        keypair = Keypair()
        private_key = base58.b58encode(bytes(keypair)).decode()
        to_address = str(Keypair().pubkey())

        # Mock blockhash response
        blockhash_response = MagicMock()
        blockhash_response.json.return_value = {
            "result": {
                "value": {
                    "blockhash": "4uQeVj5tqViQh7yWWGStvkEG1Zmhx6uasJtWCJziofM"
                }
            }
        }
        blockhash_response.raise_for_status = MagicMock()

        # Mock send response
        send_response = MagicMock()
        send_response.json.return_value = {
            "result": "5TBxABC123signature"
        }
        send_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=[blockhash_response, send_response])

        with patch("app.utils.solana_tx.get_http_client", return_value=mock_client):
            with patch("app.utils.solana_tx.settings") as mock_settings:
                mock_settings.helius_rpc_url = "https://test-rpc.com"

                result = await send_sol_transfer(
                    from_private_key=private_key,
                    to_address=to_address,
                    amount_lamports=100000000  # 0.1 SOL
                )

                assert result.success is True
                assert result.signature is not None

    @pytest.mark.asyncio
    async def test_sol_transfer_blockhash_failure(self):
        """Test SOL transfer when blockhash fetch fails."""
        from solders.keypair import Keypair

        keypair = Keypair()
        private_key = base58.b58encode(bytes(keypair)).decode()
        to_address = str(Keypair().pubkey())

        # Mock blockhash error
        blockhash_response = MagicMock()
        blockhash_response.json.return_value = {
            "error": {"message": "RPC unavailable"}
        }
        blockhash_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=blockhash_response)

        with patch("app.utils.solana_tx.get_http_client", return_value=mock_client):
            with patch("app.utils.solana_tx.settings") as mock_settings:
                mock_settings.helius_rpc_url = "https://test-rpc.com"

                result = await send_sol_transfer(
                    from_private_key=private_key,
                    to_address=to_address,
                    amount_lamports=100000000
                )

                assert result.success is False
                assert "blockhash" in result.error.lower()


class TestSPLTokenTransfer:
    """Tests for SPL token transfers."""

    @pytest.mark.asyncio
    async def test_spl_transfer_creates_ata_if_needed(self):
        """Test that SPL transfer creates ATA if recipient doesn't have one."""
        from solders.keypair import Keypair

        keypair = Keypair()
        private_key = base58.b58encode(bytes(keypair)).decode()
        to_address = str(Keypair().pubkey())
        token_mint = str(Keypair().pubkey())

        # Mock blockhash response
        blockhash_response = MagicMock()
        blockhash_response.json.return_value = {
            "result": {
                "value": {
                    "blockhash": "4uQeVj5tqViQh7yWWGStvkEG1Zmhx6uasJtWCJziofM"
                }
            }
        }
        blockhash_response.raise_for_status = MagicMock()

        # Mock ATA check - doesn't exist
        ata_response = MagicMock()
        ata_response.json.return_value = {
            "result": {"value": None}  # ATA doesn't exist
        }
        ata_response.raise_for_status = MagicMock()

        # Mock send response
        send_response = MagicMock()
        send_response.json.return_value = {
            "result": "5TBxTokenTransferSig"
        }
        send_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(
            side_effect=[blockhash_response, ata_response, send_response]
        )

        with patch("app.utils.solana_tx.get_http_client", return_value=mock_client):
            with patch("app.utils.solana_tx.settings") as mock_settings:
                mock_settings.helius_rpc_url = "https://test-rpc.com"

                result = await send_spl_token_transfer(
                    from_private_key=private_key,
                    to_address=to_address,
                    token_mint=token_mint,
                    amount=1000000000  # 1 token with 9 decimals
                )

                assert result.success is True

    @pytest.mark.asyncio
    async def test_spl_transfer_existing_ata(self):
        """Test SPL transfer when ATA already exists."""
        from solders.keypair import Keypair

        keypair = Keypair()
        private_key = base58.b58encode(bytes(keypair)).decode()
        to_address = str(Keypair().pubkey())
        token_mint = str(Keypair().pubkey())

        # Mock blockhash
        blockhash_response = MagicMock()
        blockhash_response.json.return_value = {
            "result": {"value": {"blockhash": "4uQeVj5tqViQh7yWWGStvkEG1Zmhx6uasJtWCJziofM"}}
        }
        blockhash_response.raise_for_status = MagicMock()

        # Mock ATA check - exists
        ata_response = MagicMock()
        ata_response.json.return_value = {
            "result": {"value": {"data": "somedata"}}  # ATA exists
        }
        ata_response.raise_for_status = MagicMock()

        # Mock send
        send_response = MagicMock()
        send_response.json.return_value = {"result": "5TBxSig123"}
        send_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(
            side_effect=[blockhash_response, ata_response, send_response]
        )

        with patch("app.utils.solana_tx.get_http_client", return_value=mock_client):
            with patch("app.utils.solana_tx.settings") as mock_settings:
                mock_settings.helius_rpc_url = "https://test-rpc.com"

                result = await send_spl_token_transfer(
                    from_private_key=private_key,
                    to_address=to_address,
                    token_mint=token_mint,
                    amount=1000000000
                )

                assert result.success is True


class TestTransactionConfirmation:
    """Tests for transaction confirmation polling."""

    @pytest.mark.asyncio
    async def test_confirm_transaction_success(self):
        """Test successful transaction confirmation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "value": [{
                    "confirmationStatus": "confirmed",
                    "err": None
                }]
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.utils.solana_tx.get_http_client", return_value=mock_client):
            with patch("app.utils.solana_tx.settings") as mock_settings:
                mock_settings.helius_rpc_url = "https://test-rpc.com"

                result = await confirm_transaction(
                    signature="5TBxTestSignature123",
                    timeout_seconds=5
                )

                assert result is True

    @pytest.mark.asyncio
    async def test_confirm_transaction_finalized(self):
        """Test confirmation with finalized status."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "value": [{
                    "confirmationStatus": "finalized",
                    "err": None
                }]
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.utils.solana_tx.get_http_client", return_value=mock_client):
            with patch("app.utils.solana_tx.settings") as mock_settings:
                mock_settings.helius_rpc_url = "https://test-rpc.com"

                result = await confirm_transaction("5TBxSig", timeout_seconds=5)
                assert result is True

    @pytest.mark.asyncio
    async def test_confirm_transaction_with_error(self):
        """Test confirmation when transaction has error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "value": [{
                    "confirmationStatus": "confirmed",
                    "err": {"InstructionError": [0, "InsufficientFunds"]}
                }]
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.utils.solana_tx.get_http_client", return_value=mock_client):
            with patch("app.utils.solana_tx.settings") as mock_settings:
                mock_settings.helius_rpc_url = "https://test-rpc.com"

                result = await confirm_transaction("5TBxSig", timeout_seconds=5)
                assert result is False

    @pytest.mark.asyncio
    async def test_confirm_transaction_timeout(self):
        """Test confirmation timeout."""
        # Return pending status (no confirmation) repeatedly
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "value": [None]  # Not yet confirmed
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.utils.solana_tx.get_http_client", return_value=mock_client):
            with patch("app.utils.solana_tx.settings") as mock_settings:
                mock_settings.helius_rpc_url = "https://test-rpc.com"
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    result = await confirm_transaction(
                        signature="5TBxTimeoutSig",
                        timeout_seconds=2  # Short timeout
                    )
                    # Should timeout and return False
                    assert result is False


class TestTransactionResultDataclass:
    """Tests for TransactionResult dataclass."""

    def test_success_result(self):
        """Test successful result creation."""
        result = TransactionResult(
            success=True,
            signature="5TBxSignature123"
        )
        assert result.success is True
        assert result.signature == "5TBxSignature123"
        assert result.error is None

    def test_failure_result(self):
        """Test failure result creation."""
        result = TransactionResult(
            success=False,
            error="Transaction simulation failed"
        )
        assert result.success is False
        assert result.signature is None
        assert result.error == "Transaction simulation failed"
