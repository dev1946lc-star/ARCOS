"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import AgentNetworkPanel from "@/components/agents/AgentNetworkPanel";
import EventFeedPanel from "@/components/feed/EventFeedPanel";
import NeuralInfrastructurePanel from "@/components/graph/NeuralInfrastructurePanel";
import DashboardHeader from "@/components/layout/DashboardHeader";
import MetricsBar from "@/components/metrics/MetricsBar";
import EconomicsProofBanner from "@/components/metrics/EconomicsProofBanner";
import SystemProofPanel from "@/components/metrics/SystemProofPanel";
import { useAgentBalances } from "@/hooks/useAgentBalances";
import { useNormalizedEvents } from "@/hooks/useNormalizedEvents";
import { useSpeechNarration } from "@/hooks/useSpeechNarration";
import { useSystemStats } from "@/hooks/useSystemStats";
import { useSystemProof } from "@/hooks/useSystemProof";
import { useWebSocket } from "@/hooks/useWebSocket";

const API_BASE = "http://localhost:8000";
const SPIKE_COOLDOWN_SECONDS = 3;

export default function Home() {
  const agents = useAgentBalances();
  const { events, connected } = useWebSocket();
  const normalizedEvents = useNormalizedEvents(events);
  const { metrics } = useSystemStats();
  const proof = useSystemProof();
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [cooldownRemaining, setCooldownRemaining] = useState(0);
  const spikeLockRef = useRef(false);
  const cooldownIntervalRef = useRef<number | null>(null);

  useSpeechNarration(voiceEnabled, normalizedEvents);

  const clearCooldown = useCallback(() => {
    if (cooldownIntervalRef.current) {
      window.clearInterval(cooldownIntervalRef.current);
      cooldownIntervalRef.current = null;
    }
  }, []);

  useEffect(() => clearCooldown, [clearCooldown]);

  const triggerSpike = useCallback(async () => {
    if (spikeLockRef.current || cooldownRemaining > 0) return;

    spikeLockRef.current = true;
    setCooldownRemaining(SPIKE_COOLDOWN_SECONDS);

    clearCooldown();
    cooldownIntervalRef.current = window.setInterval(() => {
      setCooldownRemaining((current) => {
        if (current <= 1) {
          spikeLockRef.current = false;
          if (cooldownIntervalRef.current) {
            window.clearInterval(cooldownIntervalRef.current);
            cooldownIntervalRef.current = null;
          }
          return 0;
        }

        return current - 1;
      });
    }, 1000);

    try {
      await fetch(`${API_BASE}/spike`, { method: "POST" });
    } catch {
      // Keep the cooldown even if the request fails so repeated clicks do not flood retries.
    }
  }, [clearCooldown, cooldownRemaining]);

  return (
    <main className="dashboard-shell">
      <div className="app-frame">
        <DashboardHeader
          connected={connected}
          voiceEnabled={voiceEnabled}
          cooldownRemaining={cooldownRemaining}
          onToggleVoice={() => setVoiceEnabled((current) => !current)}
          onTriggerSpike={triggerSpike}
          proof={proof}
        />

        <EconomicsProofBanner />
        <SystemProofPanel proof={proof} />
        <MetricsBar metrics={metrics} />

        <section className="grid h-[calc(100vh-420px)] min-h-[500px] gap-4 xl:grid-cols-[300px_minmax(0,1.55fr)_380px]">
          <div className="flex flex-col min-w-0 min-h-[340px] xl:min-h-0 h-full">
            <AgentNetworkPanel agents={agents} events={events} />
          </div>

          <div className="flex flex-col min-w-0 min-h-[480px] xl:min-h-0 h-full">
            <NeuralInfrastructurePanel agents={agents} events={events} />
          </div>

          <div className="flex flex-col min-w-0 min-h-[340px] xl:min-h-0 h-full">
            <EventFeedPanel events={normalizedEvents} connected={connected} />
          </div>
        </section>
      </div>
    </main>
  );
}
