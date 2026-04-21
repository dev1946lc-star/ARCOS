from __future__ import annotations

import json
import logging
import queue
import random
import threading
import time
import urllib.parse
import urllib.request
from collections import deque
from typing import Any

from core.config import validate_config

logger = logging.getLogger("ARCOS.Supabase")

_SUPABASE_ROW_FIELDS = (
    "id",
    "job_id",
    "sender",
    "receiver",
    "amount",
    "status",
    "confidence",
    "expected_value",
    "timestamp",
)


def to_supabase_row(tx: dict[str, Any]) -> dict[str, Any]:
    """Serialize a transaction into the compact, flat row stored in Supabase."""
    row = {
        "id": str(tx.get("id") or ""),
        "job_id": str(tx.get("job_id") or "") or None,
        "sender": str(tx.get("sender") or ""),
        "receiver": str(tx.get("receiver") or ""),
        "amount": int(tx.get("amount", 0) or 0),
        "status": str(tx.get("status") or "pending"),
        "confidence": float(tx.get("confidence", 0.0) or 0.0),
        "expected_value": float(tx.get("expected_value", 0.0) or 0.0),
        "timestamp": float(tx.get("timestamp", time.time()) or time.time()),
    }
    return {field: row.get(field) for field in _SUPABASE_ROW_FIELDS}


