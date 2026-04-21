"use client";

import Panel from "@/components/panels/Panel";
import NetworkGraph from "@/components/graph/NetworkGraph";
import type { AgentInfo } from "@/hooks/useAgentBalances";
import type { ArcosEvent } from "@/hooks/useWebSocket";

export default function NeuralInfrastructurePanel({
  agents,
  events,
}: {
  agents: AgentInfo[];
  events: ArcosEvent[];
}) {
  return (
    <Panel
      title="Neural Infrastructure Graph"
      status={{ label: `${agents.length} Nodes`, tone: "var(--accent-blue)" }}
      className="h-full"
      contentClassName="min-h-0 p-0"
    >
      <NetworkGraph agents={agents} events={events} />
    </Panel>
  );
}
