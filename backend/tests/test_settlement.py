import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.settlement_service import settlement_service
from store.transaction_store import transaction_store


class SettlementServiceTests(unittest.TestCase):
    def setUp(self):
        settlement_service.off_chain_balances.clear()
        transaction_store.clear()
        settlement_service.escrows.clear()

    def test_successful_simulated_transaction_updates_balances(self):
        settlement_service.deposit("sender", 50_000, None)
        tx = settlement_service.create_transaction(
            sender="sender",
            receiver="receiver",
            amount=2_500,
            metadata={"job_id": "job-1", "confidence": 0.8, "expected_value": 2_000},
        )

        self.assertEqual("success", tx["status"])
        self.assertTrue(
            str(tx["tx_hash"]).startswith(("sim_", "nano_", "settle_", "0x"))
        )
        self.assertEqual(47_500, settlement_service.get_balance("sender"))
        self.assertEqual(2_500, settlement_service.get_balance("receiver"))

    def test_failed_transaction_does_not_create_money(self):
        settlement_service.deposit("sender", 1_000, None)
        tx = settlement_service.create_transaction(
            sender="sender",
            receiver="receiver",
            amount=5_000,
            metadata={"job_id": "job-2"},
        )

        self.assertEqual("failed", tx["status"])
        self.assertEqual(1_000, settlement_service.get_balance("sender"))
        self.assertEqual(0, settlement_service.get_balance("receiver"))

    def test_partial_releases_require_sequential_chunk_order(self):
        settlement_service.deposit("sender", 10_000, None)
        escrow = settlement_service.create_escrow(
            job_id="job-stream",
            sender="sender",
            receiver="receiver",
            amount=6_000,
            metadata={"job_id": "job-stream"},
        )

        first = settlement_service.release_partial("job-stream", 2_000, chunk_index=1, total_chunks=3)
        out_of_order = settlement_service.release_partial("job-stream", 2_000, chunk_index=3, total_chunks=3)

        self.assertEqual("success", first["status"])
        self.assertEqual("failed", out_of_order["status"])
        self.assertIn("invalid_chunk_order", out_of_order["reason"])


if __name__ == "__main__":
    unittest.main()
