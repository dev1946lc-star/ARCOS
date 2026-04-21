"use client";

import { useMemo } from "react";

import Panel from "@/components/panels/Panel";
import type { ArcosEvent } from "@/hooks/useWebSocket";
import type { AgentInfo } from "@/hooks/useAgentBalances";

function formatWei(wei: number): string {
  if (wei >= 1e15) return `${(wei / 1e18).toFixed(4)} ETH`;
  if (wei >= 1e12) return `${(wei / 1e12).toFixed(1)}T WEI`;
  if (wei >= 1e9) return `${(wei / 1e9).toFixed(1)}G WEI`;
  return `${wei} WEI`;
}

function getStatusTone(status: "online" | "busy" | "offline") {
  switch (status) {
    case "busy":
      return "var(--accent-orange)";
    case "offline":
      return "var(--accent-red)";
    default:
      return "var(--accent-green)";
  }
}

export default function AgentNetworkPanel({
  agents,
  events,
}: {
  agents: AgentInfo[];
  events: ArcosEvent[];
}) {
  const statusMap = useMemo(() => {
    const next = new Map<string, "online" | "busy" | "offline">();

    agents.forEach((agent) => next.set(agent.agent_id, "online"));

    events.forEach((event) => {
      const agentId = event.data.agent_id as string | undefined;
      if (!agentId) return;

      if (event.type === "job_accepted") next.set(agentId, "busy");
      if (event.type === "job_completed" || event.type === "agent_spawned") next.set(agentId, "online");
    });

    return next;
  }, [agents, events]);

  return (
    <Panel
      title="Agent Network"
      status={{ label: `${agents.length} Active`, tone: "var(--accent-violet)" }}
      contentClassName="overflow-y-auto p-3"
      className="h-full"
    >
      <div className="flex flex-col gap-3">
        {agents.map((agent) => {
          const status = statusMap.get(agent.agent_id) ?? "offline";
          const tone = agent.role === "research" ? "var(--accent-violet)" : "var(--accent-cyan)";

          return (
            <article
              key={agent.agent_id}
              className="group rounded-2xl border p-4 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:bg-[color:var(--bg-surface)]"
              style={{
                background: "color-mix(in srgb, var(--bg-panel) 60%, transparent)",
                borderColor: "color-mix(in srgb, var(--border-subtle) 40%, transparent)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = tone;
                e.currentTarget.style.boxShadow = `0 8px 24px color-mix(in srgb, ${tone} 15%, transparent)`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "color-mix(in srgb, var(--border-subtle) 40%, transparent)";
                e.currentTarget.style.boxShadow = "";
              }}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-[var(--text-primary)] transition-colors group-hover:text-white">
                    {agent.agent_id}
                  </div>
                  <div className="mt-1 text-[11px] uppercase tracking-[0.14em]" style={{ color: tone }}>
                    {agent.role}
                  </div>
                </div>

                <span
                  className="inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.16em] transition-all"
                  style={{
                    color: getStatusTone(status),
                    borderColor: "color-mix(in srgb, var(--border-subtle) 82%, transparent)",
                  }}
                >
                  <span
                    className="relative flex h-2 w-2"
                  >
                    <span 
                       className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${status === 'busy' ? 'animate-ping' : ''}`}
                       style={{ background: getStatusTone(status) }}
                    />
                    <span className="relative inline-flex h-2 w-2 rounded-full" style={{ background: getStatusTone(status) }} />
                  </span>
                  {status}
                </span>
              </div>

              <div className="mt-4 text-xs text-[var(--text-secondary)]">
                Wallet
              </div>
              <div className="mt-1 truncate font-mono text-xs text-[var(--text-primary)] opacity-80 transition-opacity group-hover:opacity-100">
                {agent.wallet}
              </div>

              <div className="mt-4 text-xs text-[var(--text-secondary)]">
                Balance
              </div>
              <div className="mt-1 text-sm font-semibold text-[var(--text-primary)]">
                {formatWei(agent.balance)}
              </div>
            </article>
          );
        })}

        {agents.length === 0 ? (
          <div className="rounded-2xl border border-dashed px-4 py-8 text-center text-sm text-[var(--text-secondary)]">
            Waiting for agents to come online.
          </div>
        ) : null}
      </div>
    </Panel>
  );
}
