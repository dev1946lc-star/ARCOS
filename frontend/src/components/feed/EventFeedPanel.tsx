"use client";

import { useMemo, useState } from "react";

import Panel from "@/components/panels/Panel";
import type { DashboardEvent } from "@/hooks/useNormalizedEvents";

const FILTERS = [
  { key: "all", label: "All" },
  { key: "signals", label: "Signals" },
  { key: "trades", label: "Trades" },
  { key: "payments", label: "Payments" },
  { key: "alerts", label: "Alerts" },
] as const;

function formatTimestamp(timestamp: number) {
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(timestamp * 1000));
}

export default function EventFeedPanel({
  events,
  connected,
}: {
  events: DashboardEvent[];
  connected: boolean;
}) {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["key"]>("all");

  const filteredEvents = useMemo(() => {
    const list = [...events].reverse();

    switch (filter) {
      case "signals":
        return list.filter((event) => event.category === "signal" || event.category === "agent");
      case "trades":
        return list.filter((event) => event.category === "trade" || event.category === "success");
      case "payments":
        return list.filter((event) => event.category === "payment");
      case "alerts":
        return list.filter((event) => event.category === "warning" || event.category === "error");
      default:
        return list;
    }
  }, [events, filter]);

  return (
    <Panel
      title="Event Feed"
      status={{ label: connected ? "Live" : "Delayed", tone: connected ? "var(--accent-green)" : "var(--accent-red)" }}
      className="h-full"
      contentClassName="min-h-0"
      actions={
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((item) => {
            const active = filter === item.key;

            return (
              <button
                key={item.key}
                onClick={() => setFilter(item.key)}
                className="rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] transition"
                style={{
                  color: active ? "var(--text-primary)" : "var(--text-secondary)",
                  borderColor: active ? "color-mix(in srgb, var(--accent-blue) 42%, transparent)" : "color-mix(in srgb, var(--border-subtle) 85%, transparent)",
                  background: active ? "color-mix(in srgb, var(--accent-blue) 12%, transparent)" : "transparent",
                }}
              >
                {item.label}
              </button>
            );
          })}
        </div>
      }
    >
      <div className="h-full overflow-y-auto p-3">
        <div className="flex flex-col gap-3">
          {filteredEvents.map((event) => (
            <article
              key={event.id}
              className="feed-entry group rounded-2xl border px-4 py-3 transition-all duration-300 hover:shadow-md hover:bg-[color:var(--bg-surface)] hover:-translate-y-[2px]"
              style={{
                background: "color-mix(in srgb, var(--bg-panel) 60%, transparent)",
                borderColor: "color-mix(in srgb, var(--border-subtle) 40%, transparent)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = event.color;
                e.currentTarget.style.boxShadow = `0 4px 16px color-mix(in srgb, ${event.color} 10%, transparent)`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "color-mix(in srgb, var(--border-subtle) 40%, transparent)";
                e.currentTarget.style.boxShadow = "";
              }}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div
                    className="flex h-8 w-8 items-center justify-center rounded-xl text-sm font-semibold transition-transform duration-300 group-hover:scale-110"
                    style={{
                      color: event.color,
                      background: "color-mix(in srgb, var(--bg-surface) 86%, transparent)",
                    }}
                  >
                    {event.icon}
                  </div>
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-[0.16em] transition-colors" style={{ color: event.color }}>
                      {event.title}
                    </div>
                    <p className="mt-1 text-sm text-[var(--text-primary)] opacity-90 transition-opacity group-hover:opacity-100">{event.message}</p>
                  </div>
                </div>
                <div className="shrink-0 text-[11px] font-mono text-[var(--text-secondary)] opacity-80">
                  {formatTimestamp(event.timestamp)}
                </div>
              </div>
            </article>
          ))}

          {filteredEvents.length === 0 ? (
            <div className="rounded-2xl border border-dashed px-4 py-8 text-center text-sm text-[var(--text-secondary)]">
              No matching events yet.
            </div>
          ) : null}
        </div>
      </div>
    </Panel>
  );
}
