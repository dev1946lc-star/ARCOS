"use client";

import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE = "http://localhost:8000";
const STATS_POLL_INTERVAL = 3000;
const HIGHLIGHT_DURATION = 900;

export interface SystemStats {
  total_events: number;
  total_transactions: number;
  total_volume: number;
  active_agents: number;
  pending_jobs: number;
  completed_jobs: number;
  subscribers?: number;
}

export interface MetricItem {
  key: string;
  label: string;
  value: string;
  tone: string;
  changed: boolean;
}

function formatWei(wei: number): string {
  if (wei >= 1e15) return `${(wei / 1e18).toFixed(4)} ETH`;
  if (wei >= 1e12) return `${(wei / 1e12).toFixed(1)}T WEI`;
  if (wei >= 1e9) return `${(wei / 1e9).toFixed(1)}G WEI`;
  return `${wei} WEI`;
}

function formatUptime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m ${String(seconds % 60).padStart(2, "0")}s`;
}

export function useSystemStats() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [uptime, setUptime] = useState(0);
  const [changedKeys, setChangedKeys] = useState<string[]>([]);
  const prevRef = useRef<SystemStats | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch(`${API_BASE}/stats`);
        if (!res.ok) return;
        const next = (await res.json()) as SystemStats;

        if (prevRef.current) {
          const changed = Object.keys(next).filter((key) => {
            const typedKey = key as keyof SystemStats;
            return prevRef.current?.[typedKey] !== next[typedKey];
          });

          if (changed.length > 0) {
            setChangedKeys(changed);
            window.setTimeout(() => setChangedKeys([]), HIGHLIGHT_DURATION);
          }
        }

        prevRef.current = next;
        setStats(next);
      } catch {
        // Backend may not be available yet.
      }
    };

    fetchStats();
    const intervalId = window.setInterval(fetchStats, STATS_POLL_INTERVAL);
    return () => window.clearInterval(intervalId);
  }, []);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      setUptime((current) => current + 1);
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, []);

  const metrics = useMemo<MetricItem[]>(() => {
    return [
      {
        key: "total_transactions",
        label: "Transactions",
        value: String(stats?.total_transactions ?? 0),
        tone: "var(--accent-blue)",
        changed: changedKeys.includes("total_transactions"),
      },
      {
        key: "total_volume",
        label: "Volume",
        value: formatWei(stats?.total_volume ?? 0),
        tone: "var(--accent-green)",
        changed: changedKeys.includes("total_volume"),
      },
      {
        key: "active_agents",
        label: "Active Agents",
        value: String(stats?.active_agents ?? 0),
        tone: "var(--accent-violet)",
        changed: changedKeys.includes("active_agents"),
      },
      {
        key: "pending_jobs",
        label: "Pending Jobs",
        value: String(stats?.pending_jobs ?? 0),
        tone: "var(--accent-orange)",
        changed: changedKeys.includes("pending_jobs"),
      },
      {
        key: "completed_jobs",
        label: "Completed Jobs",
        value: String(stats?.completed_jobs ?? 0),
        tone: "var(--accent-cyan)",
        changed: changedKeys.includes("completed_jobs"),
      },
      {
        key: "uptime",
        label: "Uptime",
        value: formatUptime(uptime),
        tone: "var(--text-primary)",
        changed: false,
      },
    ];
  }, [changedKeys, stats, uptime]);

  return { stats, metrics };
}
