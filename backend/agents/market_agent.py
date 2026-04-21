import logging

from services.settlement_service import settlement_service

logger = logging.getLogger("MarketAgent")


class MarketAgent:
    def __init__(self, event_bus=None):
        self.event_bus = event_bus

    def _emit(self, event_type, data):
        if self.event_bus:
            self.event_bus.publish(event_type, data)

    def process_payment(self, job, compute_agent_wallet):
        escrow_id = job.get("escrow_id")
        if not escrow_id:
            payload = self._failed_payload(job, compute_agent_wallet, "missing_escrow")
            self._emit("transaction_created", payload)
            self._emit("payment_sent", payload)
            return payload

        transaction = None
        try:
            transaction = settlement_service.release_escrow(escrow_id)
            logger.info(
                "Transaction created: %s -> %s | %s microUSDC | tx=%s | status=%s",
                str(job.get("creator", job["sender_wallet"]))[:10],
                compute_agent_wallet[:10],
                job["price_offer"],
                transaction.get("tx_hash"),
                transaction.get("status"),
            )
        except Exception as e:
            logger.warning("Settlement failed for job %s: %s", job["task_id"], str(e))

        payload = {
            "tx_hash": (transaction or {}).get("tx_hash", "settlement-error"),
            "sender": job.get("creator", job["sender_wallet"]),
            "recipient": compute_agent_wallet,
            "amount": int(job["price_offer"]),
            "task_id": job["task_id"],
            "status": (transaction or {}).get("status", "failed"),
            "latency_ms": (transaction or {}).get("latency_ms", 0),
            "confidence": float((job.get("intelligence") or {}).get("confidence", job.get("confidence", 0.0))),
            "expected_value": float((job.get("intelligence") or {}).get("expected_value", job.get("expected_value", 0.0))),
        }
        self._emit("transaction_created", payload)
        self._emit("payment_sent", payload)
        return transaction

    def release_partial_payment(self, job, *, amount, chunk_index, total_chunks):
        transaction = settlement_service.release_partial(
            job_id=job.get("task_id"),
            amount=int(amount),
            chunk_index=int(chunk_index),
            total_chunks=int(total_chunks),
        )
        payload = {
            "tx_hash": transaction.get("tx_hash", "settlement-error"),
            "sender": job.get("creator", job["sender_wallet"]),
            "recipient": job.get("compute_wallet"),
            "amount": int(transaction.get("amount", amount)),
            "task_id": job["task_id"],
            "job_id": job["task_id"],
            "status": transaction.get("status", "failed"),
            "latency_ms": transaction.get("latency_ms", 0),
            "settlement_latency_ms": transaction.get("settlement_latency_ms", transaction.get("latency_ms", 0)),
            "confidence": float((job.get("intelligence") or {}).get("confidence", job.get("confidence", 0.0))),
            "expected_value": float((job.get("intelligence") or {}).get("expected_value", job.get("expected_value", 0.0))),
            "chunk_index": int(chunk_index),
            "total_chunks": int(total_chunks),
            "partial_payment_count": int(chunk_index),
            "cumulative_released": float(transaction.get("cumulative_released", 0.0)),
            "remaining_escrow": float(transaction.get("remaining_escrow", 0.0)),
            "explanation": (job.get("explanation") or {}).get("why_accepted", ""),
        }
        self._emit("transaction_created", payload)
        self._emit("payment_sent", payload)
        return transaction

    def lock_escrow(self, job, compute_agent_wallet):
        intelligence = job.get("intelligence") or {}
        escrow = settlement_service.create_escrow(
            job_id=job.get("task_id"),
            sender=job.get("creator", job["sender_wallet"]),
            receiver=compute_agent_wallet,
            amount=int(job["price_offer"]),
            metadata={
                "job_id": job.get("task_id"),
                "confidence": float(intelligence.get("confidence", job.get("confidence", 0.0))),
                "expected_value": float(intelligence.get("expected_value", job.get("expected_value", 0.0))),
                "description": job.get("description"),
                "explanation": (job.get("explanation") or {}).get("why_accepted", ""),
            },
        )
        if escrow.get("status") == "locked":
            job["escrow_id"] = escrow["escrow_id"]
            self._emit(
                "escrow_locked",
                {
                    "task_id": job["task_id"],
                    "escrow_id": escrow["escrow_id"],
                    "sender": escrow["sender"],
                    "recipient": escrow["receiver"],
                    "amount": escrow["amount"],
                },
            )
        return escrow

    def refund_escrow(self, job, reason="processing_failed"):
        escrow_id = job.get("escrow_id")
        if not escrow_id:
            return {"status": "missing"}
        refunded = settlement_service.refund_escrow(escrow_id, reason)
        self._emit(
            "escrow_refunded",
            {
                "task_id": job.get("task_id"),
                "escrow_id": escrow_id,
                "reason": reason,
                "status": refunded.get("status"),
            },
        )
        return refunded

    @staticmethod
    def _failed_payload(job, compute_agent_wallet, reason):
        return {
            "tx_hash": "settlement-error",
            "sender": job.get("creator", job.get("sender_wallet")),
            "recipient": compute_agent_wallet,
            "amount": int(job.get("price_offer", 0)),
            "task_id": job.get("task_id"),
            "status": "failed",
            "reason": reason,
        }
