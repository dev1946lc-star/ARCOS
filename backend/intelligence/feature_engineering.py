from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import sqrt


@dataclass(slots=True)
class FeatureVector:
    values: dict[str, float]


class FeatureEngineering:
    """Adapted from AURORA's feature engineering for generic ARCOS jobs."""

    feature_order = [
        "required_compute",
        "price_per_compute",
        "queue_pressure",
        "completion_pressure",
        "offer_momentum",
        "offer_volatility",
        "compute_trend",
        "workload_ratio",
        "task_complexity",
        "market_heat",
        "success_rate",
        "scarcity",
        "urgency",
        "profitability_index",
    ]

    def generate(
        self,
        *,
        required_compute: float,
        price_offer: float,
        queue_depth: int,
        completed_jobs: int,
        active_compute_agents: int,
        recent_offers: Sequence[float] | None = None,
        recent_workloads: Sequence[float] | None = None,
        success_rate: float = 0.5,
    ) -> FeatureVector:
        recent_offers = [float(value) for value in (recent_offers or [])]
        recent_workloads = [float(value) for value in (recent_workloads or [])]

        price_per_compute = float(price_offer) / max(float(required_compute), 1.0)
        offer_avg = self._mean(recent_offers) or price_offer
        workload_avg = self._mean(recent_workloads) or required_compute
        offer_std = self._stddev(recent_offers)

        features = {
            "required_compute": self._clamp(required_compute / 40.0),
            "price_per_compute": self._clamp(price_per_compute / 150_000_000_000.0),
            "queue_pressure": self._clamp(queue_depth / max(active_compute_agents, 1)),
            "completion_pressure": self._clamp(completed_jobs / max(queue_depth + completed_jobs, 1)),
            "offer_momentum": self._clamp(self._trend(recent_offers, fallback=0.0), -1.0, 1.0),
            "offer_volatility": self._clamp(offer_std / max(offer_avg, 1.0), 0.0, 1.0),
            "compute_trend": self._clamp(self._trend(recent_workloads, fallback=0.0), -1.0, 1.0),
            "workload_ratio": self._clamp(required_compute / max(workload_avg, 1.0), 0.0, 3.0),
            "task_complexity": self._clamp(required_compute / 50.0),
            "market_heat": self._clamp((queue_depth + completed_jobs * 0.25) / max(active_compute_agents, 1), 0.0, 3.0),
            "success_rate": self._clamp(success_rate, 0.0, 1.0),
            "scarcity": self._clamp(1.0 / max(active_compute_agents, 1), 0.0, 1.0),
            "urgency": self._clamp((queue_depth * required_compute) / 200.0, 0.0, 2.0),
            "profitability_index": self._clamp(price_per_compute / max(offer_avg / max(workload_avg, 1.0), 1.0), 0.0, 3.0),
        }
        return FeatureVector(values={name: float(features.get(name, 0.0)) for name in self.feature_order})

    @staticmethod
    def _mean(values: Sequence[float]) -> float:
        if not values:
            return 0.0
        return float(sum(values) / len(values))

    @staticmethod
    def _stddev(values: Sequence[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        return float(sqrt(variance))

    @staticmethod
    def _trend(values: Sequence[float], fallback: float = 0.0) -> float:
        if len(values) < 2:
            return fallback
        first = float(values[0])
        last = float(values[-1])
        return (last - first) / max(abs(first), 1.0)

    @staticmethod
    def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
        return float(max(lower, min(upper, value)))

