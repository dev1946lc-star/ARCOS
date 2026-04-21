"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface ArcosEvent {
  type: string;
  timestamp: number;
  data: Record<string, unknown>;
}

const API_BASE = "http://localhost:8000";
const WS_URL = "ws://localhost:8000/ws";
const RECONNECT_DELAY = 3000;
const FLUSH_INTERVAL = 500;
const MAX_EVENTS = 240;

export function useWebSocket() {
  const [events, setEvents] = useState<ArcosEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const bufferRef = useRef<ArcosEvent[]>([]);

  const flushBufferedEvents = useCallback(() => {
    if (bufferRef.current.length === 0) return;

    const nextBatch = bufferRef.current;
    bufferRef.current = [];

    setEvents((current) => [...current, ...nextBatch].slice(-MAX_EVENTS));
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = (message) => {
      try {
        const event = JSON.parse(message.data) as ArcosEvent;
        bufferRef.current.push(event);
      } catch {
        // Ignore malformed messages.
      }
    };

    ws.onclose = () => {
      setConnected(false);
      reconnectTimeoutRef.current = setTimeout(connect, RECONNECT_DELAY);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const response = await fetch(`${API_BASE}/events`);
        if (!response.ok) return;

        const data = await response.json();
        if (Array.isArray(data.events)) {
          setEvents(data.events.slice(-MAX_EVENTS));
        }
      } catch {
        // Backend may still be starting.
      }
    };

    loadHistory();
    connect();

    const flushIntervalId = window.setInterval(flushBufferedEvents, FLUSH_INTERVAL);

    return () => {
      window.clearInterval(flushIntervalId);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      wsRef.current?.close();
    };
  }, [connect, flushBufferedEvents]);

  return { events, connected };
}
