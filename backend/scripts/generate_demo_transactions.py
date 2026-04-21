from __future__ import annotations

import json
import time
import urllib.request


BASE_URL = "http://127.0.0.1:8000"


def fetch_json(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    started_at = time.time()
    spike = fetch_json("/spike")
    print(json.dumps({"event": "spike_triggered", "payload": spike, "timestamp": started_at}, indent=2))

    for _ in range(20):
        time.sleep(1.0)
        transactions = fetch_json("/transactions")
        count = int((transactions.get("summary") or {}).get("total_transactions", 0))
        if count >= 50:
            break

    transactions = fetch_json("/transactions")
    stats = fetch_json("/stats")
    preview = [
        {
            "timestamp": tx.get("timestamp"),
            "tx_hash": tx.get("tx_hash"),
            "amount": tx.get("amount"),
            "status": tx.get("status"),
            "job_id": tx.get("job_id"),
            "pricing": (tx.get("metadata") or {}),
        }
        for tx in (transactions.get("transactions") or [])[:10]
    ]
    print(json.dumps({"event": "demo_summary", "stats": stats, "transaction_preview": preview}, indent=2))


if __name__ == "__main__":
    main()
