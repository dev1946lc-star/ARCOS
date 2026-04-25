export type ViewMode = "spatial" | "temporal"

export type EventType = "signals" | "compute" | "executions" | "payments" | "validations"

export interface EventStream {
  id: EventType
  label: string
  count: number
  enabled: boolean
  color: string
}

export interface Agent {
  id: string
  name: string
  role: string
  throughput: number
  tpsData: number[]
  selected?: boolean
}

export interface TimelineEvent {
  id: string
  type: EventType
  title: string
  subtitle?: string
  timestamp: string
  x: number
  showLabel?: boolean
  isHighlighted?: boolean
}

export interface EventDetail {
  title: string
  type: string
  timestamp: string
  timeAgo: string
  agent: string
  tradeType: string
  status: "success" | "pending" | "error"
  amount: string
  pair: string
  price: string
  networkFee: string
  txHash: string
}

export interface FlowTraceItem {
  id: string
  type: EventType
  title: string
  timestamp: string
  status: "success" | "pending" | "error" | "active"
}

export interface SystemInsight {
  type: "info" | "warning" | "success"
  message: string
}

export interface EventFeedItem {
  timestamp: string
  message: string
  type: "error" | "warning" | "info" | "success"
}

// Panel layout persistence
export interface PanelPosition {
  x: number
  y: number
  width: number
  height: number
  collapsed: boolean
}

export interface PanelLayout {
  [panelId: string]: PanelPosition
}

// Backend data types
export interface BackendStats {
  total_transactions: number
  active_agents: number
  pending_jobs: number
  completed_jobs: number
  tx_per_second: number
  avg_settlement_time: number
  success_rate: number
  leaderboard: Array<{ id: string; total_profit: number; acceptance_rate: number }>
  top_agent: string | null
}

export interface BackendAgent {
  id: string
  personality: string
  total_profit: number
  acceptance_rate: number
  risk_level: string
  win_rate: number
  recent_trend: string
}

export interface SystemHealth {
  active_agents: number
  queue_size: number
  queue_utilization: number
  tx_per_second: number
  persistence_lag_ms: number
  mode: string
  supabase_status: string
}

export interface EconomicsComparison {
  arcos_cost: number
  traditional_cost: number
  savings_factor: number
  transactions: number
}
