import logging
import time
from typing import Dict, List

logger = logging.getLogger("InsightEngine")

class InsightState:
    def __init__(self):
        self.jobs_completed = 0
        self.total_agents = 3 # Simulation starts with 3
        self.last_check_time = time.time()
        self.completed_in_window = 0
        self.throughput_history: List[float] = []
        self.recent_prices: List[float] = []
        self.recent_profits: List[float] = []

    def update_throughput(self):
        now = time.time()
        elapsed = now - self.last_check_time
        if elapsed >= 10: # Every 10 seconds
            throughput = self.completed_in_window / elapsed
            self.throughput_history.append(throughput)
            self.completed_in_window = 0
            self.last_check_time = now
            return throughput
        return None

state = InsightState()

last_insight_times: Dict[str, float] = {}

COOLDOWN = {
    "job_created": 6.0,
    "job_completed": 5.0,
    "payment_sent": 8.0,
    "transaction_created": 4.0,
    "agent_spawned": 10.0,
    "throughput_spike": 10.0,
    "scarcity_pricing": 8.0,
    "competition_pressure": 8.0,
}

def can_emit(category: str) -> bool:
    now = time.time()
    last = last_insight_times.get(category, 0.0)
    if now - last >= COOLDOWN.get(category, 5.0):
        last_insight_times[category] = now
        return True
    return False


def generate_insight(event_type: str, data: dict) -> str | None:
    """
    Translates raw simulation events into human-readable narrative insights.
    Uses basic state tracking to provide analytical context.
    """
    global state

    if event_type == "agent_spawned":
        state.total_agents += 1
        if can_emit(event_type):
            agent_id = data.get("agent_id", "New Agent")
            role = data.get("role", "worker")
            return f"Compute demand increased. Spawning additional {role} agent '{agent_id}' to stabilize network latency."

    if event_type == "job_created":
        price_offer = float(data.get("price_offer", 0))
        if price_offer > 0:
            state.recent_prices.append(price_offer)
            state.recent_prices = state.recent_prices[-20:]
        if can_emit(event_type):
            desc = data.get("description", "task")
            return "Research workload increasing. New autonomous compute tasks entering the ARCOS network."
        if len(state.recent_prices) >= 5:
            avg_price = sum(state.recent_prices[:-1]) / max(len(state.recent_prices) - 1, 1)
            if avg_price > 0 and price_offer > avg_price * 1.2 and can_emit("scarcity_pricing"):
                return "Market demand surge detected. Agents are increasing price due to compute scarcity."

    if event_type in {"payment_sent", "transaction_created"}:
        if can_emit(event_type):
            amount_micro = float(data.get("amount", 0))
            usd_val = amount_micro / 1_000_000
            chunk_index = data.get("chunk_index")
            if chunk_index:
                return f"Streaming micropayment released. Chunk {chunk_index}/{data.get('total_chunks', '?')} settled for ${usd_val:.6f}."
            return f"Autonomous commerce executed. ${usd_val:.6f} settled between machine agents."

    if event_type == "job_completed":
        state.jobs_completed += 1
        state.completed_in_window += 1
        profit = float((data.get("economic") or {}).get("profit", 0.0))
        state.recent_profits.append(profit)
        state.recent_profits = state.recent_profits[-20:]
        if can_emit(event_type):
            agent_id = data.get("agent_id", "Agent")
            return f"Compute agent {agent_id} completed task and received on-chain payment."
        if len(state.recent_profits) >= 5:
            avg_profit = sum(state.recent_profits) / len(state.recent_profits)
            if avg_profit < 800 and can_emit("competition_pressure"):
                return "High competition is reducing profit margins as agents race to secure work."

    # Periodically check for throughput spikes
    tp = state.update_throughput()
    if tp is not None and len(state.throughput_history) > 1:
        prev_tp = state.throughput_history[-2]
        if prev_tp > 0 and tp > prev_tp * 1.3:
            if can_emit("throughput_spike"):
                return f"System alert: Economic throughput increased by {((tp/prev_tp)-1)*100:.0f}%. Network efficiency is optimal."

    return None

async def start_insight_manager(event_bus):
    """
    Monitors the event bus and publishes narrative insights for the frontend.
    """
    logger.info("[ARCOS] Insight Engine active. Synchronizing telemetry with narrative.")
    queue = event_bus.subscribe()
    
    try:
        while True:
            event = await queue.get()
            event_type = event.get("type")
            data = event.get("data", {})
            
            # Avoid infinite loops by not processing our own insights
            if event_type == "insight":
                continue
                
            insight_msg = generate_insight(event_type, data)
            if insight_msg:
                # Publish the insight back to the bus
                event_bus.publish("insight", {
                    "message": insight_msg,
                    "original_type": event_type
                })
            
            # Small yield to allow other tasks
            await asyncio.sleep(0.01)
    finally:
        event_bus.unsubscribe(queue)

import asyncio
