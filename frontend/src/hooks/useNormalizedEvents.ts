"use client";

import { useMemo } from "react";

import type { ArcosEvent } from "@/hooks/useWebSocket";

export type DashboardEventType =
  | "SIGNAL_GENERATED"
  | "SIGNAL_VALIDATED"
  | "SIGNAL_PURCHASED"
  | "TRADE_EXECUTED"
  | "AGENT_ONLINE"
  | "PAYMENT_SETTLED"
  | "SYSTEM_ALERT"
  | "NETWORK_SPIKE";

export type DashboardEventCategory =
  | "agent"
  | "signal"
  | "payment"
  | "trade"
  | "success"
  | "warning"
  | "error";

export interface DashboardEvent {
  id: string;
  type: DashboardEventType;
  category: DashboardEventCategory;
  icon: string;
  color: string;
  timestamp: number;
  title: string;
  message: string;
  speakable: boolean;
  rawType: string;
}

function getEventId(event: ArcosEvent) {
  const taskId = typeof event.data.task_id === "string" ? event.data.task_id : "";
  const agentId = typeof event.data.agent_id === "string" ? event.data.agent_id : "";
  const wallet = typeof event.data.wallet === "string" ? event.data.wallet : "";
  return `${event.timestamp}-${event.type}-${taskId}-${agentId}-${wallet}`;
}

/** Infer a confidence string from event data when available */
function confidenceTag(event: ArcosEvent): string {
  const conf = event.data.confidence ?? (event.data.intelligence as Record<string, unknown> | undefined)?.confidence;
  if (typeof conf === "number") return ` (confidence ${conf.toFixed(2)})`;
  return "";
}

function formatMicroUSD(amount: unknown): string {
  const n = typeof amount === "number" ? amount : 0;
  if (n === 0) return "";
  const usdc = n / 1_000_000;
  if (usdc < 0.01) return ` for ${(usdc * 1000).toFixed(3)} mUSDC`;
  return ` for ${usdc.toFixed(4)} USDC`;
}

function normalizeEvent(event: ArcosEvent): DashboardEvent | null {
  const agentId = (event.data.agent_id as string | undefined) ?? "Agent";
  const description = (event.data.description as string | undefined) ?? "signal";
  const insightMessage = (event.data.message as string | undefined) ?? "System insight generated";

  switch (event.type) {
    case "agent_spawned":
      return {
        id: getEventId(event),
        type: "AGENT_ONLINE",
        category: "agent",
        icon: "◈",
        color: "var(--accent-violet)",
        timestamp: event.timestamp,
        title: "Agent Online",
        message: `${agentId} joined the trading swarm`,
        speakable: true,
        rawType: event.type,
      };

    case "job_created":
      return {
        id: getEventId(event),
        type: "SIGNAL_GENERATED",
        category: "signal",
        icon: "⚡",
        color: "var(--accent-cyan)",
        timestamp: event.timestamp,
        title: "Signal Generated",
        message: `${description}${confidenceTag(event)}`,
        speakable: false,
        rawType: event.type,
      };

    case "job_accepted":
      return {
        id: getEventId(event),
        type: "SIGNAL_VALIDATED",
        category: "signal",
        icon: "↗",
        color: "var(--accent-blue)",
        timestamp: event.timestamp,
        title: "Signal Acquired",
        message: `${agentId} validating ${description.toLowerCase()}`,
        speakable: false,
        rawType: event.type,
      };

    case "job_completed": {
      const economic = event.data.economic as Record<string, unknown> | undefined;
      const profit = typeof economic?.profit === "number" ? economic.profit : null;
      const profitStr = profit !== null ? ` | profit ${profit > 0 ? "+" : ""}${profit.toFixed(0)}` : "";
      return {
        id: getEventId(event),
        type: "TRADE_EXECUTED",
        category: "trade",
        icon: "✓",
        color: "var(--accent-green)",
        timestamp: event.timestamp,
        title: "Trade Executed",
        message: `${description} settled by ${agentId}${profitStr}`,
        speakable: true,
        rawType: event.type,
      };
    }

    case "payment_sent":
      return {
        id: getEventId(event),
        type: "PAYMENT_SETTLED",
        category: "payment",
        icon: "$",
        color: "var(--accent-green)",
        timestamp: event.timestamp,
        title: "Payment Settled",
        message: `Nanopayment stream${formatMicroUSD(event.data.amount)}`,
        speakable: false,
        rawType: event.type,
      };

    case "job_rejected":
      return {
        id: getEventId(event),
        type: "SIGNAL_GENERATED",
        category: "warning",
        icon: "✕",
        color: "var(--accent-orange)",
        timestamp: event.timestamp,
        title: "Signal Rejected",
        message: `${agentId} rejected ${description.toLowerCase()} — ${(event.data.reason as string) ?? "risk threshold"}`,
        speakable: false,
        rawType: event.type,
      };

    case "insight": {
      const looksLikeSpike =
        insightMessage.toLowerCase().includes("throughput increased") ||
        insightMessage.toLowerCase().includes("network load increased");

      return {
        id: getEventId(event),
        type: looksLikeSpike ? "NETWORK_SPIKE" : "SYSTEM_ALERT",
        category: looksLikeSpike ? "warning" : "error",
        icon: looksLikeSpike ? "▲" : "!",
        color: looksLikeSpike ? "var(--accent-orange)" : "var(--accent-red)",
        timestamp: event.timestamp,
        title: looksLikeSpike ? "Network Spike" : "System Alert",
        message: looksLikeSpike
          ? insightMessage.replace(/^System alert:\s*/i, "")
          : insightMessage,
        speakable: !looksLikeSpike,
        rawType: event.type,
      };
    }

    default:
      return null;
  }
}

export function useNormalizedEvents(events: ArcosEvent[]) {
  return useMemo(() => {
    const normalized = events
      .map(normalizeEvent)
      .filter((event): event is DashboardEvent => event !== null);

    // Ensure every event has a unique id (duplicate raw events can produce
    // the same base id, which causes React "duplicate key" warnings).
    const seen = new Map<string, number>();
    for (const event of normalized) {
      const count = seen.get(event.id) ?? 0;
      if (count > 0) {
        event.id = `${event.id}_${count}`;
      }
      seen.set(event.id.replace(/_\d+$/, ""), count + 1);
    }

    return normalized.slice(-120);
  }, [events]);
}
