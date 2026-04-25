"use client"

import type { ReactNode } from "react"
import { useArcosSimStore } from "@/lib/store/arcos-store"
import { cn } from "@/lib/utils"

const modes = [
  { value: "spatial", label: "Spatial View" },
  { value: "temporal", label: "Temporal: Live" },
] as const

function chromeButton(children: ReactNode, className?: string) {
  return (
    <div className={cn("flex h-8 items-center justify-center rounded-[10px] border border-white/10 bg-[#050b16]/72 text-slate-300 backdrop-blur-md", className)}>
      {children}
    </div>
  )
}

export function TopBar() {
  const mode = useArcosSimStore((s) => s.mode)
  const streamStatus = useArcosSimStore((s) => s.streamStatus)
  const liveMetrics = useArcosSimStore((s) => s.liveMetrics)
  const setMode = useArcosSimStore((s) => s.setMode)

  return (
    <header className="mx-auto flex h-10 max-w-[1560px] items-center justify-between px-1 text-white">
      <div className="leading-none">
        <div className="font-display text-[2rem] font-semibold leading-[0.82] tracking-[-0.12em] text-white">
          ARCOS
        </div>
        <div className="mt-0.5 pl-0.5 text-[8px] uppercase tracking-[0.24em] text-slate-500">Agentic Economic OS</div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex h-8 items-center rounded-[10px] border border-white/10 bg-[#050b16]/72 p-1 backdrop-blur-md">
          {modes.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setMode(option.value)}
              className={cn(
                "rounded-[8px] px-3 py-1.5 text-[9px] font-semibold uppercase tracking-[0.16em] transition",
                mode === option.value
                  ? "bg-gradient-to-r from-blue-500/90 to-violet-500/90 text-white shadow-[0_0_18px_rgba(99,102,241,0.28)]"
                  : "text-slate-400 hover:text-slate-100",
              )}
            >
              {option.label}
            </button>
          ))}
        </div>

        <div className="hidden items-center gap-3 lg:flex">
          <span className="text-[9px] uppercase tracking-[0.16em] text-slate-500">System Status</span>
          <span className={cn("text-[10px] font-semibold uppercase tracking-[0.14em]", liveMetrics.backendConnected ? "text-emerald-300" : "text-amber-300")}>
            {liveMetrics.backendConnected ? "Optimal" : "Offline"}
          </span>
          <svg viewBox="0 0 110 24" className={cn("h-4 w-[84px] transition-colors", liveMetrics.backendConnected ? "text-emerald-300" : "text-amber-500/50")}>
            <path
              d={liveMetrics.backendConnected ? "M0 12h28l6-8 8 16 8-16 6 8h44" : "M0 12h110"}
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {chromeButton(
          <span className="px-0.5 text-[8px] uppercase tracking-[0.14em] text-violet-200">
            {streamStatus} · {liveMetrics.backendConnected ? "●" : "○"}
          </span>,
          "min-w-[84px] rounded-full border-violet-400/15 bg-violet-400/[0.06]",
        )}
      </div>
    </header>
  )
}
