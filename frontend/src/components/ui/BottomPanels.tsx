"use client"

import { AlertTriangle, ArrowUpRight, CheckCircle2 } from "lucide-react"
import { useArcosSimStore } from "@/lib/store/arcos-store"
import { DraggablePanel } from "./DraggablePanel"

const streamColors = [
  { label: "Signals", rate: "1,240 /m", color: "#3b82f6" },
  { label: "Compute", rate: "890 /m", color: "#a855f7" },
  { label: "Executions", rate: "2,450 /m", color: "#f97316" },
  { label: "Payments", rate: "1,130 /m", color: "#22d3ee" },
  { label: "Validations", rate: "740 /m", color: "#22c55e" },
]

function ThroughputTraces() {
  return (
    <div className="space-y-3">
      {streamColors.map((stream, i) => (
        <div key={stream.label} className="flex items-center gap-3">
          <div className="w-18 text-[10px] font-medium uppercase tracking-[0.14em]" style={{ color: stream.color }}>{stream.label}</div>
          <div className="relative h-6 flex-1 overflow-hidden rounded-full bg-white/[0.03]">
            <svg viewBox="0 0 320 32" className="h-full w-full">
              <path d={`M0,${18 + i} C40,${8 + i * 2} 65,${30 - i} 108,${16 + i} S175,${5 + i} 220,${19 - i} S282,${26 + i} 320,${8 + i}`}
                fill="none" stroke={stream.color} strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
          <div className="w-14 text-right text-[10px] font-medium text-slate-300">{stream.rate}</div>
        </div>
      ))}
    </div>
  )
}

