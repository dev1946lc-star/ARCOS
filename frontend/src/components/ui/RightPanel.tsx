"use client"

import { AlertTriangle, ArrowRightLeft, CheckCircle2, ShieldCheck, Zap } from "lucide-react"
import { useArcosSimStore } from "@/lib/store/arcos-store"
import { DraggablePanel } from "./DraggablePanel"

const flowTrace = [
  { title: "Arbitrage Signal Detected", time: "13:33:21", color: "#3b82f6", Icon: Zap },
  { title: "Model Inference Completed", time: "13:33:45", color: "#a855f7", Icon: Zap },
  { title: "Trade Execution Confirmed", time: "13:37:05", color: "#f97316", Icon: ArrowRightLeft },
  { title: "Payment Initiated", time: "13:37:19", color: "#22d3ee", Icon: ShieldCheck },
  { title: "Trade Validated", time: "13:34:08", color: "#22c55e", Icon: CheckCircle2 },
]

const eventFeedItems = [
  { time: "13:42:01", message: "Throttle-Gate-2 reported 3 dropped transactions", color: "#ec4899" },
  { time: "13:41:19", message: "Ledger-Weave-9 latency surge +12ms", color: "#f59e0b" },
  { time: "13:40:33", message: "New connecting stream: Market-A ↔ Flux-Core-03", color: "#3b82f6" },
  { time: "13:39:11", message: "Error burst cleared on Node-17", color: "#34d399" },
]

