from __future__ import annotations

import hashlib
import logging
import threading
import time
import uuid
from typing import Any

try:
    from web3 import Web3
except Exception:  # pragma: no cover
    Web3 = None  # type: ignore[assignment]

from core.config import validate_config
from ledger.transaction_store import consistency_check, transaction_store
from payments.nanopayment_service import nanopayment_service
from payments.wallet_service import wallet_service

logger = logging.getLogger("ArcSettlementService")

_CONFIG = validate_config()["config"]
ARC_RPC_URL = str(_CONFIG["ARC"]["rpc_url"])
ARC_CHAIN_ID = int(_CONFIG["ARC"]["chain_id"])
ARC_USDC_CONTRACT_ADDRESS = str(_CONFIG["ARC"]["usdc_contract_address"])
ARC_SETTLEMENT_RETRIES = int(_CONFIG["PAYMENTS"]["settlement_retries"])
ARC_MICROPAYMENT_CAP = int(_CONFIG["PAYMENTS"]["micropayment_cap"])

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
        "stateMutability": "view",
    },
    {
        "constant": False,
        "inputs": [{"name": "recipient", "type": "address"}, {"name": "amount", "type": "uint256"}],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
        "stateMutability": "nonpayable",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
        "stateMutability": "view",
    },
]

if Web3 is not None:
    _web3 = Web3(Web3.HTTPProvider(ARC_RPC_URL))
else:  # pragma: no cover
    _web3 = None


