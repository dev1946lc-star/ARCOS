import { Vector3 } from "three"
import type { NodeType } from "@/lib/store/arcos-store"

interface LayoutNode {
  id: string
  type: NodeType
}

const typeOrder: NodeType[] = ["signals", "compute", "execution", "payments", "validation"]

const typeConfig: Record<NodeType, { anchor: [number, number, number]; radius: number; arcOffset: number }> = {
  signals: { anchor: [-0.85, 3.2, 1.4], radius: 1.15, arcOffset: 0.25 },
  compute: { anchor: [-3.7, -0.2, 0.5], radius: 1.05, arcOffset: 1.6 },
  execution: { anchor: [3.65, 2.95, 1.25], radius: 1.12, arcOffset: -0.45 },
  payments: { anchor: [-0.3, -3.75, -0.55], radius: 1.18, arcOffset: 0.85 },
  validation: { anchor: [4.05, -1.55, 0.75], radius: 0.92, arcOffset: -1.25 },
}

export function getSpatialTarget(node: LayoutNode, index = 0, total = 1) {
  const ringIndex = typeOrder.indexOf(node.type)
  const config = typeConfig[node.type]
  const angularStep = (Math.PI * 2) / Math.max(total, 1)
  const angle = config.arcOffset + index * angularStep * 0.76
  const radius = config.radius + ((index % 2 === 0 ? 1 : -1) * 0.12 + ringIndex * 0.03)

  return new Vector3(
    config.anchor[0] + Math.cos(angle) * radius,
    config.anchor[1] + Math.sin(angle * 1.25) * (0.72 + ringIndex * 0.04),
    config.anchor[2] + Math.sin(angle) * radius * 0.8,
  )
}

export function getTemporalTarget(node: LayoutNode, typeIndex = 0, typeCount = 1) {
  const laneIndex = typeOrder.indexOf(node.type)
  const x = -6 + (typeIndex / Math.max(typeCount - 1, 1)) * 12
  const y = 3.4 - laneIndex * 1.75
  const z = (laneIndex % 2 === 0 ? -1 : 1) * (0.6 + (typeIndex % 3) * 0.22)

  return new Vector3(x, y, z)
}
