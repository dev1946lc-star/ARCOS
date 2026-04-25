"use client"

import { Lock, Orbit, Search, Unplug } from "lucide-react"
import { useArcosSimStore } from "@/lib/store/arcos-store"
import { DraggablePanel } from "./DraggablePanel"

const actionIcons = [
  { label: "Orbit", Icon: Orbit },
  { label: "Zoom", Icon: Search, active: true },
  { label: "Isolate", Icon: Unplug },
  { label: "Follow", Icon: Lock },
]

export function CenterPanel() {
  const mode = useArcosSimStore((s) => s.mode)
  const nodes = useArcosSimStore((s) => s.nodes)
  const selectedEntity = useArcosSimStore((s) => s.selectedEntity)
  const liveMetrics = useArcosSimStore((s) => s.liveMetrics)
  
  const selectedNode = nodes.find((n) => n.id === selectedEntity) ?? nodes[7] ?? null

  if (mode !== "spatial" || !selectedNode) return null

  const agentStats = liveMetrics.leaderboard.find((a: any) => a.id === selectedNode.id) || { personality: selectedNode.type, total_profit: 0 }

  return (
    <DraggablePanel id="center-agent-snapshot" className="w-[360px]" defaultPosition={{ x: (typeof window !== 'undefined' ? window.innerWidth : 1200) / 2 - 180, y: (typeof window !== 'undefined' ? window.innerHeight : 800) - 300 }}>
      <div className="flex items-start justify-between">
        <div>
          <div className="text-[9px] uppercase tracking-[0.16em] text-slate-500">Agent Snapshot</div>
          <div className="mt-1 text-[13px] font-semibold text-white">{selectedNode.id.toUpperCase()}</div>
        </div>
        <div className="text-[9px] uppercase tracking-[0.16em] text-slate-500">TYPE: {selectedNode.type}</div>
      </div>

      <div className="mt-3 grid grid-cols-[46px_1fr] gap-3">
        <div className="flex h-[46px] w-[46px] items-center justify-center rounded-[14px] border border-violet-400/30 bg-violet-500/10 text-violet-200">
          <Orbit className="h-4.5 w-4.5" />
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div><div className="text-[9px] uppercase tracking-[0.16em] text-slate-500">Profile</div><div className="mt-1 text-[10px] text-white uppercase tracking-[0.08em]">{agentStats.personality}</div></div>
          <div><div className="text-[9px] uppercase tracking-[0.16em] text-slate-500">Load</div><div className="mt-1 text-[11px] text-white">{Math.round(selectedNode.activity * 100)}%</div></div>
          <div><div className="text-[9px] uppercase tracking-[0.16em] text-slate-500">Profit</div><div className="mt-1 text-[11px] text-emerald-300">${agentStats.total_profit.toFixed(1)}</div></div>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-4 overflow-hidden rounded-[16px] border border-white/8 bg-black/25">
        {actionIcons.map(({ label, Icon, active }) => (
          <button key={label} type="button"
            className={`flex flex-col items-center gap-1 border-r border-white/6 px-2 py-2.5 last:border-r-0 ${active ? "bg-violet-500/14 text-violet-200" : "text-slate-300"}`}>
            <Icon className="h-3 w-3" />
            <span className="text-[9px] uppercase tracking-[0.16em]">{label}</span>
          </button>
        ))}
      </div>
    </DraggablePanel>
  )
}
