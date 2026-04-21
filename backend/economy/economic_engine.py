from __future__ import annotations

from collections import defaultdict
from typing import Any


class EconomicEngine:
    """Utility layer for expected value and simulation-wide economics metrics."""

    DEFAULT_COST_PER_COMPUTE = 500.0

    def evaluate_job(self, job: dict[str, Any], agent_state: dict[str, Any] | None = None) -> dict[str, Any]:
        state = agent_state or {}
        price_offer = float(job.get("price_offer", 0.0))
        required_compute = max(float(job.get("required_compute", 0.0)), 0.0)
        confidence = self._clamp(float(state.get("confidence", 0.5)), 0.0, 1.0)
        cost = float(state.get("cost", required_compute * float(state.get("cost_per_compute", self.DEFAULT_COST_PER_COMPUTE))))
        revenue = float(state.get("revenue", price_offer))
        demand = max(float(state.get("demand", 1.0)), 0.0)
        supply = max(float(state.get("supply", 1.0)), 1.0)
        scarcity_ratio = max(0.25, min(3.0, demand / supply))
        expected_value = price_offer * confidence
        adjusted_expected_value = expected_value * (0.85 + min(0.5, scarcity_ratio * 0.15))
        profit = revenue - cost
        profit_margin = profit / max(revenue, 1.0)
        demand_score = self._clamp(scarcity_ratio / 2.0, 0.0, 1.0)
        if scarcity_ratio >= 1.35:
            market_pressure = "high"
        elif scarcity_ratio <= 0.8:
            market_pressure = "low"
        else:
            market_pressure = "balanced"

        return {
            "price_offer": round(price_offer, 2),
            "confidence": round(confidence, 4),
            "expected_value": round(expected_value, 2),
            "adjusted_expected_value": round(adjusted_expected_value, 2),
            "revenue": round(revenue, 2),
            "cost": round(cost, 2),
            "profit": round(profit, 2),
            "profit_margin": round(profit_margin, 4),
            "profitable": profit > 0,
            "demand_score": round(demand_score, 4),
            "scarcity_ratio": round(scarcity_ratio, 4),
            "market_pressure": market_pressure,
        }

    def adaptive_strategy(
        self,
        *,
        recent_profit: float,
        acceptance_rate: float,
        success_rate: float,
    ) -> dict[str, float | str]:
        profit_signal = self._clamp(recent_profit / 5000.0, -1.0, 1.0)
        acceptance_signal = self._clamp((acceptance_rate - 0.5) * 2.0, -1.0, 1.0)
        success_signal = self._clamp((success_rate - 0.5) * 2.0, -1.0, 1.0)
        aggression = self._clamp(0.5 + profit_signal * 0.25 + acceptance_signal * 0.15 + success_signal * 0.1, 0.1, 0.95)
        if aggression >= 0.68:
            profile = "aggressive"
        elif aggression <= 0.38:
            profile = "conservative"
        else:
            profile = "balanced"
        return {
            "aggression": round(aggression, 4),
            "profit_signal": round(profit_signal, 4),
            "acceptance_signal": round(acceptance_signal, 4),
            "success_signal": round(success_signal, 4),
            "profile": profile,
        }

    def compute_metrics(
        self,
        *,
        completed_jobs: list[dict[str, Any]] | None = None,
        events: list[dict[str, Any]] | None = None,
        transactions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        completed_jobs = completed_jobs or []
        events = events or []
        transactions = transactions or []

        payments = [event for event in events if event.get("type") in {"payment_sent", "transaction_created"}]
        accepted = [event for event in events if event.get("type") == "job_accepted"]
        rejected = [event for event in events if event.get("type") == "job_rejected"]
        successful_transactions = [tx for tx in transactions if tx.get("status") == "success"]

        prices = [float(job.get("price_offer", 0.0)) for job in completed_jobs]
        confidences = [float((job.get("economic") or {}).get("confidence", 0.0)) for job in completed_jobs]
        profits = [float((job.get("economic") or {}).get("profit", 0.0)) for job in completed_jobs]
        revenues = [float((job.get("economic") or {}).get("revenue", float(job.get("price_offer", 0.0)))) for job in completed_jobs]
        transaction_values = [float(tx.get("amount", 0.0)) for tx in successful_transactions]
        transaction_timestamps = [float(tx.get("timestamp", 0.0)) for tx in transactions]
        efficiency_inputs = [float((job.get("economic") or {}).get("adjusted_expected_value", 0.0)) for job in completed_jobs]

        total_profit = sum(profits)
        total_revenue = sum(revenues)
        total_value_transferred = sum(transaction_values)
        decisions = len(accepted) + len(rejected)
        agent_profit: dict[str, float] = defaultdict(float)
        agent_jobs: dict[str, int] = defaultdict(int)
        agent_success: dict[str, int] = defaultdict(int)
        pressure_counts: dict[str, int] = defaultdict(int)
        for job in completed_jobs:
            compute_wallet = str(job.get("compute_wallet") or (job.get("execution") or {}).get("compute_wallet") or "unknown")
            agent_profit[compute_wallet] += float((job.get("economic") or {}).get("profit", 0.0))
            agent_jobs[compute_wallet] += 1
            if float((job.get("economic") or {}).get("profit", 0.0)) > 0:
                agent_success[compute_wallet] += 1
            pressure = str((job.get("economic") or {}).get("market_pressure", "balanced"))
            pressure_counts[pressure] += 1

        efficiency = 0.0
        if total_revenue > 0:
            efficiency = self._clamp((total_profit / total_revenue) * 0.7 + (sum(efficiency_inputs) / max(total_revenue, 1.0)) * 0.3, 0.0, 1.0)
        tx_elapsed = max(transaction_timestamps) - min(transaction_timestamps) if len(transaction_timestamps) > 1 else 0.0
        transaction_rate = (len(transactions) / tx_elapsed) if tx_elapsed > 0 else float(len(transactions))

        avg_profit_per_agent = total_profit / max(len(agent_profit), 1) if agent_profit else 0.0
        most_common_pressure = max(pressure_counts, key=pressure_counts.get, default="balanced")

        return {
            "total_transactions": len(transactions) or len(payments),
            "avg_price": round(sum(prices) / len(prices), 2) if prices else 0.0,
            "avg_confidence": round(sum(confidences) / len(confidences), 4) if confidences else 0.0,
            "economic_efficiency": round(efficiency, 4),
            "system_efficiency_score": round(efficiency, 4),
            "avg_profit": round(total_profit / len(profits), 2) if profits else 0.0,
            "avg_profit_per_agent": round(avg_profit_per_agent, 2),
            "acceptance_rate": round(len(accepted) / decisions, 4) if decisions else 0.0,
            "avg_transaction_value": round(sum(transaction_values) / len(transaction_values), 2) if transaction_values else 0.0,
            "transaction_rate": round(transaction_rate, 4),
            "tx_per_second": round(transaction_rate, 4),
            "success_rate": round(len(successful_transactions) / len(transactions), 4) if transactions else 0.0,
            "success_failure_ratio": round(len(successful_transactions) / max(len(transactions) - len(successful_transactions), 1), 4) if transactions else 0.0,
            "avg_settlement_time": round(
                sum(float(tx.get("latency_ms", 0.0)) for tx in successful_transactions) / len(successful_transactions),
                2,
            ) if successful_transactions else 0.0,
            "agent_profit": {key: round(value, 2) for key, value in agent_profit.items()},
            "total_value_transferred": round(total_value_transferred, 2),
            "market_pressure": most_common_pressure,
            "agent_success_rate": {
                key: round(agent_success[key] / max(agent_jobs[key], 1), 4)
                for key in agent_jobs
            },
        }

    @staticmethod
    def _clamp(value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))


economic_engine = EconomicEngine()
