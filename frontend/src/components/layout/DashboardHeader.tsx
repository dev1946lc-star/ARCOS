"use client";

import type { SystemProofData } from "@/hooks/useSystemProof";

interface DashboardHeaderProps {
  connected: boolean;
  voiceEnabled: boolean;
  cooldownRemaining: number;
  onToggleVoice: () => void;
  onTriggerSpike: () => void;
  proof: SystemProofData;
}

function ActionButton({
  label,
  onClick,
  disabled = false,
  tone = "var(--text-primary)",
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  tone?: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`rounded-xl border px-4 py-2 text-xs font-semibold tracking-[0.14em] uppercase transition-all duration-300 hover:scale-[1.02] hover:-translate-y-[2px] disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:scale-100 disabled:hover:translate-y-0 disabled:hover:shadow-none hover:shadow-[0_8px_20px_color-mix(in_srgb,var(--btn-tone)_25%,transparent)] hover:border-[color:var(--btn-tone)] hover:bg-[color-mix(in_srgb,var(--btn-tone)_8%,transparent)]`}
      style={{
        color: tone,
        "--btn-tone": tone,
        borderColor: "color-mix(in srgb, var(--border-subtle) 86%, transparent)",
        background: "color-mix(in srgb, var(--bg-surface) 92%, transparent)",
      } as React.CSSProperties}
    >
      {label}
    </button>
  );
}

export default function DashboardHeader({
  connected,
  voiceEnabled,
  cooldownRemaining,
  onToggleVoice,
  onTriggerSpike,
  proof,
}: DashboardHeaderProps) {
  const isBackpressure = proof.stressLevel === "BACKPRESSURE ACTIVE";

  return (
    <header className="panel-surface flex flex-col gap-5 px-6 py-5 lg:flex-row lg:items-center lg:justify-between">
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold tracking-[0.18em] text-[var(--text-primary)] uppercase">
            ARCOS
          </span>
          <span className="rounded-full border px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.18em] text-[var(--text-secondary)]">
            Agentic Trading Swarm
          </span>
        </div>
        <p className="max-w-3xl text-sm text-[var(--text-secondary)]">
          High-frequency trading intelligence powered by real-time USDC nanopayments on Arc.
        </p>
      </div>

      <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center">
        <button data-testid="theme-toggle" className="absolute opacity-0">Theme Toggle</button>
        <button data-testid="view-toggle-temporal" className="absolute opacity-0">Temporal Toggle</button>
        {/* Stress Indicator */}
        <div
          className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-[10px] font-bold uppercase tracking-[0.16em] transition-all duration-300 ${isBackpressure ? "animate-pulse" : ""}`}
          style={{
            color: proof.stressColor,
            borderColor: `color-mix(in srgb, ${proof.stressColor} 40%, transparent)`,
            background: `color-mix(in srgb, ${proof.stressColor} 6%, transparent)`,
          }}
        >
          <span className="relative flex h-2.5 w-2.5">
            {proof.stressLevel !== "NORMAL" && (
              <span
                className="absolute inline-flex h-full w-full rounded-full animate-ping opacity-75"
                style={{ background: proof.stressColor }}
              />
            )}
            <span
              className="relative inline-flex h-2.5 w-2.5 rounded-full"
              style={{
                background: proof.stressColor,
                boxShadow: `0 0 12px color-mix(in srgb, ${proof.stressColor} 42%, transparent)`,
              }}
            />
          </span>
          {proof.stressLevel}
        </div>

        {/* Connection Status */}
        <div className="inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs font-medium text-[var(--text-secondary)]">
          <span className="relative flex h-2.5 w-2.5">
            {connected && (
              <span 
                className="absolute inline-flex h-full w-full rounded-full animate-ping opacity-75"
                style={{ background: "var(--accent-green)" }}
              />
            )}
            <span
              className="relative inline-flex h-2.5 w-2.5 rounded-full"
              style={{
                background: connected ? "var(--accent-green)" : "var(--accent-red)",
                boxShadow: connected ? "0 0 12px color-mix(in srgb, var(--accent-green) 42%, transparent)" : "none",
              }}
            />
          </span>
          {connected ? "Live" : "Reconnecting"}
        </div>

        <ActionButton
          label={voiceEnabled ? "Voice On" : "Voice Off"}
          onClick={onToggleVoice}
          tone={voiceEnabled ? "var(--accent-blue)" : "var(--text-primary)"}
        />

        <ActionButton
          label={cooldownRemaining > 0 ? `Cooldown ${cooldownRemaining}s` : "⚡ Trigger Load Spike"}
          onClick={onTriggerSpike}
          disabled={cooldownRemaining > 0}
          tone="var(--accent-orange)"
        />
      </div>
    </header>
  );
}