export function RightPanel() {
  const mode = useArcosSimStore((s) => s.mode)
  const selectedEntity = useArcosSimStore((s) => s.selectedEntity)
  const nodes = useArcosSimStore((s) => s.nodes)
  const flows = useArcosSimStore((s) => s.flows)
  const liveMetrics = useArcosSimStore((s) => s.liveMetrics)
  const selectedNode = nodes.find((n) => n.id === selectedEntity) ?? nodes[7] ?? null

  if (mode === "temporal") {
    return (
      <>
        <DraggablePanel id="right-event-details" title="Event Details" className="w-[300px]" defaultPosition={(vp) => ({ x: vp.w - 320, y: 80 })}>
          <div className="rounded-[14px] border border-orange-400/15 bg-orange-500/[0.06] p-2.5">
            <div className="flex items-center justify-between">
              <div className="text-[11px] font-medium text-white">Trade Execution Confirmed</div>
              <div className="rounded-full bg-orange-500/15 px-2 py-1 text-[9px] uppercase tracking-[0.16em] text-orange-200">Execution</div>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-1.5 text-[11px]">
              <div className="text-slate-400">Agent</div><div className="text-right text-slate-200">Exec-Core-03</div>
              <div className="text-slate-400">Status</div><div className="text-right text-emerald-300">Success</div>
              <div className="text-slate-400">Amount</div><div className="text-right text-white">$12,450.00</div>
              <div className="text-slate-400">Pair</div><div className="text-right text-white">ETH / USDC</div>
              <div className="text-slate-400">Network Fee</div><div className="text-right text-white">$0.1453</div>
              <div className="text-slate-400">Tx Hash</div><div className="text-right text-white">0x7f3a...9b2c</div>
            </div>
          </div>
        </DraggablePanel>

        <DraggablePanel id="right-flow-trace" title="Flow Trace" className="w-[300px]" defaultPosition={(vp) => ({ x: vp.w - 320, y: 320 })}>
          <div className="space-y-3">
            {flowTrace.map(({ title, time, color, Icon }) => (
              <div key={title} className="flex items-start gap-3">
                <div className="flex h-7 w-7 items-center justify-center rounded-[12px]" style={{ backgroundColor: `${color}18`, color }}>
                  <Icon className="h-3 w-3" />
                </div>
                <div className="flex-1">
                  <div className="text-[11px] text-white">{title}</div>
                  <div className="text-[10px] text-slate-500">{time}</div>
                </div>
              </div>
            ))}
          </div>
        </DraggablePanel>
      </>
    )
  }

  return (
    <>
      <DraggablePanel id="right-live-tps" title="Live TPS" className="w-[300px]" defaultPosition={(vp) => ({ x: vp.w - 320, y: 80 })}>
        <div className="flex items-baseline justify-between">
          <div className="text-[32px] font-semibold leading-none text-white">
            {liveMetrics.backendConnected ? Math.round(liveMetrics.tps).toLocaleString() : "4,820"}
          </div>
          <div className="text-[9px] uppercase tracking-[0.16em] text-slate-500">1m avg</div>
        </div>
        <div className="mt-2 grid grid-cols-5 gap-1.5">
          {[40, 56, 70, 48, 82].map((v, i) => (
            <div key={i} className="h-2 rounded-full bg-violet-500/15">
              <div className="h-full rounded-full bg-gradient-to-r from-violet-400 to-blue-500" style={{ width: `${v}%` }} />
            </div>
          ))}
        </div>
      </DraggablePanel>

      <DraggablePanel id="right-latency" title="Latency" className="w-[300px]" defaultPosition={(vp) => ({ x: vp.w - 320, y: 220 })}>
        <div className="flex items-center justify-between">
          <div className="text-[26px] font-semibold leading-none text-white">
            {liveMetrics.backendConnected ? Math.round(liveMetrics.latency) : 28} ms
          </div>
          <div className="text-[9px] uppercase tracking-[0.16em] text-slate-500">P95</div>
        </div>
        <svg viewBox="0 0 280 72" className="mt-2 h-12 w-full">
          <path d="M0 55 C30 54 50 44 72 47 S120 32 146 38 S195 22 224 26 S258 16 280 18" fill="none" stroke="#a855f7" strokeWidth="3" strokeLinecap="round" />
        </svg>
      </DraggablePanel>

      <DraggablePanel id="right-backpressure" title="Backpressure" className="w-[300px]" defaultPosition={(vp) => ({ x: vp.w - 320, y: 380 })}>
        <div className="mb-2 flex items-center justify-between text-[9px] uppercase tracking-[0.16em] text-slate-500">
          <span>Status</span>
          {liveMetrics.backendConnected ? (
            liveMetrics.queueUtilization > 0.8 ? (
              <span className="text-rose-300">Localized congestion detected</span>
            ) : liveMetrics.queueUtilization > 0.5 ? (
              <span className="text-amber-300">Elevated queue levels</span>
            ) : (
              <span className="text-emerald-300">System Healthy</span>
            )
          ) : (
            <span className="text-rose-300">Localized congestion detected</span>
          )}
        </div>
        <div className="relative h-20 overflow-hidden rounded-[16px] bg-[#0a1220]">
          <div className="absolute inset-0 transition-opacity duration-1000" style={{ opacity: !liveMetrics.backendConnected || liveMetrics.queueUtilization > 0.5 ? 1 : 0.1 }}>
             <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_50%,rgba(236,72,153,0.35),transparent_28%),radial-gradient(circle_at_65%_45%,rgba(168,85,247,0.42),transparent_30%),radial-gradient(circle_at_55%_60%,rgba(56,189,248,0.18),transparent_36%)]" />
          </div>
        </div>
      </DraggablePanel>

      <DraggablePanel id="right-event-feed" title="Event Feed" className="w-[300px]" defaultPosition={(vp) => ({ x: vp.w - 320, y: 550 })}>
        <div className="space-y-2">
          {liveMetrics.recentEvents.slice(0, 4).map((item: any, i) => (
            <div key={i} className="flex gap-3">
              <div className="mt-1.5 h-1.5 w-1.5 rounded-full" style={{ backgroundColor: item.event_type === "warning" ? "#f59e0b" : "#3b82f6" }} />
              <div>
                <div className="text-[10px] text-slate-500">{new Date(item.timestamp).toLocaleTimeString()}</div>
                <div className="text-[11px] text-slate-200">{item.message || JSON.stringify(item.details)}</div>
              </div>
            </div>
          ))}
          {liveMetrics.recentEvents.length === 0 && eventFeedItems.map((item) => (
            <div key={item.message} className="flex gap-3">
              <div className="mt-1.5 h-1.5 w-1.5 rounded-full" style={{ backgroundColor: item.color }} />
              <div>
                <div className="text-[10px] text-slate-500">{item.time}</div>
                <div className="text-[11px] text-slate-200">{item.message}</div>
              </div>
            </div>
          ))}
          {selectedNode && (
            <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-2 text-[11px]">
              <div className="flex items-center justify-between"><span className="text-slate-400">Selected Node</span><span className="font-medium text-white">{selectedNode.id}</span></div>
              <div className="mt-2 flex items-center justify-between"><span className="text-slate-400">Connected Flows</span>
                <span className="text-violet-200">{flows.filter((f) => f.sourceId === selectedNode.id || f.targetId === selectedNode.id).length}</span>
              </div>
            </div>
          )}
        </div>
      </DraggablePanel>
    </>
  )
}
