import type {
  EventStream,
  Agent,
  TimelineEvent,
  EventDetail,
  FlowTraceItem,
  SystemInsight,
  EventFeedItem,
} from "./types"

export const eventStreams: EventStream[] = [
  { id: "signals", label: "Signals", count: 1240, enabled: true, color: "#3b82f6" },
  { id: "compute", label: "Compute", count: 890, enabled: true, color: "#f97316" },
  { id: "executions", label: "Executions", count: 2450, enabled: true, color: "#a855f7" },
  { id: "payments", label: "Payments", count: 1130, enabled: true, color: "#06b6d4" },
  { id: "validations", label: "Validations", count: 740, enabled: true, color: "#22c55e" },
]

export const agents: Agent[] = [
  {
    id: "aegis-17",
    name: "Aegis-Node-17",
    role: "Risk Guardian",
    throughput: 1240,
    tpsData: [30, 45, 35, 50, 40, 55, 45],
  },
  {
    id: "flux-03",
    name: "Flux-Core-03",
    role: "Flow Engine",
    throughput: 890,
    tpsData: [20, 35, 25, 40, 30, 45, 35],
  },
  {
    id: "ledger-9",
    name: "Ledger-Weave-9",
    role: "Settlement Mesh",
    throughput: 2450,
    tpsData: [40, 55, 45, 60, 50, 65, 55],
    selected: true,
  },
  {
    id: "throttle-2",
    name: "Throttle-Gate-2",
    role: "Backpressure Ctrl",
    throughput: 310,
    tpsData: [15, 20, 18, 25, 20, 28, 22],
  },
]

export const timelineEvents: Record<string, TimelineEvent[]> = {
  signals: [
    { id: "s1", type: "signals", title: "Arbitrage Signal Detected", timestamp: "13:33:21", x: 15, showLabel: true, isHighlighted: false },
    { id: "s2", type: "signals", title: "Market Regime Shift", timestamp: "13:36:10", x: 40, showLabel: true, isHighlighted: false },
    { id: "s3", type: "signals", title: "Opportunity Cluster", timestamp: "13:38:55", x: 65, showLabel: true, isHighlighted: false },
  ],
  compute: [
    { id: "c1", type: "compute", title: "Model Inference Completed", timestamp: "13:33:45", x: 18, showLabel: true, isHighlighted: false },
    { id: "c2", type: "compute", title: "Risk Simulation Completed", timestamp: "13:36:33", x: 43, showLabel: true, isHighlighted: false },
    { id: "c3", type: "compute", title: "Strategy Batch Generated", timestamp: "13:38:41", x: 63, showLabel: true, isHighlighted: false },
  ],
  executions: [
    { id: "e1", type: "executions", title: "Order Batch Submitted", timestamp: "13:34:02", x: 20, showLabel: true, isHighlighted: false },
    { id: "e2", type: "executions", title: "Trade Execution Confirmed", timestamp: "13:37:05", x: 48, showLabel: true, isHighlighted: true },
    { id: "e3", type: "executions", title: "Position Hedged", timestamp: "13:39:11", x: 68, showLabel: true, isHighlighted: false },
  ],
  payments: [
    { id: "p1", type: "payments", title: "Payment Initiated", subtitle: "$12,450", timestamp: "13:34:18", x: 22, showLabel: true, isHighlighted: false },
    { id: "p2", type: "payments", title: "Settlement Completed", timestamp: "13:37:19", x: 50, showLabel: true, isHighlighted: false },
    { id: "p3", type: "payments", title: "Fee Distributed", subtitle: "$145.30", timestamp: "13:39:28", x: 70, showLabel: true, isHighlighted: false },
  ],
  validations: [
    { id: "v1", type: "validations", title: "Trade Validated", timestamp: "13:34:08", x: 21, showLabel: true, isHighlighted: false },
    { id: "v2", type: "validations", title: "Compliance Check Passed", timestamp: "13:36:58", x: 46, showLabel: true, isHighlighted: false },
    { id: "v3", type: "validations", title: "State Root Committed", timestamp: "13:39:35", x: 72, showLabel: true, isHighlighted: false },
  ],
}

