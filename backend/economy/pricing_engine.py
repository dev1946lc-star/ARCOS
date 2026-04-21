from __future__ import annotations

from typing import Any

from core.config import get_int


class PricingEngine:
    """Dynamic sub-cent pricing shaped by ARCOS intelligence signals."""

    @property
    def max_price_micro_usdc(self) -> int:
        return max(100, get_int("ARCOS_MAX_PRICE_MICRO_USDC", 10_000))

    @property
    def min_price_micro_usdc(self) -> int:
        return max(1, min(self.max_price_micro_usdc, get_int("ARCOS_MIN_PRICE_MICRO_USDC", 500)))

    def compute_price(
        self,
        *,
        compute_units: int,
        predicted_profit: float,
        demand: int,
        agent_availability: int,
        confidence_score: float,
        predictor_score: float,
        strategy_score: float,
        scout_score: float,
        expected_value: float = 0.0,
        idle_capacity: int = 0,
        acceptance_rate: float = 0.5,
        recent_profit_trend: float = 0.0,
    ) -> dict[str, Any]:
        availability = max(agent_availability, 1)
        normalized_confidence = max(0.0, min(1.0, confidence_score))
        demand_pressure = min(2.0, demand / availability)
        scarcity_ratio = max(0.25, min(2.5, demand / availability if availability else 1.0))
        predictor_lift = max(-1.0, min(1.0, predictor_score))
        strategy_lift = max(-1.0, min(1.0, strategy_score))
        scout_lift = max(-1.0, min(1.0, scout_score))
        idle_penalty = min(1.0, max(0.0, idle_capacity / max(availability, 1)))

        if scarcity_ratio >= 1.35:
            market_pressure = "high"
        elif scarcity_ratio <= 0.8 and idle_penalty > 0.2:
            market_pressure = "low"
        else:
            market_pressure = "balanced"

        base_price = 550 + compute_units * 620
        profit_component = min(1800.0, max(0.0, predicted_profit) * 0.12)
        expected_value_component = min(1200.0, max(0.0, expected_value) * 0.08)
        demand_component = min(1800.0, demand_pressure * 1100 * min(1.4, scarcity_ratio))
        scarcity_component = {"low": -350.0, "balanced": 150.0, "high": 700.0}[market_pressure]
        idle_capacity_component = -600.0 * idle_penalty
        confidence_component = normalized_confidence * 1900
        adaptation_component = max(-500.0, min(500.0, ((acceptance_rate - 0.5) * 300) + (recent_profit_trend * 280)))
        intelligence_component = max(-900.0, min(900.0, (predictor_lift * 450) + (strategy_lift * 350) + (scout_lift * 220)))

        raw_price = (
            base_price
            + profit_component
            + expected_value_component
            + demand_component
            + scarcity_component
            + idle_capacity_component
            + confidence_component
            + adaptation_component
            + intelligence_component
        )
        price = int(max(self.min_price_micro_usdc, min(self.max_price_micro_usdc, raw_price)))
        price_per_unit = round(price / max(compute_units, 1), 4)

        reasons = [
            f"compute load {compute_units} units sets a base price of {base_price:.0f} micro-USDC",
            f"market pressure is {market_pressure} with scarcity ratio {scarcity_ratio:.2f}",
            f"demand contributes {demand_component:.0f} micro-USDC and idle capacity adjusts {idle_capacity_component:.0f}",
            f"confidence {normalized_confidence:.2f} contributes {confidence_component:.0f} micro-USDC",
            f"intelligence fusion contributes {intelligence_component:.0f} micro-USDC",
        ]

        return {
            "price_offer": price,
            "price_per_unit": price_per_unit,
            "pricing_reasoning": "; ".join(reasons),
            "market_pressure": market_pressure,
            "scarcity_ratio": round(scarcity_ratio, 4),
            "components": {
                "base_price": round(base_price, 2),
                "profit_component": round(profit_component, 2),
                "expected_value_component": round(expected_value_component, 2),
                "demand_component": round(demand_component, 2),
                "scarcity_component": round(scarcity_component, 2),
                "idle_capacity_component": round(idle_capacity_component, 2),
                "confidence_component": round(confidence_component, 2),
                "adaptation_component": round(adaptation_component, 2),
                "intelligence_component": round(intelligence_component, 2),
            },
        }


pricing_engine = PricingEngine()
