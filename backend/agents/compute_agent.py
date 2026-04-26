import asyncio
import json
import logging
import math
from collections import deque
from dataclasses import asdict

from agents.agent_brain import agent_brain
from economy.competition_engine import competition_engine
from economy.economic_engine import economic_engine
from intelligence.explainer import explainer
from intelligence.decision_engine import DecisionEngine
from intelligence.risk_agent import RiskAgent

logger = logging.getLogger("ComputeAgent")


class ComputeAgent:
    def __init__(self, wallet, market, market_agent, event_bus=None, agent_id="ComputeAgent", personality_type=None):
        self.wallet = wallet
        self.market = market
        self.market_agent = market_agent
        self.event_bus = event_bus
        self.agent_id = agent_id
        self.running = False
        self.jobs_completed = 0
        self.risk_agent = RiskAgent()
        self.decision_engine = DecisionEngine()
        self.jobs_evaluated = 0
        self.min_decision_score = 0.05
        profile = agent_brain.PERSONALITIES.get(personality_type) if personality_type else agent_brain.select_personality(agent_id)
        self.personality = profile
        self.job_scan_limit = 6
        self.recent_profit = deque(maxlen=10)
        self.recent_decisions = deque(maxlen=20)
        self.metrics = {"decision_count": 0, "started_at": None}
        evolved = agent_brain.evolve_behavior(base_profile=self.personality, recent_profit=0.0, acceptance_rate=0.5)
        self.risk_appetite = float(evolved["risk_appetite"])
        self.profit_trend = float(evolved["profit_trend"])
        self.risk_level = str(evolved["risk_level"])

    def _emit(self, event_type, data):
        if self.event_bus:
            self.event_bus.publish(event_type, {**data, "agent_id": self.agent_id})

    def _log_structured(self, event_name, payload):
        logger.info(json.dumps({"event": event_name, "agent_id": self.agent_id, **payload}, default=str))

    def _decision_rate(self):
        if not self.metrics["started_at"]:
            return 0.0
        elapsed = max(asyncio.get_running_loop().time() - self.metrics["started_at"], 1e-6)
        return round(self.metrics["decision_count"] / elapsed, 4)

    def _acceptance_rate(self):
        if not self.recent_decisions:
            return 0.5
        return sum(1.0 for item in self.recent_decisions if item) / len(self.recent_decisions)

    def _recent_profit_signal(self):
        if not self.recent_profit:
            return 0.0
        return sum(self.recent_profit) / len(self.recent_profit)

    def _refresh_personality_state(self):
        evolved = agent_brain.evolve_behavior(
            base_profile=self.personality,
            recent_profit=self._recent_profit_signal(),
            acceptance_rate=self._acceptance_rate(),
        )
        self.risk_appetite = float(evolved["risk_appetite"])
        self.profit_trend = float(evolved["profit_trend"])
        self.risk_level = str(evolved["risk_level"])

    def _should_accept_job(self, job):
        intelligence = job.get("intelligence") or {}
        prediction = intelligence.get("prediction") or {}
        strategy = intelligence.get("strategy") or {}
        fusion = intelligence
        features = intelligence.get("features") or {}
        scout = intelligence.get("scout") or {}

        predictor_score = float(fusion.get("factors", {}).get("ml", prediction.get("score", 0.0)))
        predictor_confidence = float(prediction.get("confidence_adjusted", prediction.get("confidence", 0.5)))
        queue_pressure = float(features.get("queue_pressure", len(getattr(self.market, "pending_jobs", [])) / 2.0))
        worker_load = float(features.get("workload_ratio", 1.0))
        risk = self.risk_agent.assess(
            price_offer=float(job.get("price_offer", 0.0)),
            required_compute=float(job.get("required_compute", 0.0)),
            predictor_confidence=predictor_confidence,
            queue_pressure=queue_pressure,
            worker_load=worker_load,
        )
        profitability_score = max(-1.0, min(1.0, risk.profit_margin * 2.5))
        blended_confidence = max(
            0.0,
            min(
                1.0,
                float(fusion.get("confidence", 0.0)) * 0.6
                + float(strategy.get("confidence", 0.0)) * 0.2
                + float(scout.get("confidence", 0.0)) * 0.2,
            ),
        )
        economic = economic_engine.evaluate_job(
            job,
            {
                "confidence": blended_confidence,
                "cost": risk.cost_estimate,
                "demand": len(getattr(self.market, "pending_jobs", [])),
                "supply": max(1, self.job_scan_limit),
            },
        )
        decision = self.decision_engine.decide(
            predictor_score=float(fusion.get("score", predictor_score)),
            profitability_score=profitability_score,
            risk_score=float(risk.score),
            technical_signals={
                "momentum_positive": bool(strategy.get("momentum_positive", False)),
                "demand_supportive": bool(strategy.get("demand_supportive", queue_pressure > 0.75)),
                "volatility_high": bool(strategy.get("volatility_high", False)),
                "overloaded": bool(strategy.get("overloaded", worker_load > 1.25)),
            },
        )
        thresholds = agent_brain.evaluate_thresholds(
            self.personality.personality_type,
            base_threshold=self.min_decision_score,
            risk_appetite=self.risk_appetite,
            profit_trend=self.profit_trend,
        )
        competition_pressure = max(0.0, min(1.0, len(getattr(self.market, "pending_jobs", [])) / max(self.job_scan_limit, 1)))
        expected_value_threshold = max(
            250.0,
            float(risk.cost_estimate) * max(0.18, thresholds["min_profit_margin"] + (competition_pressure * 0.05)),
        )
        rejection_reasons = []
        if not economic["profitable"]:
            rejection_reasons.append("unprofitable")
        if float(economic.get("expected_value", 0.0)) <= 0:
            rejection_reasons.append("non_positive_expected_value")
        if float(economic.get("adjusted_expected_value", economic.get("expected_value", 0.0))) < expected_value_threshold:
            rejection_reasons.append("expected_value_below_threshold")
        if float(economic.get("profit_margin", 0.0)) < thresholds["min_profit_margin"]:
            rejection_reasons.append("profit_margin_below_personality_threshold")
        if not risk.approved:
            rejection_reasons.append(risk.reason)
        if float(decision["score"]) < thresholds["decision_threshold"]:
            rejection_reasons.append("decision_score_below_threshold")
        if decision["decision"] == "reject":
            rejection_reasons.append("decision_engine_reject")

        accepted = not rejection_reasons
        behavior = {
            "personality_type": self.personality.personality_type,
            "thresholds": thresholds,
            "competition_pressure": round(competition_pressure, 4),
            "expected_value_threshold": round(expected_value_threshold, 2),
            "explanation": self.personality.explanation,
            "risk_appetite": round(self.risk_appetite, 4),
            "profit_trend": round(self.profit_trend, 4),
            "risk_level": self.risk_level,
        }
        explanation = explainer.explain_decision(
            accepted=accepted,
            economic=economic,
            decision=decision,
            rejection_reasons=rejection_reasons,
            behavior=behavior,
            risk_reason=getattr(risk, "reason", None),
            fusion=fusion,
        )
        return accepted, risk, decision, economic, rejection_reasons, behavior, explanation

    def _job_market_score(self, job):
        price_offer = float(job.get("price_offer", 0.0))
        compute_cost = max(float(job.get("required_compute", 1.0)) * self.risk_agent.cost_per_compute, 1.0)
        expected_value = float((job.get("intelligence") or {}).get("expected_value", job.get("expected_value", price_offer)))
        confidence = float((job.get("intelligence") or {}).get("confidence", job.get("confidence", 0.5)))
        throughput_bonus = agent_brain.evaluate_thresholds(
            self.personality.personality_type,
            base_threshold=self.min_decision_score,
            risk_appetite=self.risk_appetite,
            profit_trend=self.profit_trend,
        )["throughput_bias"]
        return ((expected_value * max(confidence, 0.1)) / compute_cost) * throughput_bonus

    async def _simulate_processing(self, required_compute):
        remaining = max(0.1, float(required_compute) / 10.0)
        while remaining > 0:
            interval = min(0.5, remaining)
            await asyncio.sleep(interval)
            remaining -= interval

    @staticmethod
    def _build_payment_schedule(total_amount, chunks):
        chunk_count = max(1, min(int(chunks), int(total_amount)))
        base = total_amount // chunk_count
        remainder = total_amount % chunk_count
        schedule = []
        for idx in range(chunk_count):
            schedule.append(base + (1 if idx < remainder else 0))
        return [amount for amount in schedule if amount > 0]

    async def run(self):
        self.running = True
        self.metrics["started_at"] = asyncio.get_running_loop().time()
        logger.info(f"{self.agent_id} ({self.wallet[:10]}...) starting up.")
        self._emit("agent_spawned", {"wallet": self.wallet, "role": "compute", "personality_type": self.personality.personality_type})

        while self.running:
            await asyncio.sleep(2)
            self._refresh_personality_state()
            job = self.market.get_best_job(self._job_market_score, limit=self.job_scan_limit)
            if job:
                accepted = True
                risk = None
                decision = None
                economic = None
                rejection_reasons = []
                behavior = {}
                explanation = {}
                try:
                    accepted, risk, decision, economic, rejection_reasons, behavior, explanation = self._should_accept_job(job)
                    self.jobs_evaluated += 1
                    self.metrics["decision_count"] += 1
                except Exception as exc:
                    logger.debug(f"{self.agent_id} decision-layer fallback triggered: {exc}")

                self.recent_decisions.append(bool(accepted))
                self._log_structured(
                    "compute_decision",
                    {
                        "job_id": job.get("task_id"),
                        "decision_inputs": {
                            "price_offer": job.get("price_offer"),
                            "required_compute": job.get("required_compute"),
                            "intelligence": job.get("intelligence"),
                        },
                        "decision_outputs": {
                            "accepted": accepted,
                            "risk": asdict(risk) if risk else None,
                            "decision": decision,
                            "rejection_reasons": rejection_reasons,
                            "behavior": behavior,
                            "explanation": explanation,
                            "decisions_per_second": self._decision_rate(),
                        },
                        "profit_estimation": economic,
                    },
                )
                competition_engine.record_decision(
                    agent_id=self.agent_id,
                    accepted=accepted,
                    personality=self.personality.personality_type,
                    risk_level=self.risk_level,
                )

                if not accepted:
                    logger.info(
                        "%s rejected job %s due to %s (%s)",
                        self.agent_id,
                        job['task_id'],
                        rejection_reasons[0] if rejection_reasons else "policy",
                        self.personality.personality_type,
                    )
                    job.setdefault("decision_log", []).append({
                        "agent_id": self.agent_id,
                        "risk": asdict(risk) if risk else None,
                        "decision": decision,
                        "economic": economic,
                        "rejection_reasons": rejection_reasons,
                        "behavior": behavior,
                        "explanation": explanation,
                    })
                    self.market.pending_jobs.append(job)
                    self._emit("job_rejected", {
                        "task_id": job["task_id"],
                        "description": job["description"],
                        "compute_wallet": self.wallet,
                        "personality_type": self.personality.personality_type,
                        "risk_level": self.risk_level,
                        "reason": rejection_reasons[0] if rejection_reasons else (decision["reasoning"][0] if decision and decision.get("reasoning") else (risk.reason if risk else "fallback")),
                        "rejection_reasons": rejection_reasons,
                        "profit_estimation": economic,
                        "explanation": explanation,
                    })
                    continue

                logger.info(
                    "%s aggressively accepted job %s with %s profile",
                    self.agent_id,
                    job['task_id'],
                    self.personality.personality_type,
                )
                self._emit("job_accepted", {
                    "task_id": job["task_id"],
                    "description": job["description"],
                    "compute_wallet": self.wallet,
                    "personality_type": self.personality.personality_type,
                    "risk_level": self.risk_level,
                    "decision": decision,
                    "risk": asdict(risk) if risk else None,
                    "economic": economic,
                    "explanation": explanation,
                })

                escrow = self.market_agent.lock_escrow(job, self.wallet)
                if escrow.get("status") != "locked":
                    rejection_reasons = [escrow.get("reason", "escrow_lock_failed")]
                    job.setdefault("decision_log", []).append({
                        "agent_id": self.agent_id,
                        "decision": decision,
                        "economic": economic,
                        "rejection_reasons": rejection_reasons,
                    })
                    self.market.pending_jobs.append(job)
                    self._emit("job_rejected", {
                        "task_id": job["task_id"],
                        "description": job["description"],
                        "compute_wallet": self.wallet,
                        "reason": rejection_reasons[0],
                        "rejection_reasons": rejection_reasons,
                        "profit_estimation": economic,
                    })
                    continue

                try:
                    dynamic_throughput_bias = agent_brain.evaluate_thresholds(
                        self.personality.personality_type,
                        base_threshold=self.min_decision_score,
                        risk_appetite=self.risk_appetite,
                        profit_trend=self.profit_trend,
                    )["throughput_bias"]
                    target_chunks = max(5, min(20, math.ceil(float(job["required_compute"]) * dynamic_throughput_bias * 1.6)))
                    payment_schedule = self._build_payment_schedule(int(job["price_offer"]), target_chunks)
                    total_chunks = len(payment_schedule)
                    for chunk_index, release_amount in enumerate(payment_schedule, start=1):
                        await self._simulate_processing(max(0.25, float(job["required_compute"]) / max(total_chunks, 1)))
                        chunk_tx = self.market_agent.release_partial_payment(
                            job,
                            chunk_index=chunk_index,
                            total_chunks=total_chunks,
                            amount=release_amount,
                        )
                        if chunk_tx.get("status") == "success":
                            self._emit("agent_payment", {
                                "task_id": job["task_id"],
                                "action": "payment",
                                "amount": release_amount,
                                "chunk": f"{chunk_index}/{total_chunks}",
                                "tx_hash": chunk_tx.get("tx_hash"),
                            })
                            logger.debug(f"{self.agent_id} released payment chunk {chunk_index}/{total_chunks}: {release_amount} microUSDC")
                        else:
                            raise ValueError(chunk_tx.get("reason", "partial_release_failed"))

                    result_payload = f"Result for: {job['description']}"
                    if economic:
                        job["economic"] = economic
                    job["execution"] = {
                        "compute_wallet": self.wallet,
                        "decision": decision,
                        "risk": asdict(risk) if risk else None,
                        "explanation": explanation,
                    }
                    job["compute_wallet"] = self.wallet
                    job["explanation"] = explanation
                    self.market.complete_job(job, result_payload)
                    self.jobs_completed += 1
                    if risk:
                        self.risk_agent.circuit_breaker.record_outcome(bool(economic and economic.get("profitable")))
                    if economic:
                        self.recent_profit.append(float(economic.get("profit", 0.0)))
                        competition_engine.record_job(
                            agent_id=self.agent_id,
                            profit=float(economic.get("profit", 0.0)),
                            revenue=float(economic.get("revenue", 0.0)),
                            cost=float(economic.get("cost", 0.0)),
                            personality=self.personality.personality_type,
                            risk_level=self.risk_level,
                            risk_appetite=self.risk_appetite,
                            profit_trend=self.profit_trend,
                        )
                    logger.info(f"{self.agent_id} completed job: {job['task_id']}")
                    self.market.complete_job(job, "success")
                    self._emit("job_completed", {
                        "task_id": job["task_id"],
                        "description": job["description"],
                        "compute_wallet": self.wallet,
                        "personality_type": self.personality.personality_type,
                        "risk_level": self.risk_level,
                        "decision": decision,
                        "economic": economic,
                        "explanation": explanation,
                    })
                except Exception as exc:
                    self.market_agent.refund_escrow(job, reason="processing_failed")
                    logger.warning("%s failed processing job %s: %s", self.agent_id, job.get("task_id"), exc)
                    self.recent_profit.append(-max(float(job.get("price_offer", 0.0)) * 0.1, 50.0))
                    self._emit("job_failed", {
                        "task_id": job.get("task_id"),
                        "description": job.get("description"),
                        "compute_wallet": self.wallet,
                        "personality_type": self.personality.personality_type,
                        "risk_level": self.risk_level,
                        "reason": "processing_failed",
                    })
