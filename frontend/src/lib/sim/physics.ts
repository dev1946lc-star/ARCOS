import { Vector3 } from "three"
import type { ArcosMode, NodeEntity } from "@/lib/store/arcos-store"

const repulsionForce = 1.45
const attractionForce = 0.48
const targetForce = 0.62
const damping = 0.9
const maxVelocity = 3.4
const desiredConnectionDistance = 2.8

export function updatePhysics(nodes: NodeEntity[], dt: number, mode: ArcosMode) {
  if (nodes.length === 0) return

  const nodeMap = new Map(nodes.map((node) => [node.id, node]))
  const repulsion = new Vector3()
  const attraction = new Vector3()
  const target = new Vector3()
  const deltaVector = new Vector3()

  for (let index = 0; index < nodes.length; index += 1) {
    const node = nodes[index]

    repulsion.set(0, 0, 0)
    attraction.set(0, 0, 0)
    target.copy(mode === "temporal" ? node.temporalTarget : node.spatialTarget).sub(node.position).multiplyScalar(targetForce)

    for (let otherIndex = 0; otherIndex < nodes.length; otherIndex += 1) {
      if (index === otherIndex) continue
      const other = nodes[otherIndex]
      deltaVector.copy(node.position).sub(other.position)
      const distanceSq = Math.max(deltaVector.lengthSq(), 0.2)
      repulsion.addScaledVector(deltaVector.normalize(), repulsionForce / distanceSq)
    }

    for (const connectionId of node.connections) {
      const connected = nodeMap.get(connectionId)
      if (!connected) continue
      deltaVector.copy(connected.position).sub(node.position)
      const distance = Math.max(deltaVector.length(), 0.001)
      const stretch = distance - desiredConnectionDistance
      attraction.addScaledVector(deltaVector.normalize(), stretch * attractionForce)
    }

    node.velocity.addScaledVector(repulsion, dt)
    node.velocity.addScaledVector(attraction, dt)
    node.velocity.addScaledVector(target, dt)
    node.velocity.multiplyScalar(Math.pow(damping, dt * 60))

    if (node.velocity.lengthSq() > maxVelocity * maxVelocity) {
      node.velocity.setLength(maxVelocity)
    }
  }

  for (const node of nodes) {
    node.position.addScaledVector(node.velocity, dt)
  }
}
