"use client"

import { useMemo, useState } from "react"
import { Zap, Cpu, GitBranch, CreditCard, Shield, Pause, Play, Maximize2 } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { DraggablePanel } from "./DraggablePanel"
import { timelineEvents, eventStreams } from "@/lib/mock-data"
import { useArcosSimStore } from "@/lib/store/arcos-store"

const iconMap: Record<string, any> = {
  signals: Zap,
  compute: Cpu,
  executions: GitBranch,
  payments: CreditCard,
  validations: Shield,
}

const colorMap: Record<string, any> = {
  signals: { bg: "bg-blue-500", text: "text-blue-500", hex: "#3b82f6", glow: "shadow-[0_0_10px_rgba(59,130,246,0.5)]" },
  compute: { bg: "bg-orange-500", text: "text-orange-500", hex: "#f97316", glow: "shadow-[0_0_10px_rgba(249,115,22,0.5)]" },
  executions: { bg: "bg-purple-500", text: "text-purple-500", hex: "#a855f7", glow: "shadow-[0_0_10px_rgba(168,85,247,0.5)]" },
  payments: { bg: "bg-cyan-500", text: "text-cyan-500", hex: "#06b6d4", glow: "shadow-[0_0_10px_rgba(6,182,212,0.5)]" },
  validations: { bg: "bg-green-500", text: "text-green-500", hex: "#22c55e", glow: "shadow-[0_0_10px_rgba(34,197,94,0.5)]" },
}

function FlowingDots({ color, count }: { color: string; count: number }) {
  const dots = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => ({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        size: Math.random() * 2.2 + 1.4,
        opacity: Math.random() * 0.34 + 0.18,
      })),
    [count],
  )

  return (
    <svg className="animate-temporal-drift absolute inset-0 h-full w-full pointer-events-none" preserveAspectRatio="none">
      <defs>
        <filter id={`glow-${color.replace("#", "")}`}>
          <feGaussianBlur stdDeviation="2" result="coloredBlur" />
          <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      {dots.map((dot) => (
        <circle
          key={dot.id}
          cx={`${dot.x}%`}
          cy={`${dot.y}%`}
          r={dot.size}
          fill={color}
          opacity={dot.opacity}
          filter={`url(#glow-${color.replace("#", "")})`}
        />
      ))}
    </svg>
  )
}

