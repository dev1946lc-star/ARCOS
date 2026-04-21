from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RiskVerdict:
    approved: bool
    confidence: float
    score: float
    decision: str
    reason: str
    expected_profit: float
    cost_estimate: float
    profit_margin: float
    circuit_breaker_active: bool


class CircuitBreaker:
    """Adapted from AURORA to halt low-quality acceptance streaks."""

    def __init__(self, max_consecutive_losses: int = 4) -> None:
        self.max_consecutive_losses = max_consecutive_losses
        self._consecutive_losses = 0
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    def record_outcome(self, profitable: bool) -> None:
        if profitable:
            self._consecutive_losses = 0
            return
        self._consecutive_losses += 1
        if self._consecutive_losses >= self.max_consecutive_losses:
            self._active = True

    def reset(self) -> None:
        self._consecutive_losses = 0
        self._active = False


class RiskAgent:
    """Adapted from AURORA's risk agent for compute profitability checks."""

    def __init__(self, max_consecutive_losses: int = 4, cost_per_compute: float = 500.0) -> None:
        self.circuit_breaker = CircuitBreaker(max_consecutive_losses=max_consecutive_losses)
        self.cost_per_compute = float(cost_per_compute)

    def assess(
        self,
        *,
        price_offer: float,
        required_compute: float,
        predictor_confidence: float,
        queue_pressure: float,
        worker_load: float,
    ) -> RiskVerdict:
        cost_estimate = max(float(required_compute), 1.0) * self.cost_per_compute
        expected_profit = float(price_offer) - cost_estimate
        profit_margin = expected_profit / max(float(price_offer), 1.0)

        score = 0.0
        score += max(-1.0, min(1.0, profit_margin * 2.0)) * 0.55
        score += (predictor_confidence - 0.5) * 0.30
        score += max(-1.0, min(1.0, queue_pressure - worker_load)) * 0.15

        if self.circuit_breaker.is_active:
            score = min(score, -0.75)
            reason = "circuit_breaker_tripped"
            approved = False
        elif expected_profit <= 0:
            reason = "unprofitable"
            approved = False
        elif worker_load > 1.5 and queue_pressure < 0.75:
            reason = "overloaded_for_low_demand"
            approved = False
        else:
            reason = "approved"
            approved = score > -0.05

        confidence = min(1.0, max(0.0, abs(score)))
        decision = "accept" if approved else "reject"
        return RiskVerdict(
            approved=approved,
            confidence=round(confidence, 4),
            score=round(max(-1.0, min(1.0, score)), 4),
            decision=decision,
            reason=reason,
            expected_profit=round(expected_profit, 2),
            cost_estimate=round(cost_estimate, 2),
            profit_margin=round(profit_margin, 4),
            circuit_breaker_active=self.circuit_breaker.is_active,
        )