export function BottomPanels() {
  const mode = useArcosSimStore((s) => s.mode)
  const liveMetrics = useArcosSimStore((s) => s.liveMetrics)
  const nodes = useArcosSimStore((s) => s.nodes)

  if (mode === "temporal") {
    return (
      <>
        <DraggablePanel id="bottom-time-nav" title="Time Navigation" showControls={false} className="w-[320px]" defaultPosition={{ x: (typeof window !== 'undefined' ? window.innerWidth : 1200) / 2 - 400, y: (typeof window !== 'undefined' ? window.innerHeight : 800) - 200 }}>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[12px] text-slate-400">May 15, 2025</p>
                <p className="mt-1 text-[22px] font-semibold text-white">13:39:42</p>
              </div>
              <span className="rounded-full bg-emerald-400/10 px-2 py-1 text-[9px] uppercase tracking-[0.16em] text-emerald-300">Live</span>
            </div>
            <div className="flex items-center gap-2">
              {["|<", "<<", "▶", ">>", ">|"].map((label, i) => (
                <button key={label} type="button"
                  className={`flex h-7 w-7 items-center justify-center rounded-[12px] border text-[11px] ${
                    i === 2 ? "border-violet-400/40 bg-violet-500/20 text-violet-100 shadow-[0_0_24px_rgba(139,92,246,0.25)]" : "border-white/8 bg-white/[0.03] text-slate-300"}`}>
                  {label}
                </button>
              ))}
            </div>
          </div>
        </DraggablePanel>

        <DraggablePanel id="bottom-event-summary" title="Event Summary" showControls={false} className="w-[320px]" defaultPosition={{ x: (typeof window !== 'undefined' ? window.innerWidth : 1200) / 2 - 60, y: (typeof window !== 'undefined' ? window.innerHeight : 800) - 200 }}>
          <div className="flex items-center gap-3">
            <div className="relative h-18 w-18 rounded-full bg-[conic-gradient(#3b82f6_0_19%,#a855f7_19%_33%,#f97316_33%_71%,#22d3ee_71%_89%,#22c55e_89%_100%)] p-2">
              <div className="flex h-full w-full flex-col items-center justify-center rounded-full bg-[#07111f]">
                <div className="text-[20px] font-semibold text-white">{liveMetrics.totalTransactions || "6,450"}</div>
                <div className="text-[9px] uppercase tracking-[0.14em] text-slate-500">Total</div>
              </div>
            </div>
            <div className="flex-1 space-y-2">
              {streamColors.map((s) => (
                <div key={s.label} className="flex items-center justify-between text-[11px]">
                  <span className="flex items-center gap-2 text-slate-300"><span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: s.color }} />{s.label}</span>
                  <span className="text-white">{s.rate.replace(" /m", "")}</span>
                </div>
              ))}
            </div>
          </div>
        </DraggablePanel>

        <DraggablePanel id="bottom-throughput" title="Throughput Over Time" showControls={false} className="w-[320px]" defaultPosition={{ x: (typeof window !== 'undefined' ? window.innerWidth : 1200) / 2 + 280, y: (typeof window !== 'undefined' ? window.innerHeight : 800) - 200 }}>
          <ThroughputTraces />
        </DraggablePanel>

        <DraggablePanel id="bottom-insights" title="System Insights" showControls={false} className="w-[320px]" defaultPosition={{ x: (typeof window !== 'undefined' ? window.innerWidth : 1200) / 2 + 620, y: (typeof window !== 'undefined' ? window.innerHeight : 800) - 200 }}>
          <div className="space-y-4">
            <div className="flex items-start gap-3 text-sm text-slate-300"><ArrowUpRight className="mt-0.5 h-4 w-4 text-sky-400" /><span>Execution throughput increased 38% in the last 5 minutes</span></div>
            <div className="flex items-start gap-3 text-sm text-slate-300"><AlertTriangle className="mt-0.5 h-4 w-4 text-amber-400" /><span>Backpressure detected between Compute and Executions</span></div>
            <div className="flex items-start gap-3 text-sm text-slate-300"><CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-400" /><span>All system validations are healthy</span></div>
          </div>
        </DraggablePanel>
      </>
    )
  }

  return (
    <>
      <DraggablePanel id="bottom-economic" title="Economic Advantage" showControls={false} className="w-[320px]" defaultPosition={{ x: (typeof window !== 'undefined' ? window.innerWidth : 1200) / 2 - 340, y: (typeof window !== 'undefined' ? window.innerHeight : 800) - 180 }}>
        <div className="flex items-center gap-3">
          <div>
            <div className="text-[30px] font-semibold text-emerald-300">
              {liveMetrics.backendConnected ? `${Math.round(liveMetrics.savingsFactor).toLocaleString()}x` : "24,188x"}
            </div>
            <div className="mt-1 text-[9px] uppercase tracking-[0.16em] text-slate-500">Cheaper Execution</div>
          </div>
          <div className="relative h-18 w-18 rounded-full bg-[conic-gradient(#34d399_0_78%,rgba(255,255,255,0.08)_78%_100%)] p-4">
            <div className="h-full w-full rounded-full bg-[#07111f]" />
          </div>
        </div>
      </DraggablePanel>

      <DraggablePanel id="bottom-value-streams" title="Value Streams" showControls={false} className="w-[320px]" defaultPosition={{ x: (typeof window !== 'undefined' ? window.innerWidth : 1200) / 2, y: (typeof window !== 'undefined' ? window.innerHeight : 800) - 180 }}>
        <ThroughputTraces />
      </DraggablePanel>

      <DraggablePanel id="bottom-sys-health" title="System Health" showControls={false} className="w-[320px]" defaultPosition={{ x: (typeof window !== 'undefined' ? window.innerWidth : 1200) / 2 + 340, y: (typeof window !== 'undefined' ? window.innerHeight : 800) - 180 }}>
        <div className="space-y-2 text-[11px]">
          <div className="flex items-center justify-between"><span className="text-slate-400">Nodes Online</span><span className="text-emerald-300">{liveMetrics.activeAgents || nodes.length}/102</span></div>
          <div className="flex items-center justify-between"><span className="text-slate-400">Packet Success</span><span className="text-emerald-300">{liveMetrics.backendConnected ? "99.99%" : "99.89%"}</span></div>
          <div className="flex items-center justify-between"><span className="text-slate-400">Queue Utilization</span><span className="text-cyan-200">{Math.round(liveMetrics.queueUtilization * 100)}%</span></div>
          <div className="flex items-center justify-between"><span className="text-slate-400">Uptime</span><span className="text-slate-100">{liveMetrics.backendConnected ? "7D 14H 22M" : "0D 0H 0M"}</span></div>
        </div>
      </DraggablePanel>
    </>
  )
}
