import { getApiBase } from "@/lib/runtime-config";

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${getApiBase()}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`);
  return res.json();
}

export async function fetchStats() {
  return fetchJSON<Record<string, unknown>>("/stats");
}

export async function fetchAgents() {
  return fetchJSON<{ agents: Record<string, unknown>[] }>("/agents");
}

export async function fetchAgentsLeaderboard() {
  return fetchJSON<{ leaderboard: Array<Record<string, unknown>> }>("/agents/leaderboard");
}

export async function fetchEvents() {
  return fetchJSON<{ events: Array<Record<string, unknown>> }>("/events");
}

export async function fetchTransactions() {
  return fetchJSON<{ transactions: Array<Record<string, unknown>>; summary: Record<string, unknown> }>("/transactions");
}

export async function fetchEconomicsSummary() {
  return fetchJSON<Record<string, unknown>>("/economics/summary");
}

export async function fetchEconomicsComparison() {
  return fetchJSON<Record<string, unknown>>("/economics/comparison");
}

export async function fetchEconomicsProof() {
  return fetchJSON<Record<string, unknown>>("/economics/proof");
}

export async function fetchSystemHealth() {
  return fetchJSON<Record<string, unknown>>("/system/health");
}

export async function fetchSystemPerformance() {
  return fetchJSON<Record<string, unknown>>("/system/performance");
}

export async function fetchSystemPersistence() {
  return fetchJSON<Record<string, unknown>>("/system/persistence");
}

export async function triggerSpike() {
  return fetchJSON<Record<string, unknown>>("/spike", { method: "POST" });
}

export async function triggerDemoStory() {
  return fetchJSON<Record<string, unknown>>("/demo/story", { method: "POST" });
}