export const eventDetail: EventDetail = {
  title: "Trade Execution Confirmed",
  type: "Trade Execution",
  timestamp: "13:37:05.342",
  timeAgo: "2m 37s ago",
  agent: "Exec-Core-03",
  tradeType: "Trade Execution",
  status: "success",
  amount: "$12,450.00",
  pair: "ETH / USDC",
  price: "3,245.67",
  networkFee: "$0.1453",
  txHash: "0x7f3a...9b2c",
}

export const flowTrace: FlowTraceItem[] = [
  { id: "ft1", type: "signals", title: "Arbitrage Signal Detected", timestamp: "13:33:21", status: "success" },
  { id: "ft2", type: "compute", title: "Model Inference Completed", timestamp: "13:33:45", status: "success" },
  { id: "ft3", type: "executions", title: "Trade Execution Confirmed", timestamp: "13:37:05", status: "active" },
  { id: "ft4", type: "payments", title: "Payment Initiated", timestamp: "13:37:19", status: "pending" },
  { id: "ft5", type: "validations", title: "Trade Validated", timestamp: "13:34:08", status: "success" },
]

export const systemInsights: SystemInsight[] = [
  { type: "info", message: "Execution throughput increased 38% in the last 5 minutes" },
  { type: "warning", message: "Backpressure detected between Compute → Executions" },
  { type: "success", message: "All system validations are healthy" },
]

export const eventFeed: EventFeedItem[] = [
  { timestamp: "13:42:01", message: "Throttle-Gate-2 reported 3 dropped transactions", type: "error" },
  { timestamp: "13:41:19", message: "Ledger-Weave-9 latency surge +12ms", type: "warning" },
  { timestamp: "13:40:33", message: "New connecting stream: Market-A ↔ Flux-Core-03", type: "info" },
  { timestamp: "13:39:11", message: "Error burst cleared on Node-17", type: "success" },
]

export const throughputData = [
  { time: "13:30", signals: 1100, compute: 800, executions: 2200, payments: 1000, validations: 650 },
  { time: "13:32", signals: 1150, compute: 820, executions: 2300, payments: 1050, validations: 680 },
  { time: "13:34", signals: 1180, compute: 850, executions: 2350, payments: 1080, validations: 700 },
  { time: "13:36", signals: 1200, compute: 870, executions: 2400, payments: 1100, validations: 720 },
  { time: "13:38", signals: 1220, compute: 880, executions: 2420, payments: 1120, validations: 730 },
  { time: "13:40", signals: 1240, compute: 890, executions: 2450, payments: 1130, validations: 740 },
]

export const valueStreamsData = [
  { time: "0", signals: 1000, compute: 700, payments: 2000, executions: 900 },
  { time: "1", signals: 1100, compute: 750, payments: 2100, executions: 950 },
  { time: "2", signals: 1050, compute: 800, payments: 2200, executions: 1000 },
  { time: "3", signals: 1150, compute: 820, payments: 2300, executions: 1050 },
  { time: "4", signals: 1200, compute: 850, payments: 2400, executions: 1100 },
  { time: "5", signals: 1240, compute: 890, payments: 2450, executions: 1130 },
]

export const eventSummary = {
  total: 6450,
  breakdown: [
    { name: "Signals", value: 1240, percentage: 19, color: "#3b82f6" },
    { name: "Compute", value: 890, percentage: 14, color: "#f97316" },
    { name: "Executions", value: 2450, percentage: 38, color: "#a855f7" },
    { name: "Payments", value: 1130, percentage: 18, color: "#06b6d4" },
    { name: "Validations", value: 740, percentage: 11, color: "#22c55e" },
  ],
}

export const latencyData = [
  { time: "0", value: 25 },
  { time: "1", value: 28 },
  { time: "2", value: 26 },
  { time: "3", value: 30 },
  { time: "4", value: 27 },
  { time: "5", value: 28 },
]

export const systemHealth = {
  nodesOnline: "94 / 102",
  packetSuccess: "99.89%",
  queueUtilization: "38%",
  uptime: "7D 14H 22M",
}
