import asyncio
import logging
import time
from collections import deque
from typing import Any

from core.config import get_int

logger = logging.getLogger("EventBus")

class EventBus:
    """Lightweight pub/sub event bus for ARCOS simulation events."""

    def __init__(self, max_events: int = 5000, subscriber_queue_size: int = 200):
        self._subscribers: list[asyncio.Queue] = []
        self._event_log: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._subscriber_queue_size = max(10, int(subscriber_queue_size))

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._subscriber_queue_size)
        self._subscribers.append(queue)
        logger.info(f"New subscriber connected. Total: {len(self._subscribers)}")
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        if queue in self._subscribers:
            self._subscribers.remove(queue)
        logger.info(f"Subscriber disconnected. Total: {len(self._subscribers)}")

    def publish(self, event_type: str, data: dict[str, Any]):
        event = {
            "type": event_type,
            "timestamp": time.time(),
            "data": data,
        }
        self._event_log.append(event)
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # Drop if consumer is too slow

    def get_recent_events(self, n: int = 50) -> list[dict]:
        return list(self._event_log)[-n:]

    def get_stats(self) -> dict:
        total = len(self._event_log)
        payments = [e for e in self._event_log if e["type"] == "transaction_created"]
        total_volume = sum(e["data"].get("amount", 0) for e in payments)
        return {
            "total_events": total,
            "total_transactions": len(payments),
            "total_volume_micro_usdc": total_volume,
            "subscribers": len(self._subscribers),
        }


# Singleton instance
event_bus = EventBus(
    max_events=get_int("ARCOS_MAX_EVENTS", 5000),
    subscriber_queue_size=get_int("ARCOS_EVENT_SUBSCRIBER_QUEUE_SIZE", 200),
)