class SettlementService:
    """Escrow-aware settlement service for Arc USDC and Gateway nanopayments."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.escrows: dict[str, dict[str, Any]] = {}
        self.off_chain_balances = wallet_service.balance_registry
        config = validate_config()["config"]
        self.settlement_mode = str(config["PAYMENTS"]["settlement_mode"]).lower()
        self.settlement_retries = int(config["PAYMENTS"]["settlement_retries"])
        self.micropayment_cap = int(config["PAYMENTS"]["micropayment_cap"])
        self.arc_sender_private_key = str(config["ARC"]["sender_private_key"])
        self._rpc_warning_emitted = False

    def arc_rpc_available(self) -> bool:
        if self.settlement_mode == "simulated":
            return False
        if _web3 is None:
            return False
        try:
            return bool(_web3.is_connected())
        except Exception as exc:
            if not self._rpc_warning_emitted:
                logger.warning("arc_rpc_unavailable %s", {"message": str(exc), "rpc_url": ARC_RPC_URL})
                self._rpc_warning_emitted = True
            return False

    def usdc_contract(self):
        if not self.arc_rpc_available():
            return None
        return _web3.eth.contract(address=_web3.to_checksum_address(ARC_USDC_CONTRACT_ADDRESS), abi=ERC20_ABI)

    def generate_tx_hash(self, sender: str, receiver: str, amount: int, metadata: dict[str, Any] | None = None) -> str:
        payload = f"{sender}:{receiver}:{amount}:{time.time_ns()}:{metadata or {}}:{uuid.uuid4()}"
        return "settle_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get_balance(self, wallet_address: str) -> int:
        local_balance = wallet_service.get_balance(wallet_address)
        if local_balance:
            return local_balance
        contract = self.usdc_contract()
        if contract is not None:
            try:
                return int(contract.functions.balanceOf(_web3.to_checksum_address(wallet_address)).call())
            except Exception:
                logger.debug("Arc balance lookup failed for %s, using local fallback.", wallet_address)
        return local_balance

    def validate_balance(self, sender: str, amount: int) -> bool:
        return amount >= 0 and amount <= self.micropayment_cap and self.get_balance(sender) >= amount

    def update_balances(self, sender: str, receiver: str, amount: int) -> tuple[int, int]:
        if not self.validate_balance(sender, amount):
            raise ValueError("Insufficient balance or invalid micropayment amount.")
        sender_balance = self.get_balance(sender) - int(amount)
        receiver_balance = self.get_balance(receiver) + int(amount)
        wallet_service.set_balance(sender, sender_balance)
        wallet_service.set_balance(receiver, receiver_balance)
        return sender_balance, receiver_balance

    def rollback_balances(self, sender: str, receiver: str, amount: int) -> None:
        wallet_service.set_balance(sender, self.get_balance(sender) + int(amount))
        wallet_service.set_balance(receiver, max(0, self.get_balance(receiver) - int(amount)))

    def create_escrow(
        self,
        *,
        job_id: str,
        sender: str,
        receiver: str,
        amount: int,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = metadata or {}
        with self._lock:
            existing_id, existing = self._find_escrow_by_job(job_id)
            if existing_id and existing and existing.get("status") in {"locked", "streaming", "released"}:
                return {"escrow_id": existing_id, **existing}

            escrow_id = f"escrow-{job_id}-{uuid.uuid4().hex[:8]}"
            if not self.validate_balance(sender, amount):
                return {"escrow_id": escrow_id, "status": "failed", "reason": "insufficient_balance", "amount": int(amount)}

            wallet_service.set_balance(sender, self.get_balance(sender) - int(amount))
            escrow = {
                "escrow_id": escrow_id,
                "job_id": job_id,
                "sender": sender,
                "receiver": receiver,
                "amount": int(amount),
                "status": "locked",
                "released_amount": 0,
                "partial_payment_count": 0,
                "metadata": metadata,
                "timestamp": time.time(),
            }
            self.escrows[escrow_id] = escrow
            return dict(escrow)

    def refund_escrow(self, escrow_id: str, reason: str = "processing_failed") -> dict[str, Any]:
        with self._lock:
            escrow = dict(self.escrows.get(escrow_id, {}))
            if not escrow or escrow.get("status") not in {"locked", "streaming"}:
                return {"escrow_id": escrow_id, "status": "missing"}
            remaining_amount = max(0, int(escrow["amount"]) - int(escrow.get("released_amount", 0)))
            wallet_service.set_balance(escrow["sender"], self.get_balance(escrow["sender"]) + remaining_amount)
            escrow["status"] = "refunded"
            escrow["reason"] = reason
            escrow["refunded_amount"] = remaining_amount
            self.escrows[escrow_id] = escrow
            return dict(escrow)

    def create_transaction(
        self,
        *,
        sender: str,
        receiver: str,
        amount: int,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        skip_balance_update: bool = False,
    ) -> dict[str, Any]:
        metadata = metadata or {}
        tx_id = idempotency_key or str(uuid.uuid4())
        existing = transaction_store.get_by_id(tx_id)
        if existing is not None:
            existing["_idempotent_replay"] = True
            return existing

        tx_record = {
            "id": tx_id,
            "job_id": metadata.get("job_id"),
            "sender": sender,
            "receiver": receiver,
            "amount": int(amount),
            "tx_hash": self.generate_tx_hash(sender, receiver, int(amount), metadata),
            "timestamp": time.time(),
            "status": "pending",
            "confidence": float(metadata.get("confidence", 0.0)),
            "expected_value": float(metadata.get("expected_value", 0.0)),
            "latency_ms": 0.0,
            "settlement_latency_ms": 0.0,
            "partial_payment_count": int(metadata.get("partial_payment_count", 1)),
            "chunk_index": int(metadata.get("chunk_index", 1)),
            "total_chunks": int(metadata.get("total_chunks", 1)),
            "cumulative_released": float(metadata.get("cumulative_released", 0.0)),
            "remaining_escrow": float(metadata.get("remaining_escrow", 0.0)),
            "explanation": metadata.get("explanation", ""),
            "metadata": metadata,
        }

        with self._lock:
            check = consistency_check(tx_record, existing_flow=transaction_store.get_job_flow(str(metadata.get("job_id") or "")))
            if not check["valid"]:
                tx_record["status"] = "failed"
                tx_record["error"] = ",".join(check["errors"])
                tx_record["validation"] = check
                logger.warning("transaction_consistency_rejected %s", {"id": tx_id, "errors": check["errors"]})
                return tx_record

            if not skip_balance_update and not self.validate_balance(sender, int(amount)):
                tx_record["status"] = "failed"
                tx_record["error"] = "insufficient_balance"
                try:
                    return transaction_store.add(tx_record)
                except ValueError:
                    replay = transaction_store.get_by_id(tx_id)
                    if replay is not None:
                        replay["_idempotent_replay"] = True
                        return replay
                    raise

            if skip_balance_update:
                wallet_service.set_balance(receiver, self.get_balance(receiver) + int(amount))
            else:
                self.update_balances(sender, receiver, int(amount))
            started_at = time.perf_counter()
            try:
                result = self.simulate_or_send_transaction(
                    sender=sender,
                    receiver=receiver,
                    amount=int(amount),
                    metadata=metadata,
                    idempotency_key=tx_id,
                )
                tx_record["status"] = result["status"]
                tx_record["tx_hash"] = result["tx_hash"]
                tx_record["latency_ms"] = result["latency_ms"]
                tx_record["settlement_latency_ms"] = result["latency_ms"]
            except Exception as exc:
                if skip_balance_update:
                    wallet_service.set_balance(receiver, max(0, self.get_balance(receiver) - int(amount)))
                else:
                    self.rollback_balances(sender, receiver, int(amount))
                tx_record["status"] = "failed"
                tx_record["error"] = str(exc)
                tx_record["latency_ms"] = int((time.perf_counter() - started_at) * 1000)
                tx_record["settlement_latency_ms"] = tx_record["latency_ms"]
                logger.warning(
                    "settlement_failed %s",
                    {"id": tx_id, "sender": sender, "receiver": receiver, "amount": amount, "message": str(exc)},
                )
        logger.info(
            "settlement_record %s",
            {"tx_hash": tx_record["tx_hash"], "sender": sender, "receiver": receiver, "amount": amount, "status": tx_record["status"]},
        )
        try:
            return transaction_store.add(tx_record)
        except ValueError:
            replay = transaction_store.get_by_id(tx_id)
            if replay is not None:
                replay["_idempotent_replay"] = True
                return replay
            raise

    def simulate_or_send_transaction(
        self,
        *,
        sender: str,
        receiver: str,
        amount: int,
        metadata: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for _attempt in range(1, self.settlement_retries + 1):
            try:
                intent = nanopayment_service.create_payment_intent(
                    amount,
                    sender,
                    receiver,
                    idempotency_key=idempotency_key,
                    metadata=metadata,
                )
                signature = wallet_service.sign_transaction(intent, sender)
                executed = nanopayment_service.execute_payment(intent, signature)
                if nanopayment_service.verify_payment(executed):
                    return {
                        "status": "success",
                        "tx_hash": executed["tx_hash"],
                        "amount": float(amount),
                        "latency_ms": int(executed.get("latency_ms", 1)),
                    }
                raise ValueError("nanopayment_verification_failed")
            except Exception as exc:
                last_error = exc
                continue

        contract = self.usdc_contract() if self.settlement_mode in {"arc", "hybrid"} else None
        if contract is not None and self.arc_sender_private_key:
            try:
                started_at = time.perf_counter()
                transfer_fn = contract.functions.transfer(_web3.to_checksum_address(receiver), int(amount))
                tx = {
                    "chainId": _web3.eth.chain_id if self.arc_rpc_available() else ARC_CHAIN_ID,
                    "gas": 100000,
                    "gasPrice": _web3.eth.gas_price,
                    "nonce": _web3.eth.get_transaction_count(_web3.to_checksum_address(sender)),
                }
                raw_tx = transfer_fn.build_transaction(tx)
                signed = _web3.eth.account.sign_transaction(raw_tx, self.arc_sender_private_key)
                sent = _web3.eth.send_raw_transaction(getattr(signed, "raw_transaction", getattr(signed, "rawTransaction", None)))
                return {
                    "status": "success",
                    "tx_hash": _web3.to_hex(sent),
                    "amount": float(amount),
                    "latency_ms": int((time.perf_counter() - started_at) * 1000),
                }
            except Exception as exc:
                last_error = exc
                logger.warning("arc_settlement_failed %s", {"idempotency_key": idempotency_key, "message": str(exc)})
        elif self.settlement_mode in {"arc", "hybrid"}:
            logger.warning("arc_settlement_skipped %s", {"reason": "rpc_or_key_unavailable", "idempotency_key": idempotency_key})

        if last_error is not None:
            raise last_error
        raise ValueError("settlement_failed")

    def release_escrow(self, escrow_id: str) -> dict[str, Any]:
        with self._lock:
            escrow = dict(self.escrows.get(escrow_id, {}))
            if not escrow:
                return {"status": "failed", "reason": "missing_escrow"}
            if escrow.get("status") != "locked":
                return {"status": "failed", "reason": f"invalid_escrow_state:{escrow.get('status')}"}

        metadata = {
            **(escrow.get("metadata") or {}),
            "job_id": escrow.get("job_id"),
            "escrow_id": escrow_id,
            "settlement_phase": "full_release",
            "partial_payment_count": 1,
            "chunk_index": 1,
            "total_chunks": 1,
            "cumulative_released": int(escrow["amount"]),
            "remaining_escrow": 0,
        }
        tx = self.create_transaction(
            sender=escrow["sender"],
            receiver=escrow["receiver"],
            amount=int(escrow["amount"]),
            metadata=metadata,
            idempotency_key=f"release-{escrow_id}",
            skip_balance_update=True,
        )
        if tx.get("status") == "success":
            with self._lock:
                escrow = dict(self.escrows.get(escrow_id, escrow))
                escrow["status"] = "released"
                escrow["released_amount"] = int(escrow["amount"])
                escrow["partial_payment_count"] = 1
                self._assert_escrow_invariants(escrow)
                self.escrows[escrow_id] = escrow
            return tx

        self.refund_escrow(escrow_id, reason="release_failed")
        return tx

    def release_partial(
        self,
        job_id: str,
        amount: int,
        *,
        chunk_index: int = 1,
        total_chunks: int = 1,
    ) -> dict[str, Any]:
        with self._lock:
            escrow_id, escrow = self._find_escrow_by_job(job_id)
            if not escrow_id or not escrow:
                return {"status": "failed", "reason": "missing_escrow", "job_id": job_id}
            if escrow.get("status") not in {"locked", "streaming"}:
                return {"status": "failed", "reason": f"invalid_escrow_state:{escrow.get('status')}", "job_id": job_id}

            expected_chunk_index = int(escrow.get("partial_payment_count", 0)) + 1
            if chunk_index < expected_chunk_index:
                existing_tx = transaction_store.get_by_id(f"partial-{escrow_id}-{chunk_index}")
                if existing_tx is not None:
                    existing_tx["_idempotent_replay"] = True
                    return existing_tx
            if chunk_index != expected_chunk_index:
                return {
                    "status": "failed",
                    "reason": f"invalid_chunk_order:{expected_chunk_index}",
                    "job_id": job_id,
                    "expected_chunk_index": expected_chunk_index,
                }

            remaining = int(escrow["amount"]) - int(escrow.get("released_amount", 0))
            release_amount = min(max(0, int(amount)), remaining)
            if release_amount <= 0:
                return {
                    "status": "failed",
                    "reason": "over_release_attempt",
                    "job_id": job_id,
                    "released_amount": int(escrow.get("released_amount", 0)),
                    "amount": 0,
                }

            metadata = {
                **(escrow.get("metadata") or {}),
                "job_id": job_id,
                "escrow_id": escrow_id,
                "settlement_phase": "partial_release",
                "partial_payment_count": expected_chunk_index,
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
            }
            future_released = int(escrow.get("released_amount", 0)) + release_amount
            metadata["cumulative_released"] = future_released
            metadata["remaining_escrow"] = max(0, int(escrow["amount"]) - future_released)

        tx = self.create_transaction(
            sender=escrow["sender"],
            receiver=escrow["receiver"],
            amount=release_amount,
            metadata=metadata,
            idempotency_key=f"partial-{escrow_id}-{chunk_index}",
            skip_balance_update=True,
        )
        if tx.get("status") != "success":
            return tx

        with self._lock:
            escrow = dict(self.escrows.get(escrow_id, escrow))
            escrow["released_amount"] = int(escrow.get("released_amount", 0)) + release_amount
            escrow["partial_payment_count"] = int(escrow.get("partial_payment_count", 0)) + 1
            escrow["status"] = "released" if escrow["released_amount"] >= int(escrow["amount"]) else "streaming"
            self._assert_escrow_invariants(escrow)
            self.escrows[escrow_id] = escrow
            tx["released_amount"] = escrow["released_amount"]
            tx["remaining_amount"] = max(0, int(escrow["amount"]) - escrow["released_amount"])
            tx["cumulative_released"] = escrow["released_amount"]
            tx["remaining_escrow"] = tx["remaining_amount"]
        return tx

    def seed_balance(self, wallet_address: str, amount: int) -> None:
        wallet_service.set_balance(wallet_address, self.get_balance(wallet_address) + int(amount))

    def deposit(self, wallet_address: str, amount: int, private_key: str | None = None) -> str:
        self.seed_balance(wallet_address, int(amount))
        return self.generate_tx_hash(wallet_address, wallet_address, int(amount), {"kind": "deposit"})

    def _find_escrow_by_job(self, job_id: str) -> tuple[str | None, dict[str, Any] | None]:
        for escrow_id, escrow in self.escrows.items():
            if escrow.get("job_id") == job_id:
                return escrow_id, dict(escrow)
        return None, None

    @staticmethod
    def _assert_escrow_invariants(escrow: dict[str, Any]) -> None:
        released = int(escrow.get("released_amount", 0))
        total = int(escrow.get("amount", 0))
        remaining = total - released
        if released < 0 or released > total:
            raise ValueError("escrow_release_invariant_violation")
        if remaining < 0:
            raise ValueError("escrow_remaining_negative")


settlement_service = SettlementService()
