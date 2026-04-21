from __future__ import annotations

import json
import logging
import queue
import sqlite3
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

from core.config import validate_config
from store.supabase_client import supabase_client, to_supabase_row

logger = logging.getLogger("ARCOS.TransactionStore")


def consistency_check(
    transaction: dict[str, Any],
    existing_flow: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    record = dict(transaction)
    errors: list[str] = []
    warnings: list[str] = []

    tx_id = str(record.get("id") or "").strip()
    sender = str(record.get("sender") or "").strip()
    receiver = str(record.get("receiver") or "").strip()
    amount = float(record.get("amount", 0.0) or 0.0)
    chunk_index = int(record.get("chunk_index", 1) or 1)
    total_chunks = int(record.get("total_chunks", 1) or 1)
    cumulative_released = float(record.get("cumulative_released", 0.0) or 0.0)
    remaining_escrow = float(record.get("remaining_escrow", 0.0) or 0.0)
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    settlement_phase = str((metadata or {}).get("settlement_phase") or "")

    if not tx_id:
        errors.append("missing_transaction_id")
    if not sender:
        errors.append("missing_sender")
    if not receiver:
        errors.append("missing_receiver")
    if amount < 0:
        errors.append("negative_amount")
    if chunk_index < 1:
        errors.append("invalid_chunk_index")
    if total_chunks < 1 or chunk_index > total_chunks:
        errors.append("invalid_total_chunks")
    if cumulative_released < 0 or remaining_escrow < 0:
        errors.append("negative_escrow_totals")

    ordered_flow = sorted(
        (dict(item) for item in (existing_flow or [])),
        key=lambda tx: (float(tx.get("timestamp", 0.0)), int(tx.get("chunk_index", 0)), str(tx.get("id", ""))),
    )
    if ordered_flow:
        seen_ids = {str(item.get("id", "")) for item in ordered_flow}
        if tx_id in seen_ids:
            errors.append("duplicate_transaction_id")
        last = ordered_flow[-1]
        last_chunk = int(last.get("chunk_index", 0) or 0)
        last_cumulative = float(last.get("cumulative_released", 0.0) or 0.0)
        if chunk_index < last_chunk:
            errors.append("out_of_order_chunk")
        if chunk_index > last_chunk + 1 and settlement_phase == "partial_release":
            errors.append("chunk_gap_detected")
        if cumulative_released and cumulative_released < last_cumulative:
            errors.append("non_monotonic_cumulative_release")
        if settlement_phase == "full_release" and any(
            str((item.get("metadata") or {}).get("settlement_phase", "")) == "partial_release" for item in ordered_flow
        ):
            warnings.append("full_release_after_partial_stream")

    return {"valid": not errors, "errors": errors, "warnings": warnings}


def validate_replay_flow(job_id: str, flow: list[dict[str, Any]]) -> dict[str, Any]:
    issues: list[str] = []
    seen_ids: set[str] = set()
    previous_chunk = 0
    previous_cumulative = 0.0
    for tx in flow:
        tx_id = str(tx.get("id", ""))
        if tx_id in seen_ids:
            issues.append(f"duplicate_id:{tx_id}")
        seen_ids.add(tx_id)
        chunk_index = int(tx.get("chunk_index", 1) or 1)
        cumulative = float(tx.get("cumulative_released", 0.0) or 0.0)
        if chunk_index < previous_chunk:
            issues.append(f"out_of_order_chunk:{tx_id}")
        if chunk_index > previous_chunk + 1 and chunk_index > 1:
            issues.append(f"chunk_gap:{tx_id}")
        if cumulative < previous_cumulative:
            issues.append(f"non_monotonic_cumulative:{tx_id}")
        previous_chunk = max(previous_chunk, chunk_index)
        previous_cumulative = max(previous_cumulative, cumulative)
    return {"job_id": job_id, "valid": not issues, "issues": issues}


class TransactionStore:
    """In-memory-first append-only ledger with bounded async secondary persistence."""

    def __init__(self, sqlite_path: str | None = None, max_in_memory: int | None = None) -> None:
        settings = validate_config()["config"]
        economy = settings["ECONOMY"]
        database = settings["DATABASE"]

        self._transactions: list[dict[str, Any]] = []
        self._transaction_ids: set[str] = set()
        self._max_in_memory = max(100, int(max_in_memory or economy["max_transactions"]))
        self._lock = threading.RLock()
        self._metrics_lock = threading.Lock()
        self.sqlite_path = sqlite_path or database["sqlite_path"]
        self._conn: sqlite3.Connection | None = None
        self._supabase = supabase_client
        self._supabase.reload_config()
        self._use_supabase = bool(database["supabase_write_enabled"] and self._supabase.is_enabled())
        self._backpressure_enabled = bool(database["enable_backpressure"])
        self._max_persistence_backlog = int(database["max_persistence_backlog"])
        self._local_queue_limit = min(int(database["persistence_queue_size"]), self._max_persistence_backlog)
        self._persistence_queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=self._local_queue_limit)
        self._persistence_worker = threading.Thread(target=self._persistence_loop, name="transaction-store-writer", daemon=True)
        self._persisted_count = 0
        self._persistence_drop_count = 0
        self._local_drop_count = 0
        self._last_persist_success_at: float | None = None
        self._last_persist_failure_at: float | None = None
        self._oldest_persisted_pending_at: float | None = None
        self._persistence_attempted = 0
        self._persistence_drop_reasons = {
            "sampling": 0,
            "backpressure": 0,
            "oversize": 0,
            "retry_failure": 0,
        }
        self._tx_timestamps: deque[float] = deque()
        self._persist_success_timestamps: deque[float] = deque()
        self._peak_tx_per_second = 0.0
        self._peak_persistence_writes_per_second = 0.0
        self._total_persist_latency_ms = 0.0
        self._persist_latency_samples = 0
        self._persistence_worker.start()
        if self.sqlite_path:
            self._init_sqlite(self.sqlite_path)

    def _init_sqlite(self, sqlite_path: str) -> None:
        path = Path(sqlite_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                job_id TEXT,
                sender TEXT NOT NULL,
                receiver TEXT NOT NULL,
                amount INTEGER NOT NULL,
                tx_hash TEXT NOT NULL,
                timestamp REAL NOT NULL,
                status TEXT NOT NULL,
                confidence REAL,
                expected_value REAL,
                latency_ms REAL,
                settlement_latency_ms REAL,
                partial_payment_count INTEGER,
                chunk_index INTEGER,
                total_chunks INTEGER,
                cumulative_released REAL,
                remaining_escrow REAL,
                explanation TEXT,
                metadata TEXT
            )
            """
        )
        self._conn.commit()

    def add(self, transaction: dict[str, Any]) -> dict[str, Any]:
        record = self._serialize_record(transaction)
        with self._lock:
            if record["id"] in self._transaction_ids:
                raise ValueError(f"duplicate_transaction_id:{record['id']}")
            existing_flow = [tx for tx in self._transactions if tx.get("job_id") == record.get("job_id")] if record.get("job_id") else []
            check = consistency_check(record, existing_flow=existing_flow)
            if not check["valid"]:
                raise ValueError("transaction_consistency_failed:" + ",".join(check["errors"]))
            self._transactions.append(record)
            self._transaction_ids.add(record["id"])
            if len(self._transactions) > self._max_in_memory:
                removed = self._transactions[:-self._max_in_memory]
                self._transactions = self._transactions[-self._max_in_memory :]
                for item in removed:
                    self._transaction_ids.discard(str(item.get("id", "")))
        self._record_transaction_timestamp(record["timestamp"])
        self._schedule_persist(record)
        return dict(record)

    def get_by_id(self, transaction_id: str) -> dict[str, Any] | None:
        with self._lock:
            for tx in reversed(self._transactions):
                if tx.get("id") == transaction_id:
                    return dict(tx)
        persisted = self._load_persisted_transactions()
        for tx in reversed(persisted):
            if tx.get("id") == transaction_id:
                return dict(tx)
        return None

    def list_transactions(self, limit: int | None = None) -> list[dict[str, Any]]:
        with self._lock:
            records = sorted(
                (dict(tx) for tx in self._transactions),
                key=lambda tx: (float(tx.get("timestamp", 0.0)), int(tx.get("chunk_index", 0)), str(tx.get("id", ""))),
            )
        if not records:
            records = self._load_persisted_transactions(limit=limit)
        if limit is None:
            return records
        return records[-max(0, int(limit)) :]

    def clear(self) -> None:
        with self._lock:
            self._transactions.clear()
            self._transaction_ids.clear()
        with self._metrics_lock:
            self._tx_timestamps.clear()

    def get_job_flow(self, job_id: str) -> list[dict[str, Any]]:
        with self._lock:
            records = [dict(tx) for tx in self._transactions if tx.get("job_id") == job_id]
        if not records:
            records = self._load_persisted_transactions(job_id=job_id, include_supabase=False)
        return sorted(records, key=lambda tx: (float(tx.get("timestamp", 0.0)), int(tx.get("chunk_index", 0)), str(tx.get("id", ""))))

    def replay_job(self, job_id: str) -> dict[str, Any]:
        flow = self.get_job_flow(job_id)
        if not flow:
            return {"job_id": job_id, "flow": [], "status": "missing", "validation": {"job_id": job_id, "valid": True, "issues": []}}
        validation = validate_replay_flow(job_id, flow)
        total_escrow = max((float(tx.get("amount", 0.0)) + float(tx.get("remaining_escrow", 0.0)) for tx in flow), default=0.0)
        released = max((float(tx.get("cumulative_released", 0.0)) for tx in flow), default=0.0)
        final_status = flow[-1].get("status", "unknown")
        return {
            "job_id": job_id,
            "status": final_status,
            "total_escrow": total_escrow,
            "released_total": released,
            "remaining_escrow": max(0.0, total_escrow - released),
            "partial_payment_count": len(flow),
            "flow": flow,
            "validation": validation,
        }

    def replay_balances(self) -> dict[str, float]:
        balances: dict[str, float] = {}
        for tx in sorted(self.list_transactions(), key=lambda item: (float(item.get("timestamp", 0.0)), str(item.get("id", "")))):
            if tx.get("status") != "success":
                continue
            sender = str(tx.get("sender", ""))
            receiver = str(tx.get("receiver", ""))
            amount = float(tx.get("amount", 0.0))
            balances[sender] = balances.get(sender, 0.0) - amount
            balances[receiver] = balances.get(receiver, 0.0) + amount
        return balances

    def snapshot(self) -> dict[str, Any]:
        transactions = self.list_transactions()
        return {"count": len(transactions), "summary": self.summary_stats(), "balances": self.replay_balances()}

    def rebuild_from_ledger(self) -> dict[str, Any]:
        transactions = self.list_transactions()
        return {
            "transactions": transactions,
            "balances": self.replay_balances(),
            "summary": self.summary_stats(),
        }

    def summary_stats(self) -> dict[str, Any]:
        transactions = self.list_transactions()
        total = len(transactions)
        successful = [tx for tx in transactions if tx.get("status") == "success"]
        amounts = [float(tx.get("amount", 0.0)) for tx in successful]
        latencies = [
            float(tx.get("settlement_latency_ms", tx.get("latency_ms", 0.0)))
            for tx in successful
            if tx.get("settlement_latency_ms", tx.get("latency_ms")) is not None
        ]
        timestamps = [float(tx.get("timestamp", 0.0)) for tx in transactions]
        elapsed = max((max(timestamps) - min(timestamps)), 1e-9) if len(timestamps) > 1 else 0.0
        throughput = (total / elapsed) if elapsed > 0 else float(total)
        return {
            "total_transactions": total,
            "avg_transaction_value": round(sum(amounts) / len(amounts), 6) if amounts else 0.0,
            "throughput": round(throughput, 4),
            "transaction_rate": round(throughput, 4),
            "tx_per_second": round(throughput, 4),
            "success_rate": round(len(successful) / total, 4) if total else 0.0,
            "avg_settlement_time": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
            "storage_mode": self.storage_mode(),
            "in_memory_transactions": len(self._transactions),
            "persistence_backlog": self.persistence_backlog(),
            "persistence_lag_ms": self.persistence_lag_ms(),
            "dropped_persistence_writes": self._persistence_drop_count,
            "write_drop_count": self.write_drop_count(),
            "queue_utilization": self.queue_utilization(),
        }

    def storage_mode(self) -> str:
        if self._use_supabase and self._conn is not None:
            return "hybrid"
        if self._use_supabase:
            return "memory+supabase"
        if self._conn is not None:
            return "memory+sqlite"
        return "memory"

    def runtime_mode(self) -> str:
        if self._use_supabase or self._conn is not None:
            return "hybrid"
        return "memory_only"

    def fallback_mode(self) -> bool:
        supabase = self._supabase.status() if self._use_supabase else {"status": "offline"}
        return bool(self._use_supabase and supabase.get("status") != "ok")

    def persistence_backlog(self) -> int:
        return self._persistence_queue.qsize() + (self._supabase.queue_backlog() if self._use_supabase else 0)

    def queue_utilization(self) -> float:
        remote_capacity = int(getattr(self._supabase, "max_backlog", 0)) if self._use_supabase else 0
        total_capacity = self._local_queue_limit + remote_capacity
        if total_capacity <= 0:
            return 0.0
        return round(min(1.0, self.persistence_backlog() / total_capacity), 4)

    def write_drop_count(self) -> int:
        remote_drops = int(self._supabase.status().get("dropped_writes", 0)) if self._use_supabase else 0
        return self._persistence_drop_count + remote_drops

    def persistence_lag_ms(self) -> float:
        local_age = 0.0
        if self._oldest_persisted_pending_at is not None:
            local_age = max(0.0, (time.time() - self._oldest_persisted_pending_at) * 1000)
        remote_age = self._supabase.oldest_pending_age_ms() if self._use_supabase else 0.0
        return round(max(local_age, remote_age), 3)

    def persistence_status(self, *, refresh: bool = False) -> dict[str, Any]:
        supabase_status = (
            self._supabase.ping() if refresh and self._use_supabase else
            self._supabase.status() if self._use_supabase else
            {"connected": False, "status": "offline", "message": "disabled"}
        )
        persistence_metrics = self.persistence_metrics(refresh=refresh)
        return {
            "storage_mode": self.storage_mode(),
            "mode": self.runtime_mode(),
            "persistence_mode": self.runtime_mode(),
            "sqlite_enabled": self._conn is not None,
            "supabase_enabled": self._use_supabase,
            "supabase_status": supabase_status,
            "queue_backlog": self.persistence_backlog(),
            "queue_utilization": self.queue_utilization(),
            "persistence_lag_ms": self.persistence_lag_ms(),
            "fallback_mode": self.fallback_mode(),
            "dropped_persistence_writes": self._persistence_drop_count,
            "write_drop_count": self.write_drop_count(),
            "write_sampling_rate": supabase_status.get("write_sampling_rate", 0.0 if not self._use_supabase else 1.0),
            "drop_reasons": persistence_metrics["drop_reasons"],
            "writes_attempted": persistence_metrics["writes_attempted"],
            "writes_successful": persistence_metrics["writes_successful"],
            "writes_dropped": persistence_metrics["writes_dropped"],
            "avg_batch_size": persistence_metrics["avg_batch_size"],
            "avg_write_latency_ms": persistence_metrics["avg_write_latency_ms"],
        }

    def _schedule_persist(self, record: dict[str, Any]) -> None:
        if self._conn is None and not self._use_supabase:
            return
        with self._metrics_lock:
            self._persistence_attempted += 1
        payload = dict(record)
        payload["_queued_at"] = time.time()
        if self._backpressure_enabled and self.persistence_backlog() >= self._max_persistence_backlog:
            if not self._drop_oldest_local():
                with self._metrics_lock:
                    self._persistence_drop_count += 1
                    self._persistence_drop_reasons["backpressure"] += 1
                return
        try:
            self._persistence_queue.put_nowait(payload)
            if self._oldest_persisted_pending_at is None:
                self._oldest_persisted_pending_at = payload["_queued_at"]
        except queue.Full:
            if self._drop_oldest_local():
                try:
                    self._persistence_queue.put_nowait(payload)
                    self._refresh_local_pending_age()
                    return
                except queue.Full:
                    pass
            with self._metrics_lock:
                self._persistence_drop_count += 1
                self._persistence_drop_reasons["backpressure"] += 1
            logger.warning(
                "transaction_persist_queue_full %s",
                {"transaction_id": payload.get("id"), "queue_backlog": self._persistence_queue.qsize()},
            )

    def _drop_oldest_local(self) -> bool:
        dropped: dict[str, Any] | None = None
        with self._persistence_queue.mutex:
            if self._persistence_queue.queue:
                dropped = self._persistence_queue.queue.popleft()
                self._persistence_queue.unfinished_tasks = max(0, self._persistence_queue.unfinished_tasks - 1)
                self._persistence_queue.not_full.notify()
        if dropped is None:
            return False
        with self._metrics_lock:
            self._local_drop_count += 1
            self._persistence_drop_count += 1
            self._persistence_drop_reasons["backpressure"] += 1
        logger.warning(
            "transaction_persist_dropped %s",
            {"transaction_id": dropped.get("id"), "reason": "backlog_protection"},
        )
        self._refresh_local_pending_age()
        return True

    def _persistence_loop(self) -> None:
        while True:
            try:
                record = self._persistence_queue.get(timeout=0.25)
            except queue.Empty:
                continue
            try:
                started_at = time.perf_counter()
                self._persist_record(record)
                elapsed_ms = (time.perf_counter() - started_at) * 1000
                with self._metrics_lock:
                    self._persisted_count += 1
                    self._total_persist_latency_ms += elapsed_ms
                    self._persist_latency_samples += 1
                self._last_persist_success_at = time.time()
                self._record_persist_success()
            except Exception as exc:
                self._last_persist_failure_at = time.time()
                logger.warning(
                    "transaction_persist_failed %s",
                    {"transaction_id": record.get("id"), "message": str(exc)},
                )
            finally:
                self._persistence_queue.task_done()
                self._refresh_local_pending_age()

    def _refresh_local_pending_age(self) -> None:
        if self._persistence_queue.empty():
            self._oldest_persisted_pending_at = None
            return
        with self._persistence_queue.mutex:
            queued = list(self._persistence_queue.queue)
        timestamps = [float(item.get("_queued_at", time.time())) for item in queued if isinstance(item, dict)]
        self._oldest_persisted_pending_at = min(timestamps) if timestamps else None

    def _persist_record(self, record: dict[str, Any]) -> None:
        materialized = {key: value for key, value in record.items() if key != "_queued_at"}
        if self._conn is not None:
            self._persist_sqlite(materialized)
        if self._use_supabase:
            self._supabase.insert_transaction(to_supabase_row(materialized))

    def _persist_sqlite(self, record: dict[str, Any]) -> None:
        with self._lock:
            if self._conn is None:
                return
            self._conn.execute(
                """
                INSERT OR IGNORE INTO transactions
                (id, job_id, sender, receiver, amount, tx_hash, timestamp, status, confidence, expected_value, latency_ms, settlement_latency_ms, partial_payment_count, chunk_index, total_chunks, cumulative_released, remaining_escrow, explanation, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.get("id"),
                    record.get("job_id"),
                    record.get("sender"),
                    record.get("receiver"),
                    int(record.get("amount", 0)),
                    record.get("tx_hash"),
                    float(record.get("timestamp", time.time())),
                    record.get("status"),
                    float(record.get("confidence", 0.0)),
                    float(record.get("expected_value", 0.0)),
                    float(record.get("latency_ms", 0.0)),
                    float(record.get("settlement_latency_ms", record.get("latency_ms", 0.0))),
                    int(record.get("partial_payment_count", 1)),
                    int(record.get("chunk_index", 1)),
                    int(record.get("total_chunks", 1)),
                    float(record.get("cumulative_released", 0.0)),
                    float(record.get("remaining_escrow", 0.0)),
                    str(record.get("explanation", "")),
                    json.dumps(record.get("metadata", {}), sort_keys=True),
                ),
            )
            self._conn.commit()

    def _load_persisted_transactions(
        self,
        *,
        limit: int | None = None,
        job_id: str | None = None,
        include_supabase: bool = True,
    ) -> list[dict[str, Any]]:
        if include_supabase and self._use_supabase:
            records = self._supabase.fetch_transactions(limit=limit, job_id=job_id)
            if records:
                return self._normalize_records(records)
        if self._conn is None:
            return []
        query = """
            SELECT id, job_id, sender, receiver, amount, tx_hash, timestamp, status, confidence, expected_value,
                   latency_ms, settlement_latency_ms, partial_payment_count, chunk_index, total_chunks,
                   cumulative_released, remaining_escrow, explanation, metadata
            FROM transactions
        """
        params: list[Any] = []
        clauses: list[str] = []
        if job_id:
            clauses.append("job_id = ?")
            params.append(job_id)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY timestamp ASC, chunk_index ASC, id ASC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(int(limit))
        with self._lock:
            rows = self._conn.execute(query, params).fetchall() if self._conn is not None else []
        return self._normalize_records(
            [
                {
                    "id": row[0],
                    "job_id": row[1],
                    "sender": row[2],
                    "receiver": row[3],
                    "amount": row[4],
                    "tx_hash": row[5],
                    "timestamp": row[6],
                    "status": row[7],
                    "confidence": row[8],
                    "expected_value": row[9],
                    "latency_ms": row[10],
                    "settlement_latency_ms": row[11],
                    "partial_payment_count": row[12],
                    "chunk_index": row[13],
                    "total_chunks": row[14],
                    "cumulative_released": row[15],
                    "remaining_escrow": row[16],
                    "explanation": row[17],
                    "metadata": json.loads(row[18] or "{}"),
                }
                for row in rows
            ]
        )

    @staticmethod
    def _serialize_record(record: dict[str, Any]) -> dict[str, Any]:
        metadata = record.get("metadata", {}) or {}
        return {
            "id": str(record.get("id") or ""),
            "job_id": record.get("job_id"),
            "sender": str(record.get("sender") or ""),
            "receiver": str(record.get("receiver") or ""),
            "amount": int(record.get("amount", 0)),
            "tx_hash": str(record.get("tx_hash") or ""),
            "timestamp": float(record.get("timestamp", time.time())),
            "status": str(record.get("status") or "pending"),
            "confidence": float(record.get("confidence", 0.0)),
            "expected_value": float(record.get("expected_value", 0.0)),
            "latency_ms": float(record.get("latency_ms", 0.0)),
            "settlement_latency_ms": float(record.get("settlement_latency_ms", record.get("latency_ms", 0.0))),
            "partial_payment_count": int(record.get("partial_payment_count", 1)),
            "chunk_index": int(record.get("chunk_index", 1)),
            "total_chunks": int(record.get("total_chunks", 1)),
            "cumulative_released": float(record.get("cumulative_released", 0.0)),
            "remaining_escrow": float(record.get("remaining_escrow", 0.0)),
            "explanation": str(record.get("explanation", "")),
            "metadata": metadata if isinstance(metadata, dict) else {},
        }

    @staticmethod
    def _normalize_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        for record in records:
            entry = dict(record)
            metadata = entry.get("metadata")
            if isinstance(metadata, str):
                try:
                    entry["metadata"] = json.loads(metadata)
                except json.JSONDecodeError:
                    entry["metadata"] = {}
            check = consistency_check(entry)
            if not check["valid"]:
                entry.setdefault("_validation_errors", check["errors"])
            normalized.append(TransactionStore._serialize_record(entry))
        return sorted(
            normalized,
            key=lambda tx: (float(tx.get("timestamp", 0.0)), int(tx.get("chunk_index", 0)), str(tx.get("id", ""))),
        )

    def persistence_metrics(self, *, refresh: bool = False) -> dict[str, Any]:
        if refresh and self._use_supabase:
            self._supabase.ping()
        supabase_metrics = self._supabase.metrics_snapshot() if self._use_supabase else {}
        with self._metrics_lock:
            local_attempted = self._persistence_attempted
            local_drop_reasons = dict(self._persistence_drop_reasons)
            local_avg_latency = round(self._total_persist_latency_ms / self._persist_latency_samples, 3) if self._persist_latency_samples else 0.0
            persistence_writes_per_second = self._current_persistence_writes_per_second_locked()
            peak_persistence_wps = round(self._peak_persistence_writes_per_second, 4)
        combined_drop_reasons = {
            "sampling": local_drop_reasons["sampling"] + int((supabase_metrics.get("drop_reasons") or {}).get("sampling", 0)),
            "backpressure": local_drop_reasons["backpressure"] + int((supabase_metrics.get("drop_reasons") or {}).get("backpressure", 0)),
            "oversize": local_drop_reasons["oversize"] + int((supabase_metrics.get("drop_reasons") or {}).get("oversize", 0)),
            "retry_failure": local_drop_reasons["retry_failure"] + int((supabase_metrics.get("drop_reasons") or {}).get("retry_failure", 0)),
        }
        writes_dropped = sum(combined_drop_reasons.values())
        writes_successful = max(0, local_attempted - writes_dropped)
        return {
            "mode": self.runtime_mode(),
            "write_sampling_rate": float(supabase_metrics.get("write_sampling_rate", 1.0)),
            "writes_attempted": local_attempted,
            "writes_successful": writes_successful,
            "writes_dropped": writes_dropped,
            "drop_reasons": combined_drop_reasons,
            "queue_size": self.persistence_backlog(),
            "queue_utilization": self.queue_utilization(),
            "avg_batch_size": float(supabase_metrics.get("avg_batch_size", 1.0 if writes_successful else 0.0)),
            "avg_write_latency_ms": float(supabase_metrics.get("avg_write_latency_ms", local_avg_latency)),
            "persistence_writes_per_second": persistence_writes_per_second,
            "peak_persistence_writes_per_second": peak_persistence_wps,
        }

    def performance_metrics(self, *, event_log: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        with self._metrics_lock:
            tx_per_second = self._current_tx_per_second_locked()
            peak_tx_per_second = round(self._peak_tx_per_second, 4)
        persistence = self.persistence_metrics()
        avg_job_latency_ms = self._average_job_latency_ms(event_log or [])
        return {
            "tx_per_second": tx_per_second,
            "persistence_writes_per_second": persistence["persistence_writes_per_second"],
            "avg_job_processing_latency_ms": avg_job_latency_ms,
            "peak_throughput_observed": peak_tx_per_second,
            "peak_persistence_writes_per_second": persistence["peak_persistence_writes_per_second"],
        }

    def validation_snapshot(self, *, event_log: list[dict[str, Any]] | None = None, balances: dict[str, float] | None = None) -> dict[str, Any]:
        with self._lock:
            memory_transactions = [dict(tx) for tx in self._transactions]
        persisted_transactions = self._load_persisted_transactions(include_supabase=True)
        duplicate_ids = self._count_duplicate_ids(memory_transactions + persisted_transactions)
        replay_valid = self._replay_integrity_ok(memory_transactions)
        negative_balance_count = sum(1 for amount in (balances or {}).values() if float(amount) < 0)
        consistency_ok = duplicate_ids == 0 and replay_valid and negative_balance_count == 0
        return {
            "memory_tx_count": len(memory_transactions),
            "persisted_tx_count": len({str(tx.get("id", "")) for tx in persisted_transactions if tx.get("id")}),
            "consistency_ok": consistency_ok,
            "duplicate_ids": duplicate_ids,
            "negative_balances": negative_balance_count,
            "replay_valid": replay_valid,
        }

    def simulate_overload(self, *, burst_size: int = 200, queue_limit: int = 32, processing_delay_ms: int = 15) -> dict[str, Any]:
        sim_queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=max(1, int(queue_limit)))
        dropped = 0
        processed = 0
        stop_event = threading.Event()
        peak_queue = 0

        def worker() -> None:
            nonlocal processed
            while not stop_event.is_set() or not sim_queue.empty():
                try:
                    sim_queue.get(timeout=0.05)
                except queue.Empty:
                    continue
                time.sleep(max(0.0, processing_delay_ms) / 1000.0)
                processed += 1
                sim_queue.task_done()

        worker_thread = threading.Thread(target=worker, name="overload-sim", daemon=True)
        worker_thread.start()
        loop = time.perf_counter()
        for index in range(max(1, int(burst_size))):
            payload = {"id": f"overload-{index}", "timestamp": time.time()}
            if sim_queue.qsize() >= sim_queue.maxsize:
                try:
                    sim_queue.get_nowait()
                    sim_queue.task_done()
                    dropped += 1
                except queue.Empty:
                    dropped += 1
            try:
                sim_queue.put_nowait(payload)
                peak_queue = max(peak_queue, sim_queue.qsize())
            except queue.Full:
                dropped += 1
        sim_queue.join()
        stop_event.set()
        worker_thread.join(timeout=1.0)
        elapsed = max(time.perf_counter() - loop, 1e-6)
        peak_tps = round(max(1, burst_size) / elapsed, 4)
        event_loop_probe_started = time.perf_counter()
        time.sleep(0)
        event_loop_blocked = (time.perf_counter() - event_loop_probe_started) > 0.05
        return {
            "burst_size": int(burst_size),
            "peak_tps": peak_tps,
            "writes_dropped": dropped,
            "system_stable": processed > 0 and worker_thread.is_alive() is False,
            "event_loop_blocked": event_loop_blocked,
            "peak_queue_size": peak_queue,
        }

    def _record_transaction_timestamp(self, timestamp: float) -> None:
        now = max(float(timestamp), time.time())
        with self._metrics_lock:
            self._tx_timestamps.append(now)
            self._trim_tx_timestamps_locked(now)

    def _record_persist_success(self) -> None:
        now = time.monotonic()
        with self._metrics_lock:
            self._persist_success_timestamps.append(now)
            self._trim_persist_timestamps_locked(now)

    def _trim_tx_timestamps_locked(self, now: float) -> None:
        window_seconds = 10.0
        cutoff = now - window_seconds
        while self._tx_timestamps and self._tx_timestamps[0] < cutoff:
            self._tx_timestamps.popleft()
        current = len(self._tx_timestamps) / window_seconds
        self._peak_tx_per_second = max(self._peak_tx_per_second, current)

    def _trim_persist_timestamps_locked(self, now: float) -> None:
        window_seconds = 10.0
        cutoff = now - window_seconds
        while self._persist_success_timestamps and self._persist_success_timestamps[0] < cutoff:
            self._persist_success_timestamps.popleft()
        current = len(self._persist_success_timestamps) / window_seconds
        self._peak_persistence_writes_per_second = max(self._peak_persistence_writes_per_second, current)

    def _current_tx_per_second_locked(self) -> float:
        self._trim_tx_timestamps_locked(time.time())
        return round(len(self._tx_timestamps) / 10.0, 4)

    def _current_persistence_writes_per_second_locked(self) -> float:
        self._trim_persist_timestamps_locked(time.monotonic())
        return round(len(self._persist_success_timestamps) / 10.0, 4)

    @staticmethod
    def _count_duplicate_ids(records: list[dict[str, Any]]) -> int:
        seen: dict[str, str] = {}
        duplicates = 0
        for record in records:
            tx_id = str(record.get("id", ""))
            if not tx_id:
                continue
            normalized = json.dumps(TransactionStore._serialize_record(record), sort_keys=True)
            if tx_id in seen and seen[tx_id] != normalized:
                duplicates += 1
                continue
            seen.setdefault(tx_id, normalized)
        return duplicates

    @staticmethod
    def _average_job_latency_ms(event_log: list[dict[str, Any]]) -> float:
        accepted_at: dict[str, float] = {}
        latencies: list[float] = []
        for event in event_log:
            event_type = str(event.get("type", ""))
            data = event.get("data") if isinstance(event.get("data"), dict) else {}
            task_id = str(data.get("task_id", ""))
            timestamp = float(event.get("timestamp", 0.0) or 0.0)
            if not task_id or timestamp <= 0:
                continue
            if event_type == "job_accepted":
                accepted_at[task_id] = timestamp
            elif event_type == "job_completed" and task_id in accepted_at:
                latencies.append(max(0.0, (timestamp - accepted_at[task_id]) * 1000))
        return round(sum(latencies) / len(latencies), 3) if latencies else 0.0

    def _replay_integrity_ok(self, memory_transactions: list[dict[str, Any]]) -> bool:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for tx in memory_transactions:
            job_id = str(tx.get("job_id", "") or "")
            if not job_id:
                continue
            grouped.setdefault(job_id, []).append(tx)
        return all(validate_replay_flow(job_id, flow).get("valid", False) for job_id, flow in grouped.items())


transaction_store = TransactionStore()
