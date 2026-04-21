import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.compute_agent import ComputeAgent
from economy.economic_engine import economic_engine
from intelligence.decision_engine import DecisionEngine
from intelligence.predictor import Predictor
from intelligence.strategy_analyzer import StrategyAnalyzer
from intelligence.scout_agent_v2 import ScoutAgentV2


class PredictorTests(unittest.TestCase):
    def test_predictor_returns_explained_output(self):
        predictor = Predictor()
        result = predictor.predict(
            {
                "price_per_compute": 0.9,
                "queue_pressure": 0.7,
                "profitability_index": 1.3,
                "offer_momentum": 0.25,
                "offer_volatility": 0.1,
                "workload_ratio": 0.8,
                "success_rate": 0.75,
            }
        )

        self.assertEqual({"confidence", "score", "decision", "explanation"}, set(result.keys()) & {"confidence", "score", "decision", "explanation"})
        self.assertIsInstance(result["confidence"], float)
        self.assertIsInstance(result["score"], float)
        self.assertIsInstance(result["decision"], str)
        self.assertTrue(result["explanation"])
        self.assertIn("reliability_factor", result)

    def test_predictor_handles_missing_and_nan(self):
        predictor = Predictor()
        result = predictor.predict({"price_per_compute": None, "queue_pressure": float("nan")})

        self.assertIn(result["decision"], {"accept", "prioritize", "reject"})
        self.assertGreaterEqual(result["confidence"], 0.0)

    def test_strategy_and_scout_return_adjusted_confidence(self):
        strategy = StrategyAnalyzer().analyze(
            feature_vector={
                "price_per_compute": 0.8,
                "profitability_index": 1.2,
                "offer_momentum": 0.2,
                "queue_pressure": 0.7,
                "offer_volatility": 0.1,
                "workload_ratio": 0.8,
            },
            recent_offers=[1000, 1400, 1800],
            recent_workloads=[2, 3, 4],
        )
        scout = ScoutAgentV2().analyze("Optimize stable market forecasting pipeline")
        self.assertIn("reliability_factor", strategy)
        self.assertIn("confidence_adjusted", scout)


class DecisionEngineTests(unittest.TestCase):
    def test_decision_engine_rejects_weak_profile(self):
        engine = DecisionEngine()
        result = engine.decide(
            predictor_score=-0.4,
            profitability_score=-0.2,
            risk_score=-0.5,
            technical_signals={"volatility_high": True, "overloaded": True},
        )

        self.assertEqual("reject", result["decision"])
        self.assertLess(result["score"], 0.0)


class EconomicEngineTests(unittest.TestCase):
    def test_economic_engine_computes_job_value_and_metrics(self):
        evaluation = economic_engine.evaluate_job(
            {"price_offer": 2_000_000_000_000, "required_compute": 10},
            {"confidence": 0.75, "cost_per_compute": 100_000_000_000},
        )
        self.assertAlmostEqual(1_500_000_000_000.0, evaluation["expected_value"])
        self.assertTrue(evaluation["profitable"])

        metrics = economic_engine.compute_metrics(
            completed_jobs=[
                {
                    "price_offer": 2_000_000_000_000,
                    "economic": evaluation,
                    "compute_wallet": "agent-1",
                }
            ],
            events=[
                {"type": "job_accepted", "data": {}},
                {"type": "payment_sent", "data": {"amount": 2_000_000_000_000}},
            ],
        )
        self.assertEqual(1, metrics["total_transactions"])
        self.assertGreater(metrics["avg_profit"], 0.0)
        self.assertEqual(1.0, metrics["acceptance_rate"])
        self.assertIn("system_efficiency_score", metrics)


class ComputeAgentDecisionTests(unittest.TestCase):
    class DummyMarket:
        def __init__(self, pending_jobs=None):
            self.pending_jobs = pending_jobs or []

    class DummyMarketAgent:
        pass

    def test_compute_agent_accepts_strong_expected_value_job(self):
        agent = ComputeAgent(
            wallet="compute",
            market=self.DummyMarket(),
            market_agent=self.DummyMarketAgent(),
            personality_type="balanced",
            agent_id="ComputeAgent_test",
        )
        job = {
            "task_id": "job-good",
            "required_compute": 2,
            "price_offer": 4500,
            "intelligence": {
                "prediction": {"score": 0.4, "confidence": 0.8, "confidence_adjusted": 0.76},
                "strategy": {"confidence": 0.7, "momentum_positive": True, "demand_supportive": True},
                "scout": {"confidence": 0.6},
                "features": {"queue_pressure": 0.8, "workload_ratio": 0.9},
                "factors": {"ml": 0.4, "technical": 0.3, "economic": 0.4, "sentiment": 0.1},
                "confidence": 0.74,
                "score": 0.36,
            },
        }
        accepted, _, _, economic, reasons, _, _ = agent._should_accept_job(job)
        self.assertTrue(accepted)
        self.assertGreater(economic["expected_value"], 0.0)
        self.assertEqual([], reasons)

    def test_compute_agent_rejects_low_expected_value_job(self):
        agent = ComputeAgent(
            wallet="compute",
            market=self.DummyMarket(),
            market_agent=self.DummyMarketAgent(),
            personality_type="conservative",
            agent_id="ComputeAgent_test",
        )
        job = {
            "task_id": "job-bad",
            "required_compute": 8,
            "price_offer": 900,
            "intelligence": {
                "prediction": {"score": -0.2, "confidence": 0.2, "confidence_adjusted": 0.18},
                "strategy": {"confidence": 0.2, "momentum_positive": False, "demand_supportive": False},
                "scout": {"confidence": 0.1},
                "features": {"queue_pressure": 0.1, "workload_ratio": 1.4},
                "factors": {"ml": -0.2, "technical": -0.15, "economic": -0.2, "sentiment": -0.05},
                "confidence": 0.18,
                "score": -0.19,
            },
        }
        accepted, _, _, _, reasons, _, _ = agent._should_accept_job(job)
        self.assertFalse(accepted)
        self.assertIn("expected_value_below_threshold", reasons)


if __name__ == "__main__":
    unittest.main()
