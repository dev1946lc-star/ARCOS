"use client";

import type { SystemProofData } from "@/hooks/useSystemProof";

function Stat({
  label,
  value,
  tone,
  suffix = "",
}: {
  label: string;
  value: string;
  tone?: string;
  suffix?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-[0.16em] text-[var(--text-secondary)]">
        {label}
      </span>
      <span
        className="font-mono text-sm font-bold transition-colors duration-300"
        style={{ color: tone ?? "var(--text-primary)" }}
      >
        {value}
        {suffix && (
          <span className="ml-1 text-[10px] font-normal text-[var(--text-secondary)]">
            {suffix}
          </span>
        )}
      </span>
    </div>
  );
}

function StressChip({ level, color }: { level: string; color: string }) {
  const isBackpressure = level === "BACKPRESSURE ACTIVE";
  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.18em] transition-all duration-300 ${isBackpressure ? "animate-pulse" : ""}`}
      style={{
        color,
        borderColor: `color-mix(in srgb, ${color} 40%, transparent)`,
        background: `color-mix(in srgb, ${color} 8%, transparent)`,
        boxShadow: isBackpressure ? `0 0 18px color-mix(in srgb, ${color} 25%, transparent)` : "none",
      }}
    >
      <span className="relative flex h-2 w-2">
        {isBackpressure && (
          <span
            className="absolute inline-flex h-full w-full rounded-full animate-ping opacity-75"
            style={{ background: color }}
          />
        )}
        <span
          className="relative inline-flex h-2 w-2 rounded-full"
          style={{ background: color }}
        />
      </span>
      {level}
    </div>
  );
}

export default function SystemProofPanel({ proof }: { proof: SystemProofData }) {
  return (
    <div className="panel-surface panel-muted flex flex-col">
      <header className="flex items-center justify-between gap-3 border-b px-5 py-4">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold tracking-[0.16em] text-[var(--text-secondary)] uppercase">
            System Proof
          </h2>
          <StressChip level={proof.stressLevel} color={proof.stressColor} />
        </div>
      </header>

      <div className="grid grid-cols-2 gap-x-6 gap-y-4 px-5 py-4 sm:grid-cols-4">
        <Stat
          label="TX / SEC"
          value={proof.txPerSecond.toFixed(1)}
          tone="var(--accent-cyan)"
          suffix="tps"
        />
        <Stat
          label="PEAK TPS"
          value={proof.peakTxPerSecond.toFixed(1)}
          tone="var(--accent-blue)"
          suffix="tps"
        />
        <Stat
          label="DROP RATE"
          value={`${(proof.dropRate * 100).toFixed(1)}%`}
          tone={proof.dropRate > 0.15 ? "var(--accent-red)" : "var(--accent-green)"}
        />
        <Stat
          label="SUCCESS RATE"
          value={`${(proof.successRate * 100).toFixed(1)}%`}
          tone="var(--accent-green)"
        />
        <Stat
          label="QUEUE HEALTH"
          value={proof.queueHealth.toUpperCase()}
          tone={
            proof.queueHealth === "healthy"
              ? "var(--accent-green)"
              : proof.queueHealth === "saturated"
                ? "var(--accent-orange)"
                : "var(--accent-red)"
          }
        />
        <Stat
          label="BACKPRESSURE"
          value={proof.backpressureActive ? "ACTIVE" : "INACTIVE"}
          tone={proof.backpressureActive ? "var(--accent-red)" : "var(--accent-green)"}
        />
        <Stat
          label="AVG LATENCY"
          value={proof.avgLatency.toFixed(1)}
          tone="var(--text-primary)"
          suffix="ms"
        />
        <Stat
          label="CONSISTENCY"
          value="MAINTAINED"
          tone="var(--accent-green)"
        />
      </div>

      {proof.backpressureActive && (
        <div className="border-t px-5 py-3 text-xs text-[var(--text-secondary)] italic">
          System handling elevated load. Non-critical writes are safely dropped under backpressure.
          No critical data loss. Memory remains source of truth.
        </div>
      )}
    </div>
  );
}
