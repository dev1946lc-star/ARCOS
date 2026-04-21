from __future__ import annotations

import math
import re
from collections import deque

try:
    from textblob import TextBlob  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    TextBlob = None


class ScoutAgentV2:
    """Lightweight sentiment scout with optional TextBlob support."""

    POSITIVE_WEIGHTS = {
        "optimize": 0.45,
        "forecast": 0.35,
        "report": 0.18,
        "analyze": 0.2,
        "generate": 0.15,
        "train": 0.3,
        "market": 0.22,
        "profit": 0.4,
        "efficient": 0.32,
        "stable": 0.3,
        "autonomous": 0.24,
        "reliable": 0.28,
    }
    NEGATIVE_WEIGHTS = {
        "risk": -0.35,
        "volatile": -0.42,
        "failure": -0.5,
        "delay": -0.28,
        "overload": -0.38,
        "expensive": -0.33,
        "loss": -0.45,
        "audit": -0.12,
        "decrypt": -0.15,
        "slow": -0.22,
    }
    INTENSIFIERS = {"very": 1.2, "high": 1.15, "urgent": 1.15, "strong": 1.18}
    NEGATORS = {"not", "no", "never", "without", "hardly"}

    def __init__(self, memory_size: int = 24) -> None:
        self._decision_memory: deque[dict[str, float]] = deque(maxlen=max(8, int(memory_size)))

    def analyze(self, text: str | None) -> dict[str, float]:
        content = (text or "").strip()
        if not content:
            return {
                "sentiment_score": 0.0,
                "confidence": 0.1,
                "confidence_adjusted": 0.1,
                "reliability_factor": 1.0,
            }

        if TextBlob is not None:
            try:
                polarity = float(TextBlob(content).sentiment.polarity)
                score = max(-1.0, min(1.0, polarity))
                confidence = min(1.0, 0.35 + abs(score) * 0.65)
                reliability_factor = self._reliability_factor(abs(score), len(content.split()))
                return {
                    "sentiment_score": round(score, 4),
                    "confidence": round(confidence * reliability_factor, 4),
                    "confidence_adjusted": round(confidence * reliability_factor, 4),
                    "base_confidence": round(confidence, 4),
                    "reliability_factor": round(reliability_factor, 4),
                }
            except Exception:
                pass

        tokens = re.findall(r"[a-zA-Z']+", content.lower())
        if not tokens:
            return {
                "sentiment_score": 0.0,
                "confidence": 0.1,
                "confidence_adjusted": 0.1,
                "reliability_factor": 1.0,
            }

        weighted_score = 0.0
        hits = 0
        for index, token in enumerate(tokens):
            base_weight = self.POSITIVE_WEIGHTS.get(token, 0.0) + self.NEGATIVE_WEIGHTS.get(token, 0.0)
            if base_weight == 0.0:
                continue

            hits += 1
            modifier = 1.0
            window = tokens[max(0, index - 2):index]
            if any(word in self.NEGATORS for word in window):
                modifier *= -1.0
            for word in window:
                modifier *= self.INTENSIFIERS.get(word, 1.0)
            weighted_score += base_weight * modifier

        length_penalty = min(1.0, math.sqrt(len(tokens)) / 4.0)
        normalized = max(-1.0, min(1.0, weighted_score * length_penalty))
        confidence = min(1.0, 0.2 + min(hits, 4) * 0.18 + abs(normalized) * 0.2)
        reliability_factor = self._reliability_factor(abs(normalized), len(tokens))
        adjusted = confidence * reliability_factor
        return {
            "sentiment_score": round(normalized, 4),
            "confidence": round(adjusted, 4),
            "confidence_adjusted": round(adjusted, 4),
            "base_confidence": round(confidence, 4),
            "reliability_factor": round(reliability_factor, 4),
        }

    def record_outcome(self, *, success: bool, score: float) -> None:
        self._decision_memory.append({"success": 1.0 if success else 0.0, "score": float(score)})

    def memory_snapshot(self) -> dict[str, float]:
        if not self._decision_memory:
            return {"success_rate": 0.5, "average_score": 0.0}
        count = float(len(self._decision_memory))
        return {
            "success_rate": round(sum(item["success"] for item in self._decision_memory) / count, 4),
            "average_score": round(sum(item["score"] for item in self._decision_memory) / count, 4),
        }

    def _reliability_factor(self, score_strength: float, token_count: int) -> float:
        memory = self.memory_snapshot()
        size_factor = max(0.55, min(1.0, 0.45 + min(token_count, 12) / 18.0))
        memory_factor = 0.75 + (memory["success_rate"] - 0.5) * 0.5
        signal_factor = 0.7 + score_strength * 0.3
        return max(0.45, min(1.0, size_factor * memory_factor * signal_factor))
