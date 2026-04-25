"use client"

import { Vector3 } from "three"
import { create } from "zustand"
import { getSpatialTarget, getTemporalTarget } from "@/lib/sim/layouts"
import { fetchStats, fetchSystemHealth, fetchEconomicsComparison, fetchAgentsLeaderboard } from "@/lib/api"
import { connectWebSocket } from "@/lib/websocket"
import type { PanelLayout } from "@/lib/types"

export type ArcosMode = "spatial" | "temporal"
export type StreamStatus = "live" | "paused"
export type NodeType = "signals" | "compute" | "execution" | "payments" | "validation"

export interface NodeEntity {
  id: string
  type: NodeType
  position: Vector3
  velocity: Vector3
  spatialTarget: Vector3
  temporalTarget: Vector3
  activity: number
  connections: string[]
}

export interface FlowEntity {
  id: string
  sourceId: string
  targetId: string
  progress: number
  speed: number
}

interface LiveMetrics {
  tps: number
  latency: number
  totalTransactions: number
  activeAgents: number
  queueSize: number
  queueUtilization: number
  savingsFactor: number
  arcosCost: number
  traditionalCost: number
  topAgent: string | null
  leaderboard: Array<Record<string, unknown>>
  recentEvents: Array<Record<string, unknown>>
  backendConnected: boolean
}

interface ArcosSimState {
  mode: ArcosMode
  nodes: NodeEntity[]
  flows: FlowEntity[]
  selectedEntity: string | null
  streamStatus: StreamStatus
  ambientPulse: number
  panelLayout: PanelLayout
  liveMetrics: LiveMetrics
  wsConnection: { disconnect: () => void } | null
  setMode: (mode: ArcosMode) => void
  selectEntity: (id: string | null) => void
  setStreamStatus: (status: StreamStatus) => void
  updatePanelLayout: (panelId: string, position: Partial<PanelLayout[string]>) => void
  resetPanelLayout: () => void
  initBackend: () => void
  cleanupBackend: () => void
}

function createNode(
  id: string,
  type: NodeType,
  index: number,
  total: number,
  typeIndex: number,
  typeCount: number,
  activity: number,
  connections: string[],
): NodeEntity {
  const spatialTarget = getSpatialTarget({ id, type }, index, total)
  const temporalTarget = getTemporalTarget({ id, type }, typeIndex, typeCount)
  const position = spatialTarget
    .clone()
    .multiplyScalar(1.18)
    .add(new Vector3((index % 2 === 0 ? 1 : -1) * 0.35, 0.22 - (index % 3) * 0.11, 0.28 - (index % 4) * 0.14))

  return {
    id,
    type,
    position,
    velocity: new Vector3(),
    spatialTarget,
    temporalTarget,
    activity,
    connections,
  }
}

function createInitialNodes(): NodeEntity[] {
  const seeds: Array<Pick<NodeEntity, "id" | "type" | "activity" | "connections">> = [
    { id: "signal-01", type: "signals", activity: 0.72, connections: ["compute-01", "compute-02"] },
    { id: "signal-02", type: "signals", activity: 0.61, connections: ["compute-02", "compute-03"] },
    { id: "signal-03", type: "signals", activity: 0.58, connections: ["compute-03", "execution-01"] },
    { id: "compute-01", type: "compute", activity: 0.83, connections: ["signal-01", "execution-01"] },
    { id: "compute-02", type: "compute", activity: 0.75, connections: ["signal-01", "signal-02", "execution-02"] },
    { id: "compute-03", type: "compute", activity: 0.69, connections: ["signal-02", "signal-03", "execution-03"] },
    { id: "execution-01", type: "execution", activity: 0.91, connections: ["compute-01", "signal-03", "payments-01"] },
    { id: "execution-02", type: "execution", activity: 0.88, connections: ["compute-02", "payments-02"] },
    { id: "execution-03", type: "execution", activity: 0.79, connections: ["compute-03", "payments-03"] },
    { id: "payments-01", type: "payments", activity: 0.67, connections: ["execution-01", "validation-01"] },
    { id: "payments-02", type: "payments", activity: 0.56, connections: ["execution-02", "validation-02"] },
    { id: "payments-03", type: "payments", activity: 0.62, connections: ["execution-03", "validation-03"] },
    { id: "validation-01", type: "validation", activity: 0.74, connections: ["payments-01"] },
    { id: "validation-02", type: "validation", activity: 0.64, connections: ["payments-02"] },
    { id: "validation-03", type: "validation", activity: 0.7, connections: ["payments-03"] },
  ]

  return seeds.map((seed, index) =>
    createNode(
      seed.id,
      seed.type,
      index,
      seeds.length,
      seeds.filter((c) => c.type === seed.type).findIndex((c) => c.id === seed.id),
      seeds.filter((c) => c.type === seed.type).length,
      seed.activity,
      seed.connections,
    ),
  )
}

