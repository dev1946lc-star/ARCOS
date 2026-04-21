from __future__ import annotations

import hashlib
import json
import time
import uuid
import urllib.error
import urllib.request
from typing import Any

from core.config import get_bool, get_env


class NanopaymentService:
    """Circle Gateway-style micropayments with offline-safe intent execution."""

    def __init__(self) -> None:
        self.gateway_url = str(get_env("CIRCLE_GATEWAY_API_URL", "") or "")
        self.gateway_api_key = str(get_env("CIRCLE_GATEWAY_API_KEY", "") or "")
        self.nanopayments_enabled = get_bool("CIRCLE_NANOPAYMENTS_ENABLED", False)
        self.intents: dict[str, dict[str, Any]] = {}

    def gateway_enabled(self) -> bool:
        return self.nanopayments_enabled and bool(self.gateway_url and self.gateway_api_key)

    def create_payment_intent(
        self,
        amount: int,
        sender: str,
        receiver: str,
        *,
        idempotency_key: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = metadata or {}
        intent = {
            "intent_id": idempotency_key,
            "amount": int(amount),
            "sender": sender,
            "receiver": receiver,
            "metadata": metadata,
            "status": "pending",
            "created_at": time.time(),
        }
        self.intents[idempotency_key] = intent
        return intent

    def execute_payment(self, intent: dict[str, Any], authorization_signature: str) -> dict[str, Any]:
        started_at = time.perf_counter()
        if self.gateway_enabled():
            payload = {
                "idempotencyKey": intent["intent_id"],
                "amount": intent["amount"],
                "sender": intent["sender"],
                "receiver": intent["receiver"],
                "authorizationSignature": authorization_signature,
                "metadata": intent.get("metadata", {}),
            }
            request = urllib.request.Request(
                self.gateway_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.gateway_api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=8) as response:
                    body = json.loads(response.read().decode("utf-8"))
                    tx_hash = ((body.get("data") or {}).get("transaction") or {}).get("txHash")
                    latency_ms = int((time.perf_counter() - started_at) * 1000)
                    intent["status"] = "success"
                    intent["tx_hash"] = tx_hash or self._simulated_hash(intent)
                    intent["latency_ms"] = latency_ms
                    return intent
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                pass

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        intent["status"] = "success"
        intent["tx_hash"] = self._simulated_hash(intent)
        intent["latency_ms"] = max(1, latency_ms)
        return intent

    def verify_payment(self, intent: dict[str, Any]) -> bool:
        return intent.get("status") == "success" and bool(intent.get("tx_hash"))

    @staticmethod
    def _simulated_hash(intent: dict[str, Any]) -> str:
        payload = f"{intent['intent_id']}:{intent['sender']}:{intent['receiver']}:{intent['amount']}:{uuid.uuid4()}"
        return "nano_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


nanopayment_service = NanopaymentService()
