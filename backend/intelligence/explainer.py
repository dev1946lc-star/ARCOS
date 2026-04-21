from __future__ import annotations

from typing import Any


class Explainer:
    """Small, human-readable reasoning layer for job pricing and acceptance."""

    @staticmethod
    def _top_factors(candidates: list[tuple[str, float]]) -> list[str]:
        ranked = sorted(candidates, key=lambda item: abs(item[1]), reverse=True)
        return [label for label, _ in ranked[:3] if label]

    def explain_pricing(
        self,
        *,
        prediction: dict[str, Any],
        strategy: dict[str, Any],
        scout: dict[str, Any],
        economic: dict[str, Any],
        pricing: dict[str, Any],
        fusion: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fusion = fusion or {}
        factors = fusion.get("factors") or {}
        top_factors = self._top_factors(
            [
                ("high expected value", float(economic.get("adjusted_expected_value", 0.0))),
                ("strong ML confidence", float(factors.get("ml", prediction.get("score", 0.0)))),
                ("supportive technical setup", float(factors.get("technical", strategy.get("score", 0.0)))),
                ("positive scout sentiment", float(factors.get("sentiment", scout.get("sentiment_score", 0.0)))),
                ("high demand pressure", 1.0 if pricing.get("market_pressure") == "high" else 0.0),
            ]
        )
        natural = (
            f"Priced higher because {', '.join(top_factors[:2])}"
            if top_factors
            else "Priced near baseline because signals were balanced."
        )
        return {
            "why_accepted": f"Research pricing is elevated because {pricing.get('reasoning', 'market conditions favor this job')}.",
            "why_rejected": "",
            "key_factors": top_factors or ["balanced market conditions"],
            "top_factors": top_factors or ["balanced market conditions"],
            "explanation": natural + ".",
        }

    def explain_decision(
        self,
        *,
        accepted: bool,
        economic: dict[str, Any],
        decision: dict[str, Any] | None,
        rejection_reasons: list[str],
        behavior: dict[str, Any] | None = None,
        risk_reason: str | None = None,
        fusion: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fusion = fusion or {}
        factors: list[tuple[str, float]] = []
        if float(economic.get("adjusted_expected_value", economic.get("expected_value", 0.0))) > 0:
            factors.append(("high expected value", float(economic.get("adjusted_expected_value", economic.get("expected_value", 0.0)))))
        if float(economic.get("profit_margin", 0.0)) > 0.1:
            factors.append(("healthy profit margin", float(economic.get("profit_margin", 0.0))))
        if decision and float(decision.get("score", 0.0)) > 0.1:
            factors.append(("decision score above threshold", float(decision.get("score", 0.0))))
        if risk_reason == "approved":
            factors.append(("low risk", 0.9))
        if behavior and behavior.get("risk_level") == "high":
            factors.append(("aggressive risk appetite", 0.45))
        if behavior and behavior.get("risk_level") == "low":
            factors.append(("conservative risk posture", 0.45))
        for name, value in (fusion.get("factors") or {}).items():
            label = {
                "ml": "strong ML signal",
                "technical": "supportive technical signal",
                "economic": "favorable economics",
                "sentiment": "positive scout sentiment",
            }.get(name)
            if label:
                factors.append((label, float(value)))

        top_factors = self._top_factors(factors)

        if accepted:
            why_accepted = "Accepted due to " + ", ".join(top_factors[:3]) + "." if top_factors else "Accepted because value and risk cleared the threshold."
            why_rejected = ""
            natural = why_accepted
        else:
            primary_reason = rejection_reasons[0] if rejection_reasons else "threshold policy"
            why_accepted = ""
            why_rejected = f"Rejected because {primary_reason.replace('_', ' ')}."
            natural = why_rejected

        return {
            "why_accepted": why_accepted,
            "why_rejected": why_rejected,
            "key_factors": top_factors or ["mixed signals"],
            "top_factors": top_factors or ["mixed signals"],
            "explanation": natural,
        }


explainer = Explainer()
