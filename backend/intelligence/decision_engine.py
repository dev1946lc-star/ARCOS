from __future__ import annotations

from typing import Any


class DecisionEngine:
    """Adapted from AURORA's decision engine for generic ARCOS jobs."""

    def decide(
        self,
        *,
        predictor_score: float,
        profitability_score: float,
        risk_score: float,
        technical_signals: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        technical_signals = technical_signals or {}
        predictor_component = predictor_score * 0.45
        profitability_component = profitability_score * 0.35
        risk_component = risk_score * 0.20
        score = predictor_component + profitability_component + risk_component
        confidence = min(1.0, abs(score))

        positive_signals = sum(
            1
            for signal in (
                predictor_score > 0.15,
                profitability_score > 0.10,
                risk_score > 0.0,
                technical_signals.get("momentum_positive", False),
                technical_signals.get("demand_supportive", False),
            )
            if signal
        )
        negative_signals = sum(
            1
            for signal in (
                predictor_score < -0.10,
                profitability_score < -0.05,
                risk_score < -0.10,
                technical_signals.get("volatility_high", False),
                technical_signals.get("overloaded", False),
            )
            if signal
        )

        decision = "accept"
        reasoning: list[str] = []
        if score >= 0.35 or positive_signals >= 4:
            decision = "prioritize"
            reasoning.append("Strong multi-signal confluence")
        elif score <= -0.15 or negative_signals >= 3:
            decision = "reject"
            reasoning.append("Risk/profitability profile is unfavorable")
        else:
            reasoning.append("Balanced profile supports standard acceptance")

        if predictor_score > 0.2:
            reasoning.append("Predictor sees strong execution potential")
        if profitability_score > 0.15:
            reasoning.append("Expected reward covers compute cost")
        if risk_score < 0.0:
            reasoning.append("Risk layer is applying a penalty")

        return {
            "confidence": round(confidence, 4),
            "score": round(max(-1.0, min(1.0, score)), 4),
            "decision": decision,
            "reasoning": reasoning,
            "components": {
                "predictor_component": round(predictor_component, 4),
                "profitability_component": round(profitability_component, 4),
                "risk_component": round(risk_component, 4),
            },
            "signals": technical_signals,
        }

