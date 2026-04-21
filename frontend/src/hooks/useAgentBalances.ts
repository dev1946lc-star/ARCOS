"use client";

import { useEffect, useState, useCallback } from "react";

const API_BASE = "http://localhost:8000";
const POLL_INTERVAL = 4000;

export interface AgentInfo {
  agent_id: string;
  wallet: string;
  role: string;
  balance: number;
}

export function useAgentBalances() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/agents`);
      const data = await res.json();
      const agentsRaw = data.agents || {};
      const agentList: AgentInfo[] = Array.isArray(agentsRaw) 
        ? agentsRaw 
        : Object.values(agentsRaw);

      // Fetch balances in parallel
      const withBalances = await Promise.all(
        agentList.map(async (a) => {
          if (!a?.wallet) return { ...a, balance: 0 };
          try {
            const bRes = await fetch(`${API_BASE}/balance/${a.wallet}`);
            const bData = await bRes.json();
            return { ...a, balance: bData.balance ?? 0 };
          } catch {
            return { ...a, balance: 0 };
          }
        })
      );

      setAgents(withBalances);
    } catch {
      // backend may not be up yet
    }
  }, []);

  useEffect(() => {
    refresh();
    const iv = setInterval(refresh, POLL_INTERVAL);
    return () => clearInterval(iv);
  }, [refresh]);

  return agents;
}
