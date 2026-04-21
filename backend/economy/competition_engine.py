from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


class CompetitionEngine:
    def __init__(self) -> None:
        self._agents: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "agent": "",
                "profit": 0.0,
                "jobs": 0,
                "roi": 0.0,
                "revenue": 0.0,
                "cost": 0.0,
                "accepted": 0,
                "rejected": 0,
                "personality": "balanced",
                "risk_level": "medium",
                "risk_appetite": 0.5,
                "profit_trend": 0.0,
                "recent_profit": deque(maxlen=8),
                "wins": 0,
                "losses": 0,
            }
        )

    def record_job(
        self,
        *,
        agent_id: str,
        profit: float,
        revenue: float,
        cost: float,
        personality: str = "balanced",
        risk_level: str = "medium",
        risk_appetite: float = 0.5,
        profit_trend: float = 0.0,
    ) -> None:
        record = self._agents[agent_id]
        record["agent"] = agent_id
        record["profit"] += float(profit)
        record["jobs"] += 1
        record["revenue"] += float(revenue)
        record["cost"] += float(cost)
        record["personality"] = personality
        record["risk_level"] = risk_level
        record["risk_appetite"] = float(risk_appetite)
        record["profit_trend"] = float(profit_trend)
        record["roi"] = round(record["profit"] / max(record["cost"], 1.0), 4)
        record["recent_profit"].append(float(profit))
        if profit >= 0:
            record["wins"] += 1
        else:
            record["losses"] += 1

    def record_decision(self, *, agent_id: str, accepted: bool, personality: str = "balanced", risk_level: str = "medium") -> None:
        record = self._agents[agent_id]
        record["agent"] = agent_id
        record["personality"] = personality
        record["risk_level"] = risk_level
        if accepted:
            record["accepted"] += 1
        else:
            record["rejected"] += 1

    @staticmethod
    def _trend_symbol(values: deque[float]) -> str:
        if len(values) < 2:
            return "→"
        if values[-1] > values[0]:
            return "↑"
        if values[-1] < values[0]:
            return "↓"
        return "→"

    def leaderboard(self) -> list[dict[str, Any]]:
        leaders = sorted(
            self._agents.values(),
            key=lambda item: (item["profit"], item["jobs"], item["roi"]),
            reverse=True,
        )
        output = []
        for entry in leaders:
            total_decisions = max(entry["accepted"] + entry["rejected"], 1)
            win_rate = entry["wins"] / max(entry["wins"] + entry["losses"], 1)
            trend = self._trend_symbol(entry["recent_profit"])
            output.append(
                {
                    "agent": entry["agent"],
                    "profit": round(entry["profit"], 2),
                    "jobs": int(entry["jobs"]),
                    "roi": round(entry["roi"], 4),
                    "acceptance_rate": round(entry["accepted"] / total_decisions, 4),
                    "personality": entry["personality"],
                    "risk_level": entry["risk_level"],
                    "risk_appetite": round(entry["risk_appetite"], 4),
                    "profit_trend": round(entry["profit_trend"], 4),
                    "recent_trend": trend,
                    "win_rate": round(win_rate, 4),
                    "reputation_score": round(
                        max(0.0, min(1.0, 0.5 + (entry["roi"] * 0.2) + ((entry["accepted"] - entry["rejected"]) * 0.02))),
                        4,
                    ),
                }
            )
        return output

    def top_agent(self) -> str | None:
        leaders = self.leaderboard()
        return leaders[0]["agent"] if leaders else None

    def get_agent(self, agent_id: str) -> dict[str, Any]:
        record = self._agents.get(agent_id) or {}
        if not record:
            return {
                "agent": agent_id,
                "profit": 0.0,
                "jobs": 0,
                "roi": 0.0,
                "acceptance_rate": 0.0,
                "personality": "balanced",
                "risk_level": "medium",
                "risk_appetite": 0.5,
                "profit_trend": 0.0,
                "recent_trend": "→",
                "win_rate": 0.0,
                "reputation_score": 0.5,
            }
        total_decisions = max(record["accepted"] + record["rejected"], 1)
        return {
            "agent": agent_id,
            "profit": round(record["profit"], 2),
            "jobs": int(record["jobs"]),
            "roi": round(record["roi"], 4),
            "acceptance_rate": round(record["accepted"] / total_decisions, 4),
            "personality": record["personality"],
            "risk_level": record["risk_level"],
            "risk_appetite": round(record["risk_appetite"], 4),
            "profit_trend": round(record["profit_trend"], 4),
            "recent_trend": self._trend_symbol(record["recent_profit"]),
            "win_rate": round(record["wins"] / max(record["wins"] + record["losses"], 1), 4),
            "reputation_score": round(
                max(0.0, min(1.0, 0.5 + (record["roi"] * 0.2) + ((record["accepted"] - record["rejected"]) * 0.02))),
                4,
            ),
        }


competition_engine = CompetitionEngine()