class SupabaseClient:
    """Optional secondary persistence client with bounded async buffering."""

    def __init__(self) -> None:
        self._status_lock = threading.Lock()
        self._metrics_lock = threading.Lock()
        self._queue: queue.Queue[dict[str, Any]] | None = None
        self._worker: threading.Thread | None = None
        self._stopped = threading.Event()
        self._write_failures = 0
        self._write_successes = 0
        self._dropped_writes = 0
        self._dropped_batches = 0
        self._sampled_out_writes = 0
        self._rate_limited_writes = 0
        self._oversized_rows = 0
        self._last_success_at: float | None = None
        self._last_error_at: float | None = None
        self._oldest_pending_at: float | None = None
        self._window_started_at = time.monotonic()
        self._writes_in_window = 0
        self._writes_attempted = 0
        self._successful_flush_count = 0
        self._successful_write_timestamps: deque[float] = deque()
        self._peak_writes_per_second = 0.0
        self._drop_reasons = {
            "sampling": 0,
            "backpressure": 0,
            "oversize": 0,
            "retry_failure": 0,
        }
        self._total_batch_size = 0
        self._total_flush_latency_ms = 0.0
        self.reload_config()

    def reload_config(self) -> None:
        settings = validate_config(force_refresh=True)["config"]["DATABASE"]
        self.url = str(settings["supabase_url"]).rstrip("/")
        self.service_key = str(settings["supabase_service_key"])
        self.table_transactions = str(settings["supabase_table_transactions"])
        self.batch_size = int(settings["supabase_batch_size"])
        self.flush_interval_ms = int(settings["supabase_flush_interval_ms"])
        self.max_queue_size = int(settings["supabase_max_queue_size"])
        self.max_retries = int(settings["supabase_max_retries"])
        self.retry_base_ms = int(settings["supabase_retry_base_ms"])
        self.request_timeout_sec = float(settings["supabase_request_timeout_sec"])
        self.write_enabled = bool(settings["supabase_write_enabled"])
        self.compact_mode = bool(settings["supabase_compact_mode"])
        self.drop_explanation = bool(settings["supabase_drop_explanation"])
        self.write_sampling_rate = float(settings["supabase_write_sampling_rate"])
        self.max_writes_per_sec = int(settings["supabase_max_writes_per_sec"])
        self.max_row_size_bytes = int(settings["supabase_max_row_size_bytes"])
        self.max_batch_bytes = int(settings["supabase_max_batch_bytes"])
        self.max_backlog = int(settings["max_persistence_backlog"])
        self.enable_backpressure = bool(settings["enable_backpressure"])
        self.enabled = bool(self.write_enabled and self.url and self.service_key)
        self._queue = queue.Queue(maxsize=max(self.max_queue_size, self.max_backlog))
        self._window_started_at = time.monotonic()
        self._writes_in_window = 0
        status_message = "ready" if self.enabled else "disabled"
        with self._status_lock:
            self._last_status = {
                "connected": False,
                "status": "offline" if self.enabled else "disabled",
                "checked_at": None,
                "message": status_message,
            }
        if self.enabled and (self._worker is None or not self._worker.is_alive()):
            self._stopped.clear()
            self._worker = threading.Thread(target=self._worker_loop, name="supabase-writer", daemon=True)
            self._worker.start()

    def is_enabled(self) -> bool:
        return self.enabled

    def _headers(self, *, prefer: str | None = None) -> dict[str, str]:
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _request(self, *, method: str, path: str, payload: Any | None = None) -> Any:
        if not self.enabled:
            raise RuntimeError("supabase_disabled")
        data = None if payload is None else json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        request = urllib.request.Request(
            f"{self.url}{path}",
            data=data,
            headers=self._headers(
                prefer="resolution=ignore-duplicates,return=minimal" if method.upper() == "POST" else None
            ),
            method=method.upper(),
        )
        with urllib.request.urlopen(request, timeout=self.request_timeout_sec) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None

    def ping(self) -> dict[str, Any]:
        if not self.enabled:
            status = {"connected": False, "status": "offline", "checked_at": time.time(), "message": "disabled"}
            with self._status_lock:
                self._last_status = status
            return self.status()
        try:
            path = f"/rest/v1/{self.table_transactions}?select=id&limit=1"
            self._request(method="GET", path=path)
            with self._status_lock:
                self._last_status = {"connected": True, "status": "ok", "checked_at": time.time(), "message": "ok"}
        except Exception as exc:
            with self._status_lock:
                self._last_status = {
                    "connected": False,
                    "status": "offline" if self.queue_backlog() == 0 else "degraded",
                    "checked_at": time.time(),
                    "message": str(exc),
                }
        return self.status()

    def status(self) -> dict[str, Any]:
        with self._status_lock:
            base = dict(self._last_status)
        with self._metrics_lock:
            drop_reasons = dict(self._drop_reasons)
            writes_attempted = self._writes_attempted
            successful_flush_count = self._successful_flush_count
            avg_batch_size = round(self._total_batch_size / successful_flush_count, 3) if successful_flush_count else 0.0
            avg_write_latency_ms = round(self._total_flush_latency_ms / self._write_successes, 3) if self._write_successes else 0.0
            writes_per_second = self._current_writes_per_second_locked()
            peak_writes_per_second = round(self._peak_writes_per_second, 4)
        base.update(
            {
                "enabled": self.enabled,
                "write_sampling_rate": self.write_sampling_rate,
                "queue_backlog": self.queue_backlog(),
                "queue_utilization": self.queue_utilization(),
                "oldest_pending_age_ms": self.oldest_pending_age_ms(),
                "write_successes": self._write_successes,
                "write_failures": self._write_failures,
                "dropped_writes": self._dropped_writes,
                "dropped_batches": self._dropped_batches,
                "sampled_out_writes": self._sampled_out_writes,
                "rate_limited_writes": self._rate_limited_writes,
                "oversized_rows": self._oversized_rows,
                "last_success_at": self._last_success_at,
                "last_error_at": self._last_error_at,
                "max_backlog": self.max_backlog,
                "writes_attempted": writes_attempted,
                "drop_reasons": drop_reasons,
                "avg_batch_size": avg_batch_size,
                "avg_write_latency_ms": avg_write_latency_ms,
                "writes_per_second": writes_per_second,
                "peak_writes_per_second": peak_writes_per_second,
            }
        )
        return base

    def queue_backlog(self) -> int:
        return self._queue.qsize() if self._queue is not None else 0

    def queue_utilization(self) -> float:
        if not self._queue:
            return 0.0
        capacity = max(self.max_backlog, 1)
        return round(min(1.0, self.queue_backlog() / capacity), 4)

    def oldest_pending_age_ms(self) -> float:
        if self._oldest_pending_at is None:
            return 0.0
        return round(max(0.0, (time.time() - self._oldest_pending_at) * 1000), 3)

    def insert_transaction(self, record: dict[str, Any], retries: int = 2) -> bool:
        return self.enqueue_transaction(record)

    def enqueue_transaction(self, record: dict[str, Any]) -> bool:
        if not self.enabled or self._queue is None:
            return False
        with self._metrics_lock:
            self._writes_attempted += 1
        if self.write_sampling_rate <= 0 or random.random() > self.write_sampling_rate:
            with self._metrics_lock:
                self._sampled_out_writes += 1
                self._dropped_writes += 1
                self._drop_reasons["sampling"] += 1
            return False

        payload = to_supabase_row(record) if self.compact_mode else dict(record)
        row_size = self._row_size_bytes(payload)
        if row_size > self.max_row_size_bytes:
            with self._metrics_lock:
                self._oversized_rows += 1
                self._dropped_writes += 1
                self._drop_reasons["oversize"] += 1
            logger.warning(
                "supabase_enqueue_dropped %s",
                {"reason": "row_too_large", "transaction_id": payload.get("id"), "row_size": row_size},
            )
            return False

        payload["_queued_at"] = time.time()
        payload["_row_size_bytes"] = row_size

        if self.enable_backpressure and self.queue_backlog() >= self.max_backlog:
            if not self._drop_oldest_queued("backlog_limit"):
                with self._metrics_lock:
                    self._dropped_writes += 1
                    self._drop_reasons["backpressure"] += 1
                return False

        try:
            self._queue.put_nowait(payload)
            if self._oldest_pending_at is None:
                self._oldest_pending_at = payload["_queued_at"]
            return True
        except queue.Full:
            if self._drop_oldest_queued("queue_full"):
                try:
                    self._queue.put_nowait(payload)
                    self._refresh_oldest_pending()
                    return True
                except queue.Full:
                    pass
            with self._metrics_lock:
                self._dropped_writes += 1
                self._drop_reasons["backpressure"] += 1
            with self._status_lock:
                self._last_status = {
                    "connected": False,
                    "status": "degraded",
                    "checked_at": time.time(),
                    "message": "supabase_queue_full",
                }
            logger.warning(
                "supabase_enqueue_failed %s",
                {"reason": "queue_full", "queue_backlog": self.queue_backlog(), "transaction_id": payload.get("id")},
            )
            return False

    def _drop_oldest_queued(self, reason: str) -> bool:
        if self._queue is None:
            return False
        dropped: dict[str, Any] | None = None
        with self._queue.mutex:
            if self._queue.queue:
                dropped = self._queue.queue.popleft()
                self._queue.unfinished_tasks = max(0, self._queue.unfinished_tasks - 1)
                self._queue.not_full.notify()
        if dropped is None:
            return False
        with self._metrics_lock:
            self._dropped_writes += 1
            self._drop_reasons["backpressure"] += 1
        logger.warning(
            "supabase_write_dropped %s",
            {"reason": reason, "transaction_id": dropped.get("id"), "queue_backlog": self.queue_backlog()},
        )
        self._refresh_oldest_pending()
        return True

    def _worker_loop(self) -> None:
        while not self._stopped.is_set():
            batch = self._dequeue_batch()
            if not batch:
                continue
            self._flush_batch(batch)

    def _dequeue_batch(self) -> list[dict[str, Any]]:
        if self._queue is None:
            return []
        try:
            first = self._queue.get(timeout=max(self.flush_interval_ms / 1000.0, 0.05))
        except queue.Empty:
            return []

        batch = [first]
        batch_bytes = int(first.get("_row_size_bytes", 0))
        deadline = time.time() + (self.flush_interval_ms / 1000.0)
        while len(batch) < self.batch_size and time.time() < deadline:
            timeout = max(0.01, deadline - time.time())
            try:
                candidate = self._queue.get(timeout=timeout)
            except queue.Empty:
                break
            candidate_bytes = int(candidate.get("_row_size_bytes", self._row_size_bytes(candidate)))
            if batch and batch_bytes + candidate_bytes > self.max_batch_bytes:
                self._queue_requeue_front(candidate, from_get=True)
                break
            batch.append(candidate)
            batch_bytes += candidate_bytes
        return batch

    def _queue_requeue_front(self, item: dict[str, Any], *, from_get: bool = False) -> None:
        if self._queue is None:
            return
        with self._queue.mutex:
            self._queue.queue.appendleft(item)
            if not from_get:
                self._queue.unfinished_tasks += 1
            self._queue.not_empty.notify()
        self._refresh_oldest_pending()

    def _flush_batch(self, batch: list[dict[str, Any]]) -> None:
        records = [{key: value for key, value in item.items() if not key.startswith("_")} for item in batch]
        payload_bytes = self._payload_size_bytes(records)
        if payload_bytes > self.max_batch_bytes:
            with self._metrics_lock:
                self._dropped_batches += 1
                self._dropped_writes += len(records)
                self._drop_reasons["oversize"] += len(records)
            for _ in batch:
                if self._queue is not None:
                    self._queue.task_done()
            self._refresh_oldest_pending()
            logger.warning(
                "supabase_batch_dropped %s",
                {"reason": "batch_too_large", "count": len(records), "payload_bytes": payload_bytes},
            )
            return

        allowed_now = self._allow_writes_now(len(records))
        if allowed_now <= 0:
            with self._metrics_lock:
                self._rate_limited_writes += len(records)
            for item in reversed(batch):
                self._queue_requeue_front(item)
                if self._queue is not None:
                    self._queue.task_done()
            time.sleep(min(self.flush_interval_ms / 1000.0, 0.1))
            return
        if allowed_now < len(batch):
            overflow = batch[allowed_now:]
            batch = batch[:allowed_now]
            for item in reversed(overflow):
                self._queue_requeue_front(item)
                if self._queue is not None:
                    self._queue.task_done()
            records = [{key: value for key, value in item.items() if not key.startswith("_")} for item in batch]

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                flush_started_at = time.perf_counter()
                self._post_records(records)
                flush_latency_ms = (time.perf_counter() - flush_started_at) * 1000
                with self._metrics_lock:
                    self._write_successes += len(records)
                    self._successful_flush_count += 1
                    self._total_batch_size += len(records)
                    self._total_flush_latency_ms += flush_latency_ms * len(records)
                    now = time.monotonic()
                    for _ in records:
                        self._successful_write_timestamps.append(now)
                    self._trim_success_timestamps_locked(now)
                self._last_success_at = time.time()
                self._refresh_oldest_pending()
                with self._status_lock:
                    self._last_status = {
                        "connected": True,
                        "status": "ok",
                        "checked_at": self._last_success_at,
                        "message": "ok",
                    }
                for _ in batch:
                    if self._queue is not None:
                        self._queue.task_done()
                return
            except Exception as exc:
                last_error = exc
                with self._metrics_lock:
                    self._write_failures += len(records)
                self._last_error_at = time.time()
                delay = min((self.retry_base_ms / 1000.0) * (2 ** (attempt - 1)), 5.0)
                time.sleep(delay)

        with self._status_lock:
            self._last_status = {
                "connected": False,
                "status": "degraded",
                "checked_at": time.time(),
                "message": str(last_error or "supabase_write_failed"),
            }
        logger.warning(
            "supabase_flush_failed %s",
            {"count": len(records), "message": str(last_error or "supabase_write_failed")},
        )
        with self._metrics_lock:
            self._dropped_writes += len(records)
            self._drop_reasons["retry_failure"] += len(records)
        for item in batch:
            if self._queue is not None:
                self._queue.task_done()
        self._refresh_oldest_pending()

    def _allow_writes_now(self, requested: int) -> int:
        now = time.monotonic()
        if now - self._window_started_at >= 1.0:
            self._window_started_at = now
            self._writes_in_window = 0
        available = max(0, self.max_writes_per_sec - self._writes_in_window)
        granted = min(requested, available)
        self._writes_in_window += granted
        return granted

    def _refresh_oldest_pending(self) -> None:
        if self._queue is None or self._queue.empty():
            self._oldest_pending_at = None
            return
        with self._queue.mutex:
            queued = list(self._queue.queue)
        timestamps = [float(item.get("_queued_at", time.time())) for item in queued if isinstance(item, dict)]
        self._oldest_pending_at = min(timestamps) if timestamps else None

    def _post_records(self, records: list[dict[str, Any]]) -> None:
        if not records:
            return
        path = f"/rest/v1/{self.table_transactions}?on_conflict=id"
        self._request(method="POST", path=path, payload=records)

    def fetch_transactions(self, *, limit: int | None = None, job_id: str | None = None) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        params = {"select": "*", "order": "timestamp.asc,id.asc"}
        if limit is not None:
            params["limit"] = str(max(1, int(limit)))
        if job_id:
            params["job_id"] = f"eq.{job_id}"
        path = f"/rest/v1/{self.table_transactions}?{urllib.parse.urlencode(params)}"
        try:
            result = self._request(method="GET", path=path)
            if isinstance(result, list):
                with self._status_lock:
                    self._last_status = {"connected": True, "status": "ok", "checked_at": time.time(), "message": "ok"}
                return [dict(item) for item in result]
        except Exception as exc:
            with self._status_lock:
                self._last_status = {
                    "connected": False,
                    "status": "degraded",
                    "checked_at": time.time(),
                    "message": str(exc),
                }
        return []

    @staticmethod
    def _row_size_bytes(record: dict[str, Any]) -> int:
        return len(json.dumps({key: value for key, value in record.items() if not key.startswith("_")}, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))

    @staticmethod
    def _payload_size_bytes(records: list[dict[str, Any]]) -> int:
        return len(json.dumps(records, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))

    def metrics_snapshot(self) -> dict[str, Any]:
        return self.status()

    def _trim_success_timestamps_locked(self, now: float) -> None:
        window_seconds = 10.0
        cutoff = now - window_seconds
        while self._successful_write_timestamps and self._successful_write_timestamps[0] < cutoff:
            self._successful_write_timestamps.popleft()
        current = len(self._successful_write_timestamps) / window_seconds
        self._peak_writes_per_second = max(self._peak_writes_per_second, current)

    def _current_writes_per_second_locked(self) -> float:
        now = time.monotonic()
        self._trim_success_timestamps_locked(now)
        return round(len(self._successful_write_timestamps) / 10.0, 4)


supabase_client = SupabaseClient()
