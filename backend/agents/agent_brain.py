from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersonalityProfile:
    personality_type: str
    threshold_factor: float
    min_profit_margin: float
    throughput_bias: float
    base_risk_appetite: float
    explanation: str


class AgentBrain:
    PERSONALITIES = {
        "greedy": PersonalityProfile(
            personality_type="greedy",
            threshold_factor=0.7,
            min_profit_margin=0.02,
            throughput_bias=1.2,
            base_risk_appetite=0.75,
            explanation="accepts thinner margins to maximize flow",
        ),
        "balanced": PersonalityProfile(
            personality_type="balanced",
            threshold_factor=1.0,
            min_profit_margin=0.08,
            throughput_bias=1.0,
            base_risk_appetite=0.5,
            explanation="balances profit discipline with healthy throughput",
        ),
        "conservative": PersonalityProfile(
            personality_type="conservative",
            threshold_factor=1.3,
            min_profit_margin=0.18,
            throughput_bias=0.8,
            base_risk_appetite=0.25,
            explanation="waits for strong expected value and cleaner margins",
        ),
    }

    DEFAULT_ROTATION = ("balanced", "greedy", "conservative")

    def select_personality(self, agent_id: str) -> PersonalityProfile:
        if not agent_id:
            return self.PERSONALITIES["balanced"]
        numeric = sum(ord(char) for char in agent_id)
        personality = self.DEFAULT_ROTATION[numeric % len(self.DEFAULT_ROTATION)]
        return self.PERSONALITIES[personality]

    def evaluate_thresholds(
        self,
        personality_type: str,
        *,
        base_threshold: float,
        risk_appetite: float | None = None,
        profit_trend: float = 0.0,
    ) -> dict[str, float]:
        profile = self.PERSONALITIES.get(personality_type, self.PERSONALITIES["balanced"])
        appetite = max(0.0, min(1.0, profile.base_risk_appetite if risk_appetite is None else risk_appetite))
        trend_adjustment = max(-0.25, min(0.25, profit_trend * 0.12))
        decision_threshold = base_threshold * profile.threshold_factor * (1.15 - appetite * 0.3) * (1.0 - trend_adjustment)
        min_profit_margin = profile.min_profit_margin * (1.2 - appetite * 0.35) * (1.0 - trend_adjustment * 0.5)
        throughput_bias = profile.throughput_bias * (0.9 + appetite * 0.25) * (1.0 + trend_adjustment * 0.4)
        return {
            "decision_threshold": round(max(0.02, min(0.4, decision_threshold)), 4),
            "min_profit_margin": round(max(0.01, min(0.4, min_profit_margin)), 4),
            "throughput_bias": round(max(0.5, min(1.8, throughput_bias)), 4),
            "risk_appetite": round(appetite, 4),
            "profit_trend": round(profit_trend, 4),
        }

    @staticmethod
    def evolve_behavior(*, base_profile: PersonalityProfile, recent_profit: float, acceptance_rate: float) -> dict[str, float | str]:
        profit_trend = max(-1.0, min(1.0, recent_profit / 4000.0))
        risk_shift = profit_trend * 0.18 + (acceptance_rate - 0.5) * 0.12
        risk_appetite = max(0.05, min(0.95, base_profile.base_risk_appetite + risk_shift))
        if risk_appetite >= 0.68:
            risk_level = "high"
        elif risk_appetite <= 0.35:
            risk_level = "low"
        else:
            risk_level = "medium"
        return {
            "risk_appetite": round(risk_appetite, 4),
            "profit_trend": round(profit_trend, 4),
            "risk_level": risk_level,
        }


agent_brain = AgentBrain()
