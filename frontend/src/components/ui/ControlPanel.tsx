"use client"

import { useState } from "react"
import { Play, Zap, AlertCircle, CheckCircle2 } from "lucide-react"
import { DraggablePanel } from "./DraggablePanel"
import { triggerSpike, triggerDemoStory } from "@/lib/api"
import { useArcosSimStore } from "@/lib/store/arcos-store"

export function ControlPanel() {
  const mode = useArcosSimStore((s) => s.mode)
  const [spikeStatus, setSpikeStatus] = useState<"idle" | "loading" | "success" | "error">("idle")
  const [demoStatus, setDemoStatus] = useState<"idle" | "loading" | "success" | "error">("idle")

  if (mode !== "spatial") return null

  const handleSpike = async () => {
    try {
      setSpikeStatus("loading")
      await triggerSpike()
      setSpikeStatus("success")
      setTimeout(() => setSpikeStatus("idle"), 3000)
    } catch {
      setSpikeStatus("error")
      setTimeout(() => setSpikeStatus("idle"), 3000)
    }
  }

  const handleDemo = async () => {
    try {
      setDemoStatus("loading")
      await triggerDemoStory()
      setDemoStatus("success")
      setTimeout(() => setDemoStatus("idle"), 3000)
    } catch {
      setDemoStatus("error")
      setTimeout(() => setDemoStatus("idle"), 3000)
    }
  }

  return (
    <DraggablePanel id="control-panel" title="System Controls" className="w-[280px]" defaultPosition={(vp) => ({ x: vp.w - 640, y: 80 })}>
      <div className="space-y-3">
        <div className="rounded-[14px] border border-white/6 bg-white/[0.03] p-3">
          <div className="mb-2 text-[11px] font-medium text-white">Load Injector</div>
          <p className="mb-3 text-[10px] text-slate-400">Trigger a massive influx of synthetic jobs to test the autonomous scaling and backpressure mechanisms.</p>
          <button
            onClick={handleSpike}
            disabled={spikeStatus === "loading"}
            className="flex w-full items-center justify-center gap-2 rounded-[10px] bg-rose-500/20 py-2 text-[11px] font-medium text-rose-300 transition-colors hover:bg-rose-500/30 disabled:opacity-50"
          >
            {spikeStatus === "loading" ? (
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-rose-300 border-t-transparent" />
            ) : spikeStatus === "success" ? (
              <><CheckCircle2 className="h-3.5 w-3.5" /> Injected</>
            ) : spikeStatus === "error" ? (
              <><AlertCircle className="h-3.5 w-3.5" /> Failed</>
            ) : (
              <><Zap className="h-3.5 w-3.5" /> Trigger Load Spike</>
            )}
          </button>
        </div>

        <div className="rounded-[14px] border border-white/6 bg-white/[0.03] p-3">
          <div className="mb-2 text-[11px] font-medium text-white">Demo Sequence</div>
          <p className="mb-3 text-[10px] text-slate-400">Run the predefined narrative demonstration highlighting agent adaptations and streaming nanopayments.</p>
          <button
            onClick={handleDemo}
            disabled={demoStatus === "loading"}
            className="flex w-full items-center justify-center gap-2 rounded-[10px] bg-violet-500/20 py-2 text-[11px] font-medium text-violet-300 transition-colors hover:bg-violet-500/30 disabled:opacity-50"
          >
            {demoStatus === "loading" ? (
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-violet-300 border-t-transparent" />
            ) : demoStatus === "success" ? (
              <><CheckCircle2 className="h-3.5 w-3.5" /> Running</>
            ) : demoStatus === "error" ? (
              <><AlertCircle className="h-3.5 w-3.5" /> Failed</>
            ) : (
              <><Play className="h-3.5 w-3.5" /> Start Demo Story</>
            )}
          </button>
        </div>
      </div>
    </DraggablePanel>
  )
}
