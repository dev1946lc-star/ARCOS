from __future__ import annotations

import hashlib
import json
import time
import uuid
import urllib.error
import urllib.request
from typing import Any

from core.config import get_env


class WalletService:
    """Circle Wallets adapter with deterministic local fallback."""

    def __init__(self) -> None:
        self.circle_api_key = str(get_env("CIRCLE_API_KEY", "") or "")
        self.circle_wallet_url = str(get_env("CIRCLE_WALLET_API_URL", "https://api.circle.com/v1/w3s/developer/wallets"))
        self.wallet_set_id = str(get_env("CIRCLE_WALLET_SET_ID", "") or "")
        self.entity_secret_ciphertext = str(get_env("CIRCLE_ENTITY_SECRET_CIPHERTEXT", "") or "")
        self.arc_blockchain = str(get_env("CIRCLE_ARC_BLOCKCHAIN", "EVM-ARC"))
        self.wallet_registry: dict[str, dict[str, Any]] = {}
        self.balance_registry: dict[str, int] = {}

    def circle_enabled(self) -> bool:
        return bool(self.circle_api_key and self.wallet_set_id and self.entity_secret_ciphertext)

    def create_wallet(self, owner_name: str, ref_id: str | None = None) -> dict[str, Any]:
        idempotency_key = str(uuid.uuid4())
        if self.circle_enabled():
            payload = {
                "idempotencyKey": idempotency_key,
                "blockchains": [self.arc_blockchain],
                "walletSetId": self.wallet_set_id,
                "entitySecretCiphertext": self.entity_secret_ciphertext,
                "accountType": "SCA",
                "count": 1,
                "metadata": [{"name": owner_name, "refId": ref_id or owner_name}],
            }
            request = urllib.request.Request(
                self.circle_wallet_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.circle_api_key}",
                    "Content-Type": "application/json",
                    "X-Request-Id": idempotency_key,
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=8) as response:
                    body = json.loads(response.read().decode("utf-8"))
                    wallet = (body.get("data") or {}).get("wallets", [{}])[0]
                    result = {
                        "wallet_id": wallet.get("id", str(uuid.uuid4())),
                        "address": wallet.get("address"),
                        "mode": "circle_wallets",
                        "owner": owner_name,
                    }
                    self.wallet_registry[owner_name] = result
                    self.balance_registry.setdefault(str(result["address"]), 0)
                    return result
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                pass

        simulated_address = "0x" + hashlib.sha256(f"{owner_name}:{time.time_ns()}".encode("utf-8")).hexdigest()[:40]
        result = {
            "wallet_id": f"sim-{owner_name.lower()}",
            "address": simulated_address,
            "mode": "simulated_wallet",
            "owner": owner_name,
        }
        self.wallet_registry[owner_name] = result
        self.balance_registry.setdefault(simulated_address, 0)
        return result

    def get_balance(self, address: str) -> int:
        return int(self.balance_registry.get(address, 0))

    def set_balance(self, address: str, amount: int) -> None:
        self.balance_registry[address] = max(0, int(amount))

    def sign_transaction(self, payload: dict[str, Any], address: str) -> str:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "sig_" + hashlib.sha256(f"{address}:{serialized}".encode("utf-8")).hexdigest()


wallet_service = WalletService()
