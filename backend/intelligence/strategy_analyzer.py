from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from typing import Any


class StrategyAnalyzer:
    """Combines AnalystAgent and StrategyAnalyzer ideas for job ranking."""

    def __init__(self, memory_size: int = 24) -> None:
        self._decision_memory: deque[dict[str, float]] = deque(maxlen=max(8, int(memory_size)))

    def analyze(
        self,
        *,
        feature_vector: dict[str, float],
        recent_offers: Sequence[float] | None = None,
        recent_workloads: Sequence[float] | None = None,
    ) -> dict[str, Any]:
        recent_offers = [float(value) for value in (recent_offers or [])]
        recent_workloads = [float(value) for value in (recent_workloads or [])]

        offer_momentum = self._momentum(recent_offers)
        compute_momentum = self._momentum(recent_workloads)
        trend_reliability = self._trend_reliability(recent_offers, recent_workloads)
        memory = self.memory_snapshot()

        technical_score = 0.0
        technical_score += (feature_vector.get("price_per_compute", 0.0) - 0.55) * 0.42
        technical_score += (feature_vector.get("profitability_index", 0.8) - 0.8) * 0.30
        technical_score += offer_momentum * 0.18
        technical_score += (feature_vector.get("queue_pressure", 0.35) - 0.35) * 0.15
        technical_score -= feature_vector.get("offer_volatility", 0.0) * 0.18
        technical_score -= max(0.0, feature_vector.get("workload_ratio", 1.0) - 1.0) * 0.22
        technical_score += (memory["success_rate"] - 0.5) * 0.15
        technical_score = max(-1.0, min(1.0, technical_score))

        reliability_factor = max(
            0.45,
            min(
                1.0,
                trend_reliability * (0.85 + (memory["success_rate"] - 0.5) * 0.4),
            ),
        )
        confidence = max(0.12, min(0.98, abs(technical_score) * 0.7 + trend_reliability * 0.3))
        confidence_adjusted = max(0.0, min(1.0, confidence * reliability_factor))

        demand_supportive = feature_vector.get("queue_pressure", 0.0) > 0.5
        overloaded = feature_vector.get("workload_ratio", 1.0) > 1.25
        volatility_high = feature_vector.get("offer_volatility", 0.0) > 0.25

        threshold = max(0.1, min(0.3, 0.16 + (0.55 - memory["success_rate"]) * 0.18))
        if technical_score > threshold + 0.08:
            decision = "prioritize"
        elif technical_score < -(threshold + 0.02):
            decision = "reject"
        else:
            decision = "accept"

        return {
            "confidence": round(confidence_adjusted, 4),
            "confidence_adjusted": round(confidence_adjusted, 4),
            "base_confidence": round(confidence, 4),
            "reliability_factor": round(reliability_factor, 4),
            "score": round(technical_score, 4),
            "decision": decision,
            "technical_score": round(technical_score, 4),
            "momentum_positive": offer_momentum > 0,
            "demand_supportive": demand_supportive,
            "volatility_high": volatility_high,
            "overloaded": overloaded,
            "offer_momentum": round(offer_momentum, 4),
            "compute_momentum": round(compute_momentum, 4),
            "memory": memory,
        }

    def record_outcome(self, *, accepted: bool, success: bool, score: float) -> None:
        self._decision_memory.append(
            {
                "accepted": 1.0 if accepted else 0.0,
                "success": 1.0 if success else 0.0,
                "score": float(score),
            }
        )

    def memory_snapshot(self) -> dict[str, float]:
        if not self._decision_memory:
            return {"success_rate": 0.5, "acceptance_rate": 0.5, "average_score": 0.0}
        count = float(len(self._decision_memory))
        return {
            "success_rate": round(sum(item["success"] for item in self._decision_memory) / count, 4),
            "acceptance_rate": round(sum(item["accepted"] for item in self._decision_memory) / count, 4),
            "average_score": round(sum(item["score"] for item in self._decision_memory) / count, 4),
        }

    @staticmethod
    def _momentum(values: Sequence[float]) -> float:
        if len(values) < 2:
            return 0.0
        first = float(values[0])
        last = float(values[-1])
        return max(-1.0, min(1.0, (last - first) / max(abs(first), 1.0)))

    @staticmethod
    def _trend_reliability(recent_offers: Sequence[float], recent_workloads: Sequence[float]) -> float:
        activity = min(1.0, (len(recent_offers) + len(recent_workloads)) / 12.0)
        return max(0.5, min(1.0, 0.55 + activity * 0.45))
