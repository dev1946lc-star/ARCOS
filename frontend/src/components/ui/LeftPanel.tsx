"use client"

import { Activity, Cpu, RadioTower, ShieldCheck, Wallet } from "lucide-react"
import { useArcosSimStore } from "@/lib/store/arcos-store"
import { DraggablePanel } from "./DraggablePanel"

const eventStreams = [
  { label: "Signals", count: "1,240 events", Icon: RadioTower, color: "#3b82f6" },
  { label: "Compute", count: "890 events", Icon: Cpu, color: "#a855f7" },
  { label: "Executions", count: "2,450 events", Icon: Activity, color: "#f97316" },
  { label: "Payments", count: "1,130 events", Icon: Wallet, color: "#22d3ee" },
  { label: "Validations", count: "740 events", Icon: ShieldCheck, color: "#22c55e" },
]

const quickAgents = [
  { name: "Aegis-Node-17", role: "Risk Guardian", throughput: "1,240 tps", color: "#3b82f6" },
  { name: "Flux-Core-03", role: "Flow Engine", throughput: "890 tps", color: "#f59e0b" },
  { name: "Ledger-Weave-9", role: "Settlement Mesh", throughput: "2,450 tps", color: "#8b5cf6", active: true },
  { name: "Throttle-Gate-2", role: "Backpressure Ctrl", throughput: "310 tps", color: "#ec4899" },
]

export function LeftPanel() {
  const mode = useArcosSimStore((s) => s.mode)
  const streamStatus = useArcosSimStore((s) => s.streamStatus)
  const setStreamStatus = useArcosSimStore((s) => s.setStreamStatus)
  const liveMetrics = useArcosSimStore((s) => s.liveMetrics)

  if (mode === "temporal") {
    return (
      <>
        <DraggablePanel id="left-event-streams" title="Event Streams" className="w-[280px]" defaultPosition={{ x: 20, y: 80 }}>
          <div className="space-y-2">
            {eventStreams.map(({ label, count, Icon, color }) => (
              <div key={label} className="flex items-center justify-between rounded-[14px] border border-white/6 bg-white/[0.03] px-2.5 py-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-7 w-7 items-center justify-center rounded-lg" style={{ backgroundColor: `${color}18`, color }}>
                    <Icon className="h-3 w-3" />
                  </div>
                  <div>
                    <div className="text-[11px] font-medium text-white">{label}</div>
                    <div className="text-[10px] text-slate-500">{count}</div>
                  </div>
                </div>
                <div className="h-4 w-4 rounded-md border border-white/10 bg-blue-500/80" />
              </div>
            ))}
          </div>
        </DraggablePanel>

        <DraggablePanel id="left-filters" title="Filters" className="w-[280px]" defaultPosition={{ x: 20, y: 380 }}>
          <div className="space-y-2 text-[11px]">
            {["Last 15 Minutes", "All Agents", "All Types"].map((label, i) => (
              <div key={label}>
                <div className="mb-1 text-[9px] uppercase tracking-[0.16em] text-slate-500">
                  {i === 0 ? "Time Range" : i === 1 ? "Agents" : "Event Types"}
                </div>
                <div className="rounded-[14px] border border-white/8 bg-white/[0.03] px-2.5 py-2 text-slate-300">{label}</div>
              </div>
            ))}
            <button type="button" onClick={() => setStreamStatus(streamStatus === "live" ? "paused" : "live")}
              className="mt-1 flex w-full items-center justify-between rounded-[14px] border border-white/8 bg-white/[0.03] px-2.5 py-2 text-left">
              <span className="text-[11px] text-slate-300">Show System Events</span>
              <span className={`rounded-full px-2 py-1 text-[9px] uppercase tracking-[0.16em] ${streamStatus === "live" ? "bg-blue-500/20 text-blue-200" : "bg-white/8 text-slate-400"}`}>
                {streamStatus}
              </span>
            </button>
          </div>
        </DraggablePanel>
      </>
    )
  }

  return (
    <>
      <DraggablePanel id="left-agents" title={`Agent Leaderboard Summary`} className="w-[280px]" defaultPosition={{ x: 20, y: 80 }}>
        <div className="space-y-3">
          {liveMetrics.backendConnected && liveMetrics.leaderboard.length > 0 ? (
            liveMetrics.leaderboard.slice(0, 4).map((agent: any) => (
              <div key={agent.id}
                className="rounded-[14px] border border-white/6 bg-white/[0.03] px-2.5 py-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-400">
                    <Activity className="h-3 w-3" />
                  </div>
                  <div className="flex-1">
                    <div className="text-[11px] font-medium text-white">{agent.id}</div>
                    <div className="text-[10px] text-slate-500 uppercase tracking-[0.16em]">{agent.personality}</div>
                  </div>
                </div>
                <div className="mt-2 flex items-center justify-between">
                  <div className="text-[9px] uppercase tracking-[0.16em] text-slate-500">Total Profit</div>
                  <div className="text-[11px] text-emerald-300">+${agent.total_profit.toFixed(2)}</div>
                </div>
              </div>
            ))
          ) : (
            quickAgents.map((agent) => (
              <div key={agent.name}
                className={`rounded-[14px] border px-2.5 py-2 ${agent.active ? "border-violet-400/30 bg-violet-500/8" : "border-white/6 bg-white/[0.03]"}`}>
                <div className="flex items-center gap-3">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full" style={{ backgroundColor: `${agent.color}18`, color: agent.color }}>
                    <Activity className="h-3 w-3" />
                  </div>
                  <div className="flex-1">
                    <div className="text-[11px] font-medium text-white">{agent.name}</div>
                    <div className="text-[10px] text-slate-500">{agent.role}</div>
                  </div>
                </div>
                <div className="mt-2 flex items-center justify-between">
                  <div className="text-[9px] uppercase tracking-[0.16em] text-slate-500">Throughput</div>
                  <div className="text-[11px] text-white">{agent.throughput}</div>
                </div>
              </div>
            ))
          )}
        </div>
      </DraggablePanel>

      <DraggablePanel id="left-filters-spatial" title="Filters" className="w-[280px]" defaultPosition={{ x: 20, y: 460 }}>
        <div className="space-y-2.5 text-[11px]">
          <div className="flex items-center justify-between text-slate-400"><span>Role: Market / Ops</span><span className="h-4 w-4 rounded-md border border-white/10" /></div>
          <div className="flex items-center justify-between text-slate-400"><span>Show Streams</span><span className="h-4 w-4 rounded-md bg-blue-500/80" /></div>
          <div className="flex items-center justify-between text-slate-400"><span>Highlight Errors</span><span className="h-4 w-4 rounded-md bg-blue-500/80" /></div>
        </div>
      </DraggablePanel>
    </>
  )
}
