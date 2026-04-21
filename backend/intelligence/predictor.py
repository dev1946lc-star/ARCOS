from __future__ import annotations

import json
import math
from collections import OrderedDict, deque
from pathlib import Path
from typing import Any

try:
    import joblib  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    joblib = None


class Predictor:
    """Adapted from AURORA's predictor with ARCOS-safe heuristic fallback."""

    DEFAULT_FEATURES = {
        "price_per_compute": 0.55,
        "queue_pressure": 0.35,
        "profitability_index": 0.8,
        "offer_momentum": 0.0,
        "offer_volatility": 0.1,
        "workload_ratio": 1.0,
        "success_rate": 0.5,
        "demand_signal": 0.5,
        "expected_value_signal": 0.5,
    }

    def __init__(
        self,
        model_path: str | Path | None = None,
        feature_schema_path: str | Path | None = None,
        cache_size: int = 64,
        memory_size: int = 32,
    ) -> None:
        self.model_path = Path(model_path) if model_path else None
        self.feature_schema_path = Path(feature_schema_path) if feature_schema_path else None
        self.model: Any | None = None
        self.feature_columns: list[str] = []
        self._load_attempted = False
        self.cache_size = max(8, int(cache_size))
        self._prediction_cache: OrderedDict[tuple[tuple[str, float], ...], dict[str, Any]] = OrderedDict()
        self._decision_memory: deque[dict[str, float]] = deque(maxlen=max(8, int(memory_size)))

    def load(self) -> None:
        self._load_attempted = True
        if not self.model_path or not self.feature_schema_path or joblib is None:
            return
        if not self.model_path.exists() or not self.feature_schema_path.exists():
            return
        self.model = joblib.load(self.model_path)
        payload = json.loads(self.feature_schema_path.read_text(encoding="utf-8"))
        self.feature_columns = list(payload.get("feature_columns", []))

    def predict(self, features: dict[str, float | int | None]) -> dict[str, Any]:
        if not self._load_attempted:
            self.load()

        sanitized_features = self._sanitize_features(features)
        cache_key = tuple(sorted((key, round(value, 6)) for key, value in sanitized_features.items()))
        cached = self._prediction_cache.get(cache_key)
        if cached is not None:
            self._prediction_cache.move_to_end(cache_key)
            return dict(cached)

        reliability_factor = self._reliability_factor(sanitized_features)
        ml_score = self._ml_score(sanitized_features)
        heuristic_score = self._heuristic_score(sanitized_features)
        score = max(-1.0, min(1.0, ml_score * 0.6 + heuristic_score * 0.4))
        base_confidence = self._base_confidence(score, sanitized_features)
        confidence_adjusted = max(0.0, min(1.0, base_confidence * reliability_factor))
        threshold = self._dynamic_threshold()
        decision = self._label(score, confidence_adjusted, threshold)

        result = {
            "confidence": round(confidence_adjusted, 4),
            "confidence_adjusted": round(confidence_adjusted, 4),
            "base_confidence": round(base_confidence, 4),
            "reliability_factor": round(reliability_factor, 4),
            "score": round(score, 4),
            "decision": decision,
            "explanation": self._explain(sanitized_features, score),
            "source": "model" if self.model is not None and self.feature_columns else "heuristic",
            "ml_score": round(ml_score, 4),
            "heuristic_score": round(heuristic_score, 4),
            "memory": self.memory_snapshot(),
        }
        if not sanitized_features:
            result = self._default_result()
        self._store_cache(cache_key, result)
        return dict(result)

    def record_outcome(self, *, accepted: bool, success: bool, score: float, confidence: float) -> None:
        self._decision_memory.append(
            {
                "accepted": 1.0 if accepted else 0.0,
                "success": 1.0 if success else 0.0,
                "score": float(score),
                "confidence": float(confidence),
            }
        )

    def memory_snapshot(self) -> dict[str, float]:
        if not self._decision_memory:
            return {
                "decision_count": 0.0,
                "success_rate": 0.5,
                "acceptance_rate": 0.5,
                "average_score": 0.0,
            }
        count = float(len(self._decision_memory))
        success_rate = sum(item["success"] for item in self._decision_memory) / count
        acceptance_rate = sum(item["accepted"] for item in self._decision_memory) / count
        average_score = sum(item["score"] for item in self._decision_memory) / count
        return {
            "decision_count": count,
            "success_rate": round(success_rate, 4),
            "acceptance_rate": round(acceptance_rate, 4),
            "average_score": round(average_score, 4),
        }

    def _store_cache(self, cache_key: tuple[tuple[str, float], ...], result: dict[str, Any]) -> None:
        self._prediction_cache[cache_key] = dict(result)
        self._prediction_cache.move_to_end(cache_key)
        while len(self._prediction_cache) > self.cache_size:
            self._prediction_cache.popitem(last=False)

    def _sanitize_features(self, features: dict[str, float | int | None] | None) -> dict[str, float]:
        sanitized: dict[str, float] = {}
        source = features or {}
        for key, default_value in self.DEFAULT_FEATURES.items():
            sanitized[key] = self._normalize_value(key, source.get(key), default_value)

        for key, raw_value in source.items():
            if key in sanitized:
                continue
            normalized = self._safe_float(raw_value, None)
            if normalized is None:
                continue
            sanitized[key] = self._clamp_feature(key, normalized)
        return sanitized

    @staticmethod
    def _safe_float(value: Any, default: float | None) -> float | None:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return default
        if not math.isfinite(numeric):
            return default
        return numeric

    def _normalize_value(self, key: str, raw_value: Any, default: float) -> float:
        normalized = self._safe_float(raw_value, default)
        if normalized is None:
            return default
        return self._clamp_feature(key, normalized)

    @staticmethod
    def _clamp_feature(key: str, value: float) -> float:
        if key in {"offer_momentum", "compute_trend"}:
            return max(-1.0, min(1.0, value))
        if key in {"workload_ratio", "urgency", "market_heat", "profitability_index"}:
            return max(0.0, min(3.0, value))
        return max(0.0, min(1.0, value))

    def _default_result(self) -> dict[str, Any]:
        return {
            "confidence": 0.15,
            "confidence_adjusted": 0.15,
            "base_confidence": 0.2,
            "reliability_factor": 0.75,
            "score": 0.0,
            "decision": "accept",
            "explanation": "Insufficient signal quality, using neutral fallback prediction.",
            "source": "default",
            "ml_score": 0.0,
            "heuristic_score": 0.0,
            "memory": self.memory_snapshot(),
        }

    def _ml_score(self, features: dict[str, float]) -> float:
        if self.model is not None and self.feature_columns:
            try:
                ordered = [[float(features.get(column, 0.0)) for column in self.feature_columns]]
                probabilities = self.model.predict_proba(ordered)[-1]
                positive_probability = float(probabilities[1])
                return max(-1.0, min(1.0, (positive_probability - 0.5) * 2.0))
            except Exception:
                pass
        return self._heuristic_score(features)

    def _base_confidence(self, score: float, features: dict[str, float]) -> float:
        directional_strength = abs(score)
        signal_quality = (
            features.get("success_rate", 0.5) * 0.25
            + features.get("queue_pressure", 0.35) * 0.20
            + min(1.0, features.get("profitability_index", 0.8)) * 0.30
            + (1.0 - min(1.0, features.get("offer_volatility", 0.1))) * 0.25
        )
        return max(0.12, min(0.98, directional_strength * 0.55 + signal_quality * 0.45))

    def _reliability_factor(self, features: dict[str, float]) -> float:
        memory = self.memory_snapshot()
        feature_stability = 1.0 - min(0.45, features.get("offer_volatility", 0.1) * 0.7)
        workload_penalty = 1.0 - min(0.25, max(0.0, features.get("workload_ratio", 1.0) - 1.0) * 0.2)
        memory_support = 0.7 + (memory["success_rate"] - 0.5) * 0.6
        reliability = feature_stability * workload_penalty * memory_support
        return max(0.45, min(1.0, reliability))

    def _dynamic_threshold(self) -> float:
        memory = self.memory_snapshot()
        if memory["decision_count"] < 4:
            return 0.18
        drift = (0.55 - memory["success_rate"]) * 0.25
        return max(0.1, min(0.35, 0.18 + drift))

    @staticmethod
    def _heuristic_score(features: dict[str, float]) -> float:
        score = 0.0
        score += (features.get("price_per_compute", 0.0) - 0.55) * 0.35
        score += (features.get("queue_pressure", 0.0) - 0.35) * 0.16
        score += (features.get("profitability_index", 0.0) - 0.8) * 0.22
        score += features.get("offer_momentum", 0.0) * 0.10
        score -= features.get("offer_volatility", 0.0) * 0.16
        score -= max(0.0, features.get("workload_ratio", 1.0) - 1.0) * 0.15
        score += (features.get("success_rate", 0.5) - 0.5) * 0.12
        score += (features.get("demand_signal", 0.5) - 0.5) * 0.12
        score += (features.get("expected_value_signal", 0.5) - 0.5) * 0.18
        return max(-1.0, min(1.0, score))

    @staticmethod
    def _label(score: float, confidence: float, threshold: float) -> str:
        if score >= threshold + 0.12 and confidence >= threshold:
            return "prioritize"
        if score <= -(threshold + 0.05):
            return "reject"
        return "accept"

    @staticmethod
    def _explain(features: dict[str, float], score: float) -> str:
        signals: list[str] = []
        if features.get("offer_volatility", 0.0) > 0.35:
            signals.append("high volatility")
        if features.get("offer_momentum", 0.0) > 0.12:
            signals.append("upward momentum")
        elif features.get("offer_momentum", 0.0) < -0.12:
            signals.append("downward momentum")
        if features.get("price_per_compute", 0.0) > 0.65:
            signals.append("strong pricing")
        if features.get("queue_pressure", 0.0) > 0.65:
            signals.append("elevated demand")
        if features.get("profitability_index", 0.0) > 1.0:
            signals.append("healthy profitability")
        if features.get("workload_ratio", 0.0) > 1.25:
            signals.append("heavy workload")
        if features.get("success_rate", 0.0) > 0.65:
            signals.append("strong execution history")

        if not signals:
            return "Signals are mixed, so the predictor is staying close to neutral."

        top_signals = signals[:2]
        tone = "supports a positive execution outlook" if score >= 0.1 else "suggests caution" if score <= -0.1 else "creates a balanced outlook"
        return f"{' + '.join(part.capitalize() for part in top_signals)} {tone}."
