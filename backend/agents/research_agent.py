import asyncio
import json
import logging
import os
from collections import deque
import random
import time
import uuid

from economy.economic_engine import economic_engine
from economy.pricing_engine import pricing_engine
from intelligence.explainer import explainer
from intelligence.feature_engineering import FeatureEngineering
from intelligence.predictor import Predictor
from intelligence.scout_agent_v2 import ScoutAgentV2
from intelligence.strategy_analyzer import StrategyAnalyzer

logger = logging.getLogger("ResearchAgent")

JOB_DESCRIPTIONS = [
    "Generate BTC Momentum Signal",
    "Analyze ETH Volatility Pattern",
    "Detect Cross-DEX Arbitrage",
    "Predict Market Sentiment Shift",
    "Validate Trading Strategy Alpha",
    "Score Liquidity Pool Depth",
    "Backtest Mean Reversion Model",
    "Assess DeFi Yield Opportunity",
]


class ResearchAgent:
    def __init__(self, wallet, private_key, market, event_bus=None, agent_id="ResearchAgent"):
        self.wallet = wallet
        self.private_key = private_key
        self.market = market
        self.event_bus = event_bus
        self.agent_id = agent_id
        self.running = False
        self.feature_engineering = FeatureEngineering()
        self.predictor = Predictor()
        self.strategy_analyzer = StrategyAnalyzer()
        self.scout_agent = ScoutAgentV2()
        self.offer_history = deque(maxlen=24)
        self.workload_history = deque(maxlen=24)
        self.jobs_created = 0
        self.jobs_priced_intelligently = 0
        self.feature_refresh_interval = 0.5
        self._pricing_cache = {}
        self._pricing_cache_order = deque()
        self._recent_outcomes = deque(maxlen=20)

    def _emit(self, event_type, data):
        if self.event_bus:
            self.event_bus.publish(event_type, {**data, "agent_id": self.agent_id})

    def _log_structured(self, event_name, payload):
        logger.info(json.dumps({"event": event_name, "agent_id": self.agent_id, **payload}, default=str))

    @staticmethod
    def _bounded(value, lower, upper):
        return max(lower, min(upper, value))

    def _estimate_active_compute_agents(self):
        try:
            from economy import simulation_engine

            count = sum(1 for agent in simulation_engine.agent_registry if agent.get("role") == "compute")
            return max(1, count)
        except Exception:
            return max(1, len(getattr(self.market, "pending_jobs", [])) + 1)

    def _cache_lookup(self, cache_key):
        entry = self._pricing_cache.get(cache_key)
        if not entry:
            return None
        if time.monotonic() - entry["timestamp"] > self.feature_refresh_interval:
            return None
        return entry

    def _cache_store(self, cache_key, price_offer, intelligence):
        if cache_key in self._pricing_cache:
            try:
                self._pricing_cache_order.remove(cache_key)
            except ValueError:
                pass
        self._pricing_cache[cache_key] = {
            "timestamp": time.monotonic(),
            "price_offer": price_offer,
            "intelligence": intelligence,
        }
        self._pricing_cache_order.append(cache_key)
        while len(self._pricing_cache_order) > 32:
            oldest = self._pricing_cache_order.popleft()
            self._pricing_cache.pop(oldest, None)

    def _success_rate(self):
        if not self._recent_outcomes:
            return 0.5
        return sum(self._recent_outcomes) / len(self._recent_outcomes)

    def _fuse_intelligence(self, prediction, strategy, economic, scout, feature_vector):
        factors = {
            "ml": round(float(prediction.get("score", 0.0)), 4),
            "technical": round(float(strategy.get("technical_score", strategy.get("score", 0.0))), 4),
            "economic": round(
                self._bounded(
                    (float(economic.get("profit_margin", 0.0)) * 1.8)
                    + (float(economic.get("demand_score", 0.0)) * 0.8)
                    + ((float(economic.get("adjusted_expected_value", 0.0)) / max(float(economic.get("price_offer", 1.0)), 1.0)) - 0.5),
                    -1.0,
                    1.0,
                ),
                4,
            ),
            "sentiment": round(float(scout.get("sentiment_score", 0.0)), 4),
        }
        score = self._bounded(
            factors["ml"] * 0.32 + factors["technical"] * 0.28 + factors["economic"] * 0.28 + factors["sentiment"] * 0.12,
            -1.0,
            1.0,
        )
        reliability_factor = self._bounded(
            float(prediction.get("reliability_factor", 1.0)) * 0.35
            + float(strategy.get("reliability_factor", 1.0)) * 0.25
            + float(scout.get("reliability_factor", 1.0)) * 0.15
            + (0.75 + self._success_rate() * 0.25) * 0.25,
            0.45,
            1.0,
        )
        base_confidence = self._bounded(
            float(prediction.get("base_confidence", prediction.get("confidence", 0.0))) * 0.4
            + float(strategy.get("base_confidence", strategy.get("confidence", 0.0))) * 0.3
            + float(scout.get("base_confidence", scout.get("confidence", 0.0))) * 0.15
            + float(economic.get("confidence", 0.5)) * 0.15,
            0.1,
            1.0,
        )
        confidence_adjusted = self._bounded(base_confidence * reliability_factor, 0.05, 1.0)
        if score >= 0.3 and confidence_adjusted >= 0.22:
            decision = "prioritize"
        elif score <= -0.12:
            decision = "reject"
        else:
            decision = "accept"
        return {
            "decision": decision,
            "confidence": round(confidence_adjusted, 4),
            "confidence_adjusted": round(confidence_adjusted, 4),
            "base_confidence": round(base_confidence, 4),
            "reliability_factor": round(reliability_factor, 4),
            "score": round(score, 4),
            "factors": factors,
            "memory": {
                "success_rate": round(self._success_rate(), 4),
                "priced_jobs": self.jobs_priced_intelligently,
            },
            "features": feature_vector.values,
        }

    def _build_intelligent_pricing(self, description, required_compute):
        queue_depth = len(getattr(self.market, "pending_jobs", []))
        completed_jobs = len(getattr(self.market, "completed_jobs", []))
        active_compute_agents = self._estimate_active_compute_agents()
        idle_capacity = max(0, active_compute_agents - min(queue_depth, active_compute_agents))
        success_rate = self._success_rate()
        recent_profit_trend = 0.0
        if self._recent_outcomes:
            recent_window = list(self._recent_outcomes)[-5:]
            recent_profit_trend = (sum(recent_window) / max(len(recent_window), 1)) - 0.5
        cache_key = (
            description.lower(),
            int(required_compute),
            queue_depth,
            completed_jobs,
            active_compute_agents,
            round(success_rate, 2),
            tuple(int(value / 100) for value in list(self.offer_history)[-4:]),
            tuple(int(value) for value in list(self.workload_history)[-4:]),
        )
        cached = self._cache_lookup(cache_key)
        if cached is not None:
            return cached["price_offer"], cached["intelligence"]

        baseline_price = required_compute * random.randint(550, 820)
        feature_vector = self.feature_engineering.generate(
            required_compute=required_compute,
            price_offer=baseline_price,
            queue_depth=queue_depth,
            completed_jobs=completed_jobs,
            active_compute_agents=active_compute_agents,
            recent_offers=list(self.offer_history),
            recent_workloads=list(self.workload_history),
            success_rate=success_rate,
        )
        feature_vector.values["demand_signal"] = self._bounded(queue_depth / max(active_compute_agents, 1), 0.0, 1.0)
        feature_vector.values["expected_value_signal"] = self._bounded(baseline_price / max(required_compute * 1200, 1), 0.0, 1.0)

        prediction = self.predictor.predict(feature_vector.values)
        strategy = self.strategy_analyzer.analyze(
            feature_vector=feature_vector.values,
            recent_offers=list(self.offer_history),
            recent_workloads=list(self.workload_history),
        )
        scout = self.scout_agent.analyze(description)

        economic = economic_engine.evaluate_job(
            {"price_offer": baseline_price, "required_compute": required_compute},
            {"confidence": prediction["confidence"], "demand": queue_depth, "supply": active_compute_agents},
        )
        fusion = self._fuse_intelligence(prediction, strategy, economic, scout, feature_vector)
        priced = pricing_engine.compute_price(
            compute_units=required_compute,
            predicted_profit=float(economic["profit"]),
            demand=queue_depth,
            agent_availability=active_compute_agents,
            confidence_score=float(fusion["confidence"]),
            predictor_score=float(prediction["score"]),
            strategy_score=float(strategy["score"]),
            scout_score=float(scout["sentiment_score"]),
            expected_value=float(economic["adjusted_expected_value"]),
            idle_capacity=idle_capacity,
            acceptance_rate=success_rate,
            recent_profit_trend=recent_profit_trend,
        )
        price_offer = int(priced["price_offer"])
        economic = economic_engine.evaluate_job(
            {"price_offer": price_offer, "required_compute": required_compute},
            {"confidence": fusion["confidence"], "demand": queue_depth, "supply": active_compute_agents},
        )
        fusion["decision"] = "prioritize" if float(fusion["score"]) > 0.2 and economic["market_pressure"] == "high" else fusion["decision"]
        intelligence = {
            "features": feature_vector.values,
            "prediction": prediction,
            "strategy": strategy,
            "scout": scout,
            "economic": economic,
            "pricing": {
                "baseline_price": baseline_price,
                "price_per_unit": priced["price_per_unit"],
                "reasoning": priced["pricing_reasoning"],
                "market_pressure": priced["market_pressure"],
                "scarcity_ratio": priced["scarcity_ratio"],
                **priced["components"],
            },
            "decision": fusion["decision"],
            "confidence": fusion["confidence"],
            "score": fusion["score"],
            "factors": fusion["factors"],
            "reliability_factor": fusion["reliability_factor"],
            "expected_value": economic["adjusted_expected_value"],
            "price_per_unit": priced["price_per_unit"],
            "market_pressure": priced["market_pressure"],
            "summary": f"Fusion score {fusion['score']:.2f} with {priced['market_pressure']} market pressure.",
        }
        intelligence["explanation"] = explainer.explain_pricing(
            prediction=prediction,
            strategy=strategy,
            scout=scout,
            economic=economic,
            pricing=intelligence["pricing"],
            fusion=fusion,
        )
        self._cache_store(cache_key, price_offer, intelligence)
        return price_offer, intelligence

    async def run(self):
        self.running = True
        logger.info(f"{self.agent_id} ({self.wallet[:10]}...) starting up.")
        self._emit("agent_spawned", {"wallet": self.wallet, "role": "research"})

        interval = float(os.environ.get("ARCOS_RESEARCH_INTERVAL", "3.0"))
        while self.running:
            await asyncio.sleep(random.uniform(interval, interval * 1.5))
            required_compute = random.randint(2, 8)
            description = random.choice(JOB_DESCRIPTIONS)
            price_offer = random.randint(1_200, 8_500)
            intelligence = None

            try:
                price_offer, intelligence = self._build_intelligent_pricing(description, required_compute)
                self.jobs_priced_intelligently += 1
                self._recent_outcomes.append(1.0 if float((intelligence.get("score") or 0.0)) >= 0 else 0.0)
            except Exception as exc:
                logger.debug(f"{self.agent_id} intelligent pricing fallback triggered: {exc}")

            job = {
                "task_id": str(uuid.uuid4())[:8],
                "description": description,
                "required_compute": required_compute,
                "price_offer": price_offer,
                "sender_wallet": self.wallet,
                "creator": self.wallet,
                "sender_key": self.private_key,
            }
            if intelligence:
                job["intelligence"] = intelligence
                job["confidence"] = intelligence.get("confidence")
                job["expected_value"] = intelligence.get("expected_value")
                job["market_pressure"] = intelligence.get("market_pressure")

            self.offer_history.append(price_offer)
            self.workload_history.append(required_compute)
            self.jobs_created += 1
            if intelligence:
                self._log_structured(
                    "research_pricing",
                    {
                        "job_id": job["task_id"],
                        "decision_inputs": {
                            "description": description,
                            "required_compute": required_compute,
                            "queue_depth": len(getattr(self.market, "pending_jobs", [])),
                        },
                        "decision_outputs": {
                            "price_offer": price_offer,
                            "decision": intelligence.get("decision"),
                            "confidence": intelligence.get("confidence"),
                            "market_pressure": intelligence.get("market_pressure"),
                        },
                        "profit_estimation": intelligence.get("economic"),
                    },
                )
            logger.debug(f"{self.agent_id} created job: {job['task_id']}")
            self.market.add_job(job)
            self._emit("job_created", {
                "task_id": job["task_id"],
                "description": job["description"],
                "price_offer": job["price_offer"],
                "sender_wallet": self.wallet,
                "intelligence": intelligence,
                "market_pressure": (intelligence or {}).get("market_pressure"),
            })