function createInitialFlows(): FlowEntity[] {
  return [
    { id: "flow-01", sourceId: "signal-01", targetId: "compute-01", progress: 0.12, speed: 0.22 },
    { id: "flow-02", sourceId: "signal-02", targetId: "compute-02", progress: 0.48, speed: 0.18 },
    { id: "flow-03", sourceId: "compute-01", targetId: "execution-01", progress: 0.2, speed: 0.27 },
    { id: "flow-04", sourceId: "compute-03", targetId: "execution-03", progress: 0.74, speed: 0.24 },
    { id: "flow-05", sourceId: "execution-02", targetId: "payments-02", progress: 0.33, speed: 0.31 },
    { id: "flow-06", sourceId: "payments-03", targetId: "validation-03", progress: 0.58, speed: 0.2 },
    { id: "flow-07", sourceId: "signal-03", targetId: "execution-01", progress: 0.86, speed: 0.29 },
    { id: "flow-08", sourceId: "payments-01", targetId: "validation-01", progress: 0.42, speed: 0.17 },
    { id: "flow-09", sourceId: "signal-01", targetId: "compute-02", progress: 0.66, speed: 0.2 },
    { id: "flow-10", sourceId: "signal-02", targetId: "compute-03", progress: 0.1, speed: 0.24 },
    { id: "flow-11", sourceId: "compute-02", targetId: "execution-02", progress: 0.27, speed: 0.26 },
    { id: "flow-12", sourceId: "execution-01", targetId: "payments-01", progress: 0.51, speed: 0.19 },
    { id: "flow-13", sourceId: "execution-03", targetId: "payments-03", progress: 0.79, speed: 0.23 },
    { id: "flow-14", sourceId: "payments-02", targetId: "validation-02", progress: 0.14, speed: 0.16 },
    { id: "flow-15", sourceId: "compute-01", targetId: "execution-01", progress: 0.61, speed: 0.3 },
    { id: "flow-16", sourceId: "payments-03", targetId: "validation-03", progress: 0.87, speed: 0.18 },
  ]
}

const DEFAULT_PANEL_LAYOUT: PanelLayout = {}

function loadPanelLayout(): PanelLayout {
  if (typeof window === "undefined") return DEFAULT_PANEL_LAYOUT
  try {
    const stored = localStorage.getItem("arcos-panel-layout")
    return stored ? JSON.parse(stored) : DEFAULT_PANEL_LAYOUT
  } catch {
    return DEFAULT_PANEL_LAYOUT
  }
}

function savePanelLayout(layout: PanelLayout) {
  if (typeof window === "undefined") return
  try {
    localStorage.setItem("arcos-panel-layout", JSON.stringify(layout))
  } catch {
    // ignore
  }
}

const defaultMetrics: LiveMetrics = {
  tps: 4820,
  latency: 28,
  totalTransactions: 0,
  activeAgents: 0,
  queueSize: 0,
  queueUtilization: 0.38,
  savingsFactor: 24188,
  arcosCost: 0.00000024,
  traditionalCost: 0.005789,
  topAgent: null,
  leaderboard: [],
  recentEvents: [],
  backendConnected: false,
}

