import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analysis.gas_model import gas_model
from economy.pricing_engine import pricing_engine
from payments.settlement_service import settlement_service
from payments.wallet_service import wallet_service
from ledger.transaction_store import transaction_store


class PricingEngineTests(unittest.TestCase):
    def test_pricing_engine_caps_subcent_price(self):
        result = pricing_engine.compute_price(
            compute_units=8,
            predicted_profit=100.0,
            demand=10,
            agent_availability=2,
            confidence_score=0.9,
            predictor_score=0.5,
            strategy_score=0.4,
            scout_score=0.2,
            expected_value=1500.0,
            idle_capacity=0,
            acceptance_rate=0.6,
            recent_profit_trend=0.2,
        )
        self.assertLessEqual(result["price_offer"], 10_000)
        self.assertGreaterEqual(result["price_offer"], 500)
        self.assertIn("pricing_reasoning", result)
        self.assertIn("market_pressure", result)


class EscrowSettlementTests(unittest.TestCase):
    def setUp(self):
        transaction_store.clear()
        wallet_service.balance_registry.clear()
        settlement_service.escrows.clear()
        settlement_service.seed_balance("research", 50_000)

    def test_escrow_lock_release_and_refund(self):
        escrow = settlement_service.create_escrow(
            job_id="job-123",
            sender="research",
            receiver="compute",
            amount=4_000,
            metadata={"job_id": "job-123", "confidence": 0.8, "expected_value": 3500},
        )
        self.assertEqual("locked", escrow["status"])
        self.assertEqual(46_000, settlement_service.get_balance("research"))

        release = settlement_service.release_escrow(escrow["escrow_id"])
        self.assertEqual("success", release["status"])
        self.assertEqual(4_000, settlement_service.get_balance("compute"))

        escrow2 = settlement_service.create_escrow(
            job_id="job-124",
            sender="research",
            receiver="compute",
            amount=2_000,
            metadata={"job_id": "job-124"},
        )
        refund = settlement_service.refund_escrow(escrow2["escrow_id"])
        self.assertEqual("refunded", refund["status"])
        self.assertEqual(46_000, settlement_service.get_balance("research"))

    def test_partial_release_tracks_chunks(self):
        escrow = settlement_service.create_escrow(
            job_id="job-stream",
            sender="research",
            receiver="compute",
            amount=5_000,
            metadata={"job_id": "job-stream", "confidence": 0.7, "expected_value": 4200},
        )
        tx1 = settlement_service.release_partial("job-stream", 2_000, chunk_index=1, total_chunks=3)
        tx2 = settlement_service.release_partial("job-stream", 2_000, chunk_index=2, total_chunks=3)
        tx3 = settlement_service.release_partial("job-stream", 1_000, chunk_index=3, total_chunks=3)
        self.assertEqual("success", tx1["status"])
        self.assertEqual("success", tx2["status"])
        self.assertEqual("success", tx3["status"])
        self.assertEqual(5_000, settlement_service.get_balance("compute"))
        self.assertEqual(45_000, settlement_service.get_balance("research"))

    def test_duplicate_partial_release_is_idempotent(self):
        settlement_service.create_escrow(
            job_id="job-dup",
            sender="research",
            receiver="compute",
            amount=3_000,
            metadata={"job_id": "job-dup"},
        )
        tx1 = settlement_service.release_partial("job-dup", 1_500, chunk_index=1, total_chunks=2)
        tx2 = settlement_service.release_partial("job-dup", 1_500, chunk_index=1, total_chunks=2)
        self.assertEqual(tx1["id"], tx2["id"])
        self.assertEqual(1_500, settlement_service.get_balance("compute"))
        escrow_id, escrow = settlement_service._find_escrow_by_job("job-dup")
        self.assertIsNotNone(escrow_id)
        self.assertEqual(1_500, escrow["released_amount"])

    def test_partial_release_overflow_is_blocked(self):
        settlement_service.create_escrow(
            job_id="job-overflow",
            sender="research",
            receiver="compute",
            amount=1_000,
            metadata={"job_id": "job-overflow"},
        )
        settlement_service.release_partial("job-overflow", 1_000, chunk_index=1, total_chunks=1)
        overflow = settlement_service.release_partial("job-overflow", 500, chunk_index=2, total_chunks=2)
        self.assertEqual("failed", overflow["status"])
        self.assertIn("invalid_escrow_state", overflow["reason"])

    def test_ledger_replay_and_append_only(self):
        tx = {
            "id": "tx-1",
            "job_id": "job-ledger",
            "sender": "research",
            "receiver": "compute",
            "amount": 1200,
            "tx_hash": "nano_demo",
            "timestamp": 1.0,
            "status": "success",
        }
        transaction_store.add(tx)
        balances = transaction_store.replay_balances()
        self.assertEqual(-1200.0, balances["research"])
        self.assertEqual(1200.0, balances["compute"])
        with self.assertRaises(ValueError):
            transaction_store.add(tx)


class GasModelTests(unittest.TestCase):
    def test_gas_model_shows_eth_costlier_than_arc(self):
        result = gas_model.compare(transactions=50, avg_amount_micro_usdc=5_000)
        self.assertGreater(result["eth_cost"], result["arc_cost"])
        self.assertGreater(result["margin_loss"], 0.0)


if __name__ == "__main__":
    unittest.main()
