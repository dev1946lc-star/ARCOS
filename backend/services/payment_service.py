from __future__ import annotations

from core.config import get_int
from payments.settlement_service import settlement_service

DEFAULT_SETTLEMENT_FLOAT = get_int("ARCOS_SEED_BALANCE", 250_000_000)

def get_balance(wallet_address: str) -> int:
    return settlement_service.get_balance(wallet_address)


def deposit(sender_address: str, private_key: str, amount: int) -> str:
    settlement_service.seed_balance(sender_address, int(amount))
    return settlement_service.generate_tx_hash(sender_address, sender_address, int(amount), {"kind": "deposit"})


def pay(sender_address: str, private_key: str, recipient_address: str, amount: int) -> str:
    tx = settlement_service.create_transaction(
        sender=sender_address,
        receiver=recipient_address,
        amount=int(amount),
        metadata={"kind": "direct_payment"},
    )
    return str(tx.get("tx_hash"))


def ensure_seed_balance(wallet_address: str, private_key: str | None = None, amount: int = DEFAULT_SETTLEMENT_FLOAT) -> str:
    settlement_service.seed_balance(wallet_address, int(amount))
    return settlement_service.generate_tx_hash(wallet_address, wallet_address, int(amount), {"kind": "seed"})