export function TemporalLiveFeed() {
  const mode = useArcosSimStore((s) => s.mode)
  const liveMetrics = useArcosSimStore((s) => s.liveMetrics)
  const [selectedTimeRange, setSelectedTimeRange] = useState("15m")
  const [isPaused, setIsPaused] = useState(false)
  const [hoveredEvent, setHoveredEvent] = useState<string | null>(null)

  const timeRanges = ["1m", "5m", "15m", "1h", "6h", "24h"]
  const timeLabels = ["13:30", "13:32", "13:34", "13:36", "13:38", "13:39:42", "13:40", "13:42", "13:44"]
  const pressureDots = useMemo(
    () =>
      Array.from({ length: 24 }, (_, i) => ({
        id: i,
        warm: i % 7 === 0 || i % 11 === 0,
      })),
    [],
  )

  if (mode !== "temporal") return null

  return (
    <DraggablePanel
      id="temporal-live-feed"
      title="Temporal Live Feed"
      className="w-[960px] max-w-[calc(100vw-64px)]"
      defaultPosition={(vp) => ({ x: vp.w / 2 - 480, y: 112 })}
    >
      <div className="flex flex-col overflow-hidden bg-transparent">
        <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
          <div className="flex items-center gap-3">
            <motion.span className="flex items-center gap-1.5" animate={{ opacity: [1, 0.5, 1] }} transition={{ duration: 2, repeat: Infinity }}>
              <span className={`h-2 w-2 rounded-full ${liveMetrics.backendConnected ? "bg-green-500" : "bg-amber-500"}`} />
              <span className={`text-xs font-medium ${liveMetrics.backendConnected ? "text-green-500" : "text-amber-500"}`}>LIVE</span>
            </motion.span>
          </div>

          <div className="flex items-center gap-2">
            {timeRanges.map((range) => (
              <button key={range} onClick={() => setSelectedTimeRange(range)} className={`rounded px-2 py-1 text-xs font-medium transition-all ${selectedTimeRange === range ? "bg-blue-500 text-white" : "text-slate-400 hover:bg-white/5 hover:text-white"}`}>
                {range}
              </button>
            ))}
            <button className="rounded px-3 py-1 text-xs font-medium text-slate-400 transition-colors hover:bg-white/5 hover:text-white">Now</button>
            <button onClick={() => setIsPaused(!isPaused)} className="rounded p-1.5 text-slate-400 transition-colors hover:bg-white/5 hover:text-white">
              {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
            </button>
            <button className="rounded p-1.5 text-slate-400 transition-colors hover:bg-white/5 hover:text-white">
              <Maximize2 className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-hidden">
          <div className="flex items-center border-b border-white/10 px-4 py-2">
            <div className="w-28 shrink-0" />
            <div className="flex flex-1 items-center justify-between px-2">
              {timeLabels.map((label, i) => (
                <div key={i} className="flex flex-col items-center">
                  {label === "13:39:42" ? (
                    <motion.div className="rounded bg-blue-500 px-2 py-1 text-xs font-medium text-white" animate={{ scale: [1, 1.05, 1] }} transition={{ duration: 2, repeat: Infinity }}>
                      {label}
                    </motion.div>
                  ) : (
                    <span className="text-xs text-slate-500">{label}</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="max-h-[420px] flex-1 overflow-y-auto">
            {eventStreams.map((stream: any) => {
              const Icon = iconMap[stream.id] || Zap
              const colors = colorMap[stream.id] || colorMap.signals

              const streamEvents = liveMetrics.backendConnected
                ? liveMetrics.recentEvents
                    .filter((e: any) => {
                      const type = (e.event_type || "").toLowerCase()
                      if (stream.id === "signals" && type.includes("signal")) return true
                      if (stream.id === "compute" && (type.includes("job") || type.includes("compute"))) return true
                      if (stream.id === "payments" && type.includes("payment")) return true
                      if (stream.id === "validations" && type.includes("valid")) return true
                      if (stream.id === "executions" && type.includes("exec")) return true
                      return type.includes(stream.id.substring(0, 4))
                    })
                    .map((e: any, idx) => ({
                      id: e.event_id || `ev-${stream.id}-${idx}`,
                      title: e.message || "Event Processed",
                      timestamp: new Date(e.timestamp || Date.now()).toLocaleTimeString(),
                      x: (idx * 15 + 10) % 85 + 5,
                      showLabel: idx === 0,
                      isHighlighted: idx === 0,
                    }))
                    .slice(0, 5)
                : timelineEvents[stream.id as keyof typeof timelineEvents] || []

              return (
                <div key={stream.id} className="group relative flex items-center border-b border-white/5 px-4 py-3.5">
                  <div className="w-28 shrink-0">
                    <div className="flex items-center gap-2">
                      <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${colors.bg}/10`}><Icon className={`h-4 w-4 ${colors.text}`} /></div>
                      <span className="text-sm font-medium uppercase text-white">{stream.label}</span>
                    </div>
                    <div className="ml-10 mt-1 flex items-center gap-1">
                      <span className={`h-2 w-2 rounded-full ${colors.bg}`} />
                      <span className={`text-xs font-medium ${colors.text}`}>{liveMetrics.backendConnected ? Math.floor(stream.count * (liveMetrics.tps / 4820 || 1)).toLocaleString() : stream.count.toLocaleString()}</span>
                    </div>
                  </div>

                  <div className="relative h-14 flex-1 overflow-hidden">
                    <FlowingDots color={colors.hex} count={18} />

                    <AnimatePresence>
                      {streamEvents.map((event: any) => (
                        <motion.div
                          key={event.id}
                          initial={{ scale: 0, opacity: 0 }}
                          animate={{ scale: 1, opacity: 1 }}
                          exit={{ scale: 0, opacity: 0 }}
                          className="group/event absolute cursor-pointer"
                          style={{ left: `${event.x}%`, top: "50%", transform: "translateY(-50%)" }}
                          onMouseEnter={() => setHoveredEvent(event.id)}
                          onMouseLeave={() => setHoveredEvent(null)}
                        >
                          <AnimatePresence>
                            {(hoveredEvent === event.id || event.showLabel) && (
                              <motion.div initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 5 }} className="absolute bottom-full left-1/2 z-20 mb-3 -translate-x-1/2">
                                <div className="whitespace-nowrap rounded-lg border border-white/10 bg-[#07111f] px-3 py-2 shadow-xl">
                                  <p className="text-xs font-medium text-white">{event.title}</p>
                                  {event.subtitle && <p className="text-xs text-slate-400">{event.subtitle}</p>}
                                  <p className="mt-0.5 text-xs text-slate-500">{event.timestamp}</p>
                                </div>
                                <div className="absolute left-1/2 top-full -mt-1 h-2 w-2 -translate-x-1/2 rotate-45 transform border-b border-r border-white/10 bg-[#07111f]" />
                              </motion.div>
                            )}
                          </AnimatePresence>

                          <motion.div
                            className={`h-4 w-4 rounded-full ${colors.bg} ${colors.glow} ring-4 ring-[#07111f] transition-all`}
                            whileHover={{ scale: 1.3 }}
                            animate={event.isHighlighted ? { boxShadow: [`0 0 10px ${colors.hex}`, `0 0 20px ${colors.hex}`, `0 0 10px ${colors.hex}`] } : {}}
                            transition={{ duration: 1, repeat: event.isHighlighted ? Infinity : 0 }}
                          />
                        </motion.div>
                      ))}
                    </AnimatePresence>

                    <motion.div className="absolute bottom-0 top-0 w-px bg-blue-500" style={{ left: "55%" }} animate={{ opacity: [0.35, 0.8, 0.35] }} transition={{ duration: 2.4, repeat: Infinity }}>
                      <motion.div className="absolute left-1/2 top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-blue-500 ring-4 ring-blue-500/20" animate={{ scale: [1, 1.2, 1] }} transition={{ duration: 2, repeat: Infinity }} />
                    </motion.div>
                  </div>
                </div>
              )
            })}

            <div className="flex items-center border-b border-white/5 px-4 py-4">
              <div className="w-28 shrink-0">
                <span className="text-sm font-medium uppercase text-white">System Pressure</span>
                <div className="mt-1 flex items-center gap-1">
                  <motion.span className="h-2 w-2 rounded-full bg-green-500" animate={{ scale: [1, 1.2, 1] }} transition={{ duration: 2, repeat: Infinity }} />
                  <span className="text-xs font-medium text-green-500">LOW</span>
                </div>
              </div>
              <div className="relative h-8 flex-1 overflow-hidden rounded-full bg-white/5">
                <svg className="h-full w-full" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="pressureGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#22c55e" stopOpacity="0.4" />
                      <stop offset="30%" stopColor="#22c55e" stopOpacity="0.3" />
                      <stop offset="50%" stopColor="#eab308" stopOpacity="0.4" />
                      <stop offset="70%" stopColor="#22c55e" stopOpacity="0.3" />
                      <stop offset="100%" stopColor="#22c55e" stopOpacity="0.4" />
                    </linearGradient>
                  </defs>
                  <rect x="0" y="0" width="100%" height="100%" fill="url(#pressureGradient)" rx="16" />
                </svg>
                <div className="absolute inset-0 flex items-center gap-3 px-4">
                  {pressureDots.map((dot) => (
                    <div key={dot.id} className={`animate-pulse-soft h-2 w-2 rounded-full ${dot.warm ? "bg-yellow-500" : "bg-green-500"}`} style={{ animationDelay: `${dot.id * 0.08}s` }} />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </DraggablePanel>
  )
}