export const useArcosSimStore = create<ArcosSimState>((set, get) => ({
  mode: "spatial",
  nodes: createInitialNodes(),
  flows: createInitialFlows(),
  selectedEntity: null,
  streamStatus: "live",
  ambientPulse: 0.32,
  panelLayout: loadPanelLayout(),
  liveMetrics: defaultMetrics,
  wsConnection: null,

  setMode: (mode) => set({ mode }),
  selectEntity: (id) => set({ selectedEntity: id }),
  setStreamStatus: (status) => set({ streamStatus: status }),

  updatePanelLayout: (panelId, position) => {
    const current = get().panelLayout
    const updated = { ...current, [panelId]: { ...current[panelId], ...position } }
    savePanelLayout(updated)
    set({ panelLayout: updated })
  },

  resetPanelLayout: () => {
    savePanelLayout(DEFAULT_PANEL_LAYOUT)
    set({ panelLayout: DEFAULT_PANEL_LAYOUT })
  },

  initBackend: () => {
    // Fetch initial data
    const poll = async () => {
      try {
        const [stats, health, comparison, leaderboard] = await Promise.allSettled([
          fetchStats(),
          fetchSystemHealth(),
          fetchEconomicsComparison(),
          fetchAgentsLeaderboard(),
        ])

        const statsData = stats.status === "fulfilled" ? stats.value : {}
        const healthData = health.status === "fulfilled" ? health.value : {}
        const comparisonData = comparison.status === "fulfilled" ? comparison.value : {}
        const leaderboardData = leaderboard.status === "fulfilled" ? leaderboard.value : { leaderboard: [] }

        set((state) => {
          const currentNodes = [...state.nodes];
          const newAgents = (leaderboardData.leaderboard as Array<{id: string}>) || [];
          let nodesChanged = false;

          // Dynamically spawn new agents when they appear in the leaderboard (e.g. during a load spike)
          for (const agent of newAgents) {
            if (!currentNodes.find(n => n.id === agent.id)) {
              const computeNodes = currentNodes.filter(n => n.type === "compute");
              const newIndex = currentNodes.length;
              
              currentNodes.push(createNode(
                agent.id,
                "compute",
                newIndex,
                newIndex + 1, // approximate total
                computeNodes.length,
                computeNodes.length + 1,
                0.8,
                ["signal-01", "execution-01"] // default connections for new dynamic agents
              ));
              nodesChanged = true;
            }
          }

          // If load is high, ramp up activity
          const queueUtil = Number(healthData.queue_utilization || state.liveMetrics.queueUtilization);
          if (queueUtil > 0.5) {
            currentNodes.forEach(n => {
              if (Math.random() > 0.7) n.activity = Math.min(1, n.activity + 0.2);
            });
            nodesChanged = true;
          }

          return {
            nodes: nodesChanged ? currentNodes : state.nodes,
            liveMetrics: {
              ...state.liveMetrics,
              tps: Number(statsData.tx_per_second || healthData.tx_per_second || state.liveMetrics.tps),
              latency: Number(healthData.persistence_lag_ms || state.liveMetrics.latency),
              totalTransactions: Number(statsData.total_transactions || state.liveMetrics.totalTransactions),
              activeAgents: Number(statsData.active_agents || healthData.active_agents || state.liveMetrics.activeAgents),
              queueSize: Number(healthData.queue_size || state.liveMetrics.queueSize),
              queueUtilization: queueUtil,
              savingsFactor: Number(comparisonData.savings_factor || state.liveMetrics.savingsFactor),
              arcosCost: Number(comparisonData.arcos_total_cost || state.liveMetrics.arcosCost),
              traditionalCost: Number(comparisonData.traditional_total_cost || state.liveMetrics.traditionalCost),
              topAgent: (statsData.top_agent as string) || state.liveMetrics.topAgent,
              leaderboard: (leaderboardData.leaderboard as Array<Record<string, unknown>>) || state.liveMetrics.leaderboard,
              backendConnected: true,
            },
          }
        })
      } catch {
        set((state) => ({
          liveMetrics: { ...state.liveMetrics, backendConnected: false },
        }))
      }
    }

    poll()
    const intervalId = setInterval(poll, 5000)

    // Connect WebSocket
    const wsConn = connectWebSocket((event) => {
      set((state) => ({
        liveMetrics: {
          ...state.liveMetrics,
          recentEvents: [event, ...state.liveMetrics.recentEvents].slice(0, 50),
          backendConnected: true,
        },
      }))

      // Pulse activity on WebSocket events
      const eventType = event.event_type as string
      if (eventType) {
        set((state) => ({
          ambientPulse: Math.min(1, state.ambientPulse * 0.45 + 0.55),
        }))
      }
    })

    set({ wsConnection: wsConn })

    // Store interval for cleanup
    ;(globalThis as Record<string, unknown>).__arcosInterval = intervalId
  },

  cleanupBackend: () => {
    const state = get()
    state.wsConnection?.disconnect()
    const intervalId = (globalThis as Record<string, unknown>).__arcosInterval as ReturnType<typeof setInterval>
    if (intervalId) clearInterval(intervalId)
    set({ wsConnection: null })
  },
}))
