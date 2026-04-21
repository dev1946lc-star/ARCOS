"use client";

import { useEffect, useState, useCallback } from "react";

const API_BASE = "http://localhost:8000";

export interface SystemProofData {
  // Stress
  stressLevel: "NORMAL" | "HIGH LOAD" | "BACKPRESSURE ACTIVE";
  stressColor: string;

  // Persistence
  dropRate: number;
  successRate: number;
  queueHealth: string;
  backpressureActive: boolean;

  // Performance
  txPerSecond: number;
  peakTxPerSecond: number;
  avgLatency: number;
  persistenceThroughput: number;
}

const DEFAULT_STATE: SystemProofData = {
  stressLevel: "NORMAL",
  stressColor: "var(--accent-green)",
  dropRate: 0,
  successRate: 1,
  queueHealth: "healthy",
  backpressureActive: false,
  txPerSecond: 0,
  peakTxPerSecond: 0,
  avgLatency: 0,
  persistenceThroughput: 0,
};

function deriveStress(
  queueHealth: string,
  backpressure: boolean,
  tps: number
): Pick<SystemProofData, "stressLevel" | "stressColor"> {
  if (backpressure || queueHealth === "critical") {
    return { stressLevel: "BACKPRESSURE ACTIVE", stressColor: "var(--accent-red)" };
  }
  if (queueHealth === "saturated" || tps > 25) {
    return { stressLevel: "HIGH LOAD", stressColor: "var(--accent-orange)" };
  }
  return { stressLevel: "NORMAL", stressColor: "var(--accent-green)" };
}

export function useSystemProof() {
  const [data, setData] = useState<SystemProofData>(DEFAULT_STATE);

  const refresh = useCallback(async () => {
    try {
      const [persRes, perfRes] = await Promise.all([
        fetch(`${API_BASE}/system/persistence`),
        fetch(`${API_BASE}/system/performance`),
      ]);
      if (!persRes.ok || !perfRes.ok) return;

      const pers = await persRes.json();
      const perf = await perfRes.json();

      const queueHealth = String(pers.queue_health ?? "healthy");
      const backpressure = Boolean(pers.backpressure_active);
      const tps = Number(perf.tx_per_second ?? 0);

      const stress = deriveStress(queueHealth, backpressure, tps);

      setData({
        ...stress,
        dropRate: Number(pers.drop_rate ?? 0),
        successRate: Number(pers.success_rate ?? 1),
        queueHealth,
        backpressureActive: backpressure,
        txPerSecond: tps,
        peakTxPerSecond: Number(perf.peak_throughput_observed ?? 0),
        avgLatency: Number(perf.avg_settlement_time ?? 0),
        persistenceThroughput: Number(perf.persistence_throughput ?? 0),
      });
    } catch {
      // Backend may not be available
    }
  }, []);

  useEffect(() => {
    refresh();
    const iv = setInterval(refresh, 2000);
    return () => clearInterval(iv);
  }, [refresh]);

  return data;
}
