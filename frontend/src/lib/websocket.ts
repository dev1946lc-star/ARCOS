type EventHandler = (event: Record<string, unknown>) => void;

import { getWebSocketUrl } from "@/lib/runtime-config";

export function connectWebSocket(onEvent: EventHandler) {
  let ws: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let alive = true;

  function connect() {
    if (!alive) return;

    try {
      ws = new WebSocket(getWebSocketUrl());

      ws.onopen = () => {
        console.log("[ARCOS WS] Connected");
      };

      ws.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data);
          onEvent(data);
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        console.log("[ARCOS WS] Disconnected, reconnecting in 3s...");
        scheduleReconnect();
      };

      ws.onerror = () => {
        ws?.close();
      };
    } catch {
      scheduleReconnect();
    }
  }

  function scheduleReconnect() {
    if (!alive) return;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(connect, 3000);
  }

  connect();

  return {
    disconnect() {
      alive = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
      ws = null;
    },
  };
}
