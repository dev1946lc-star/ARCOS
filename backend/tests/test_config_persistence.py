import os
import tempfile
import time
import unittest
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import main as backend_main
except ModuleNotFoundError:
    backend_main = None
from core import config
from ledger.transaction_store import TransactionStore, transaction_store
from store.supabase_client import to_supabase_row


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self._original = {
            "DEBUG": os.environ.get("DEBUG"),
            "PORT": os.environ.get("PORT"),
            "ARC_RPC_URL": os.environ.get("ARC_RPC_URL"),
            "ARC_SETTLEMENT_RETRIES": os.environ.get("ARC_SETTLEMENT_RETRIES"),
            "SUPABASE_URL": os.environ.get("SUPABASE_URL"),
            "USE_SUPABASE": os.environ.get("USE_SUPABASE"),
            "SUPABASE_WRITE_ENABLED": os.environ.get("SUPABASE_WRITE_ENABLED"),
            "SUPABASE_SERVICE_KEY": os.environ.get("SUPABASE_SERVICE_KEY"),
        }
        os.environ.pop("DEBUG", None)
        os.environ.pop("PORT", None)
        os.environ.pop("ARC_RPC_URL", None)
        os.environ.pop("ARC_SETTLEMENT_RETRIES", None)
        os.environ.pop("SUPABASE_URL", None)
        os.environ.pop("USE_SUPABASE", None)
        os.environ.pop("SUPABASE_WRITE_ENABLED", None)
        os.environ.pop("SUPABASE_SERVICE_KEY", None)

    def tearDown(self):
        for key, value in self._original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        config.load_environment()

    def test_defaults_are_safe_when_env_missing(self):
        self.assertEqual("fallback", config.get_env("ARCOS_NOT_SET", "fallback"))
        self.assertTrue(config.get_bool("ARCOS_BOOL_NOT_SET", True))
        self.assertEqual(42, config.get_int("ARCOS_INT_NOT_SET", 42))

    def test_load_environment_reads_env_file(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write("DEBUG=false\nPORT=9100\n")
            path = handle.name
        try:
            loaded = config.load_environment(path)
            self.assertTrue(loaded)
            self.assertFalse(config.get_bool("DEBUG", True))
            self.assertEqual(9100, config.get_int("PORT", 8000))
        finally:
            Path(path).unlink(missing_ok=True)

    def test_validate_config_warns_and_clamps_invalid_values(self):
        os.environ["ARC_RPC_URL"] = "notaurl"
        os.environ["ARC_SETTLEMENT_RETRIES"] = "-10"
        os.environ["USE_SUPABASE"] = "true"
        os.environ["SUPABASE_WRITE_ENABLED"] = "true"
        validation = config.validate_config(force_refresh=True)

        self.assertFalse(validation["valid"])
        self.assertGreaterEqual(validation["warning_count"], 2)
        self.assertEqual(1, validation["config"]["PAYMENTS"]["settlement_retries"])
        self.assertTrue(any(item["key"] == "ARC_RPC_URL" for item in validation["warnings"]))


class FakeSupabase:
    def __init__(self, seeded: list[dict] | None = None):
        self.inserted: list[dict] = []
        self.seeded = seeded or []
        self.connected = True
        self.max_backlog = 100
        self._metrics = {
            "write_sampling_rate": 1.0,
            "drop_reasons": {"sampling": 0, "backpressure": 0, "oversize": 0, "retry_failure": 0},
            "avg_batch_size": 1.0,
            "avg_write_latency_ms": 1.0,
            "writes_attempted": 0,
        }

    def is_enabled(self) -> bool:
        return True

    def reload_config(self) -> None:
        return None

    def insert_transaction(self, record: dict, retries: int = 2) -> bool:
        self.inserted.append(dict(record))
        self._metrics["writes_attempted"] += 1
        return True

    def fetch_transactions(self, *, limit=None, job_id=None):
        records = list(self.seeded)
        if job_id:
            records = [record for record in records if record.get("job_id") == job_id]
        if limit is not None:
            records = records[:limit]
        return records

    def status(self) -> dict:
        return {
            "connected": self.connected,
            "status": "ok" if self.connected else "degraded",
            "message": "ok",
            "write_sampling_rate": 1.0,
            "dropped_writes": 0,
            "drop_reasons": dict(self._metrics["drop_reasons"]),
            "avg_batch_size": self._metrics["avg_batch_size"],
            "avg_write_latency_ms": self._metrics["avg_write_latency_ms"],
        }

    def ping(self) -> dict:
        return self.status()

    def queue_backlog(self) -> int:
        return 0

    def oldest_pending_age_ms(self) -> float:
        return 0.0

    def metrics_snapshot(self) -> dict:
        return self.status()


class TransactionStorePersistenceTests(unittest.TestCase):
    def test_store_keeps_memory_and_persists_to_supabase(self):
        store = TransactionStore(max_in_memory=10)
        store._supabase = FakeSupabase()
        store._use_supabase = True
        store._schedule_persist = lambda record: store._persist_record(record)

        tx = {
            "id": "tx-supabase-1",
            "job_id": "job-supabase",
            "sender": "research",
            "receiver": "compute",
            "amount": 2500,
            "tx_hash": "nano_test",
            "timestamp": 10.0,
            "status": "success",
            "chunk_index": 1,
            "total_chunks": 1,
        }
        store.add(tx)

        self.assertEqual(1, len(store.list_transactions()))
        self.assertEqual(1, len(store._supabase.inserted))
        self.assertEqual("tx-supabase-1", store._supabase.inserted[0]["id"])
        self.assertEqual(
            {"id", "job_id", "sender", "receiver", "amount", "status", "confidence", "expected_value", "timestamp"},
            set(store._supabase.inserted[0].keys()),
        )

    def test_store_can_fallback_to_persisted_records(self):
        persisted = [
            {
                "id": "tx-persisted-1",
                "job_id": "job-persisted",
                "sender": "research",
                "receiver": "compute",
                "amount": 1000,
                "tx_hash": "nano_persisted",
                "timestamp": 5.0,
                "status": "success",
                "chunk_index": 1,
                "total_chunks": 1,
                "cumulative_released": 1000,
                "remaining_escrow": 0,
                "metadata": {},
            }
        ]
        store = TransactionStore(max_in_memory=10)
        store._supabase = FakeSupabase(seeded=persisted)
        store._use_supabase = True

        records = store.list_transactions()
        self.assertEqual(1, len(records))
        self.assertEqual("tx-persisted-1", records[0]["id"])

    def test_duplicate_transaction_is_not_inserted_twice(self):
        store = TransactionStore(max_in_memory=10)
        store._supabase = FakeSupabase()
        store._use_supabase = True
        store._schedule_persist = lambda record: store._persist_record(record)
        tx = {
            "id": "tx-dup",
            "job_id": "job-dup",
            "sender": "research",
            "receiver": "compute",
            "amount": 500,
            "tx_hash": "nano_dup",
            "timestamp": 11.0,
            "status": "success",
        }
        store.add(tx)
        with self.assertRaises(ValueError):
            store.add(tx)
        self.assertEqual(1, len(store._supabase.inserted))

    def test_persistence_status_reports_mode_and_backlog(self):
        store = TransactionStore(max_in_memory=10)
        store._supabase = FakeSupabase()
        store._use_supabase = True
        status = store.persistence_status()

        self.assertEqual("hybrid", status["mode"])
        self.assertIn("queue_backlog", status)
        self.assertIn("persistence_lag_ms", status)
        self.assertIn("queue_utilization", status)
        self.assertIn("write_drop_count", status)
        self.assertIn("write_sampling_rate", status)
        self.assertIn("drop_reasons", status)
        self.assertIn("writes_attempted", status)
        self.assertIn("writes_successful", status)

    def test_persistence_metrics_reconcile_attempts_and_successes(self):
        store = TransactionStore(max_in_memory=10)
        store._supabase = FakeSupabase()
        store._use_supabase = True
        def persist_now(record):
            store._persistence_attempted += 1
            store._persist_record(record)
        store._schedule_persist = persist_now
        store.add(
            {
                "id": "tx-metrics-1",
                "job_id": "job-metrics",
                "sender": "research",
                "receiver": "compute",
                "amount": 700,
                "tx_hash": "nano_metrics",
                "timestamp": 20.0,
                "status": "success",
            }
        )
        metrics = store.persistence_metrics()
        self.assertEqual(1, metrics["writes_attempted"])
        self.assertEqual(1, metrics["writes_successful"])
        self.assertEqual(0, metrics["writes_dropped"])
        self.assertEqual(0, sum(metrics["drop_reasons"].values()))

    def test_performance_metrics_capture_recent_throughput(self):
        store = TransactionStore(max_in_memory=10)
        store._schedule_persist = lambda record: None
        base = time.time()
        for index in range(5):
            store.add(
                {
                    "id": f"tx-perf-{index}",
                    "job_id": f"job-perf-{index}",
                    "sender": "research",
                    "receiver": "compute",
                    "amount": 100 + index,
                    "tx_hash": f"nano-perf-{index}",
                    "timestamp": base + index * 0.01,
                    "status": "success",
                }
            )
        performance = store.performance_metrics(
            event_log=[
                {"type": "job_accepted", "timestamp": base, "data": {"task_id": "job-perf-1"}},
                {"type": "job_completed", "timestamp": base + 0.5, "data": {"task_id": "job-perf-1"}},
            ]
        )
        self.assertGreater(performance["tx_per_second"], 0.0)
        self.assertGreater(performance["peak_throughput_observed"], 0.0)
        self.assertGreater(performance["avg_job_processing_latency_ms"], 0.0)

    def test_validation_snapshot_flags_duplicates_and_replay_integrity(self):
        store = TransactionStore(max_in_memory=10)
        base = time.time()
        store.add(
            {
                "id": "tx-validate-1",
                "job_id": "job-validate",
                "sender": "research",
                "receiver": "compute",
                "amount": 500,
                "tx_hash": "nano-validate-1",
                "timestamp": base,
                "status": "success",
                "chunk_index": 1,
                "total_chunks": 2,
                "cumulative_released": 500,
                "remaining_escrow": 500,
            }
        )
        store.add(
            {
                "id": "tx-validate-2",
                "job_id": "job-validate",
                "sender": "research",
                "receiver": "compute",
                "amount": 500,
                "tx_hash": "nano-validate-2",
                "timestamp": base + 0.01,
                "status": "success",
                "chunk_index": 2,
                "total_chunks": 2,
                "cumulative_released": 1000,
                "remaining_escrow": 0,
            }
        )
        snapshot = store.validation_snapshot(balances={"research": 1000.0, "compute": 500.0})
        self.assertEqual(2, snapshot["memory_tx_count"])
        self.assertTrue(snapshot["consistency_ok"])
        self.assertEqual(0, snapshot["duplicate_ids"])
        self.assertTrue(snapshot["replay_valid"])

    def test_compact_supabase_row_strips_streaming_fields(self):
        row = to_supabase_row(
            {
                "id": "tx-compact",
                "job_id": "job-compact",
                "sender": "research",
                "receiver": "compute",
                "amount": 1234,
                "status": "success",
                "confidence": 0.88,
                "expected_value": 999.5,
                "timestamp": 123.45,
                "chunk_index": 3,
                "explanation": "rich explanation",
                "metadata": {"debug": True},
            }
        )
        self.assertEqual("tx-compact", row["id"])
        self.assertNotIn("chunk_index", row)
        self.assertNotIn("explanation", row)
        self.assertNotIn("metadata", row)


class ReplayEndpointTests(unittest.TestCase):
    def setUp(self):
        transaction_store.clear()

    def test_replay_endpoint_reconstructs_job_flow(self):
        transaction_store.add(
            {
                "id": "replay-1",
                "job_id": "job-replay",
                "sender": "research",
                "receiver": "compute",
                "amount": 2000,
                "tx_hash": "nano_1",
                "timestamp": time.time(),
                "status": "success",
                "chunk_index": 1,
                "total_chunks": 3,
                "cumulative_released": 2000,
                "remaining_escrow": 4000,
                "metadata": {},
            }
        )
        transaction_store.add(
            {
                "id": "replay-2",
                "job_id": "job-replay",
                "sender": "research",
                "receiver": "compute",
                "amount": 2000,
                "tx_hash": "nano_2",
                "timestamp": time.time() + 0.01,
                "status": "success",
                "chunk_index": 2,
                "total_chunks": 3,
                "cumulative_released": 4000,
                "remaining_escrow": 2000,
                "metadata": {},
            }
        )
        transaction_store.add(
            {
                "id": "replay-3",
                "job_id": "job-replay",
                "sender": "research",
                "receiver": "compute",
                "amount": 2000,
                "tx_hash": "nano_3",
                "timestamp": time.time() + 0.02,
                "status": "success",
                "chunk_index": 3,
                "total_chunks": 3,
                "cumulative_released": 6000,
                "remaining_escrow": 0,
                "metadata": {},
            }
        )

        replay = transaction_store.replay_job("job-replay")
        self.assertEqual("success", replay["status"])
        self.assertEqual(3, replay["partial_payment_count"])
        self.assertEqual(6000.0, replay["released_total"])
        self.assertEqual(0.0, replay["remaining_escrow"])

    def test_env_and_persistence_status_are_available(self):
        env = config.env_status()
        persistence = transaction_store.persistence_status()
        self.assertIn("loaded", env)
        self.assertIn("valid", env)
        self.assertIn("storage_mode", persistence)
        self.assertIn("supabase_status", persistence)
        self.assertIn("queue_utilization", persistence)

    def test_observability_endpoints_append_safe_fields(self):
        if backend_main is None:
            self.skipTest("fastapi is not installed in this workspace")
        health = backend_main.get_system_health()
        persistence = backend_main.get_system_persistence()
        performance = backend_main.get_system_performance()
        economics = backend_main.get_economics_summary()

        self.assertTrue(health["frontend_safe"])
        self.assertEqual("memory_primary", health["data_source"])
        self.assertIn("frontend_validation", health)
        self.assertTrue(health["frontend_validation"]["typecheck_passed"])
        self.assertTrue(health["frontend_validation"]["build_passed"])
        self.assertTrue(health["frontend_validation"]["runtime_safe"])
        self.assertIn("drop_reasons", persistence)
        self.assertIn("avg_write_latency_ms", persistence)
        self.assertIn("drop_rate", persistence)
        self.assertIn("success_rate", persistence)
        self.assertIn("system_load", persistence)
        self.assertIn("status", persistence)
        self.assertIn("backpressure_active", persistence)
        self.assertIn("queue_health", persistence)
        self.assertIn("peak_throughput_observed", performance)
        self.assertIn("scalability", economics)
        self.assertIn("scalability_score", economics)
        self.assertIn("guarantees", economics)

    def test_validation_endpoint_reports_data_integrity_proof(self):
        if backend_main is None:
            self.skipTest("fastapi is not installed in this workspace")
        validation = backend_main.get_system_validation()

        self.assertIn("data_integrity", validation)
        self.assertIn("critical_data_loss", validation["data_integrity"])
        self.assertIn("non_critical_data_loss", validation["data_integrity"])
        self.assertEqual(0, validation["data_integrity"]["critical_data_loss"])

    def test_overload_endpoint_reports_judge_verdict(self):
        if backend_main is None:
            self.skipTest("fastapi is not installed in this workspace")
        result = asyncio.run(
            backend_main.post_system_test_overload(
                backend_main.OverloadTestRequest(burst_size=20, queue_limit=8, processing_delay_ms=1)
            )
        )

        self.assertIn("validation", result)
        self.assertIn("test_result", result)
        self.assertIn("reason", result)
        self.assertEqual("PASS", result["test_result"])
        self.assertEqual("no blocking, no crash, consistent state", result["reason"])


if __name__ == "__main__":
    unittest.main()
