"use client"

import { useMemo, useRef } from "react"
import { useFrame } from "@react-three/fiber"
import { AdditiveBlending, CatmullRomCurve3, Color, InstancedMesh, Matrix4, Object3D, Vector3 } from "three"
import { useArcosSimStore, type NodeType } from "@/lib/store/arcos-store"

const typeColorMap: Record<NodeType, string> = {
  signals: "#3b82f6",
  compute: "#a855f7",
  execution: "#f97316",
  payments: "#22d3ee",
  validation: "#22c55e",
}
const trailSegments = 3

export function Flows() {
  const flows = useArcosSimStore((state) => state.flows)
  const meshRef = useRef<InstancedMesh>(null)
  const tempObject = useMemo(() => new Object3D(), [])
  const tempMatrix = useMemo(() => new Matrix4(), [])
  const source = useMemo(() => new Vector3(), [])
  const target = useMemo(() => new Vector3(), [])
  const lift = useMemo(() => new Vector3(), [])
  const mid = useMemo(() => new Vector3(), [])
  const startControl = useMemo(() => new Vector3(), [])
  const endControl = useMemo(() => new Vector3(), [])
  const color = useMemo(() => new Color(), [])

  useFrame((_, delta) => {
    const { nodes } = useArcosSimStore.getState()
    const nodeMap = new Map(nodes.map((node) => [node.id, node]))
    const mesh = meshRef.current

    if (!mesh) return

    flows.forEach((flow, flowIndex) => {
      const sourceNode = nodeMap.get(flow.sourceId)
      const targetNode = nodeMap.get(flow.targetId)

      if (!sourceNode || !targetNode) {
        tempObject.position.set(9999, 9999, 9999)
        tempObject.scale.setScalar(0.0001)
        tempObject.updateMatrix()
        for (let trailIndex = 0; trailIndex < trailSegments; trailIndex += 1) {
          mesh.setMatrixAt(flowIndex * trailSegments + trailIndex, tempObject.matrix)
        }
        return
      }

      flow.progress = (flow.progress + flow.speed * delta) % 1

      source.copy(sourceNode.position)
      target.copy(targetNode.position)
      mid.copy(source).lerp(target, 0.5)
      lift.set(0, 0.7 + source.distanceTo(target) * 0.15, 0)
      startControl.copy(mid).lerp(source, 0.45).add(lift)
      endControl.copy(mid).lerp(target, 0.45).add(lift)

      const curve = new CatmullRomCurve3([source.clone(), startControl.clone(), endControl.clone(), target.clone()])
      for (let trailIndex = 0; trailIndex < trailSegments; trailIndex += 1) {
        const progress = (flow.progress - trailIndex * 0.045 + 1) % 1
        const point = curve.getPoint(progress)
        const tangent = curve.getTangent(progress).normalize()
        const scale = (0.12 + sourceNode.activity * 0.09) * (1 - trailIndex * 0.18)

        tempObject.position.copy(point)
        tempObject.scale.setScalar(scale)
        tempObject.lookAt(point.clone().add(tangent))
        tempObject.updateMatrix()
        tempMatrix.copy(tempObject.matrix)
        mesh.setMatrixAt(flowIndex * trailSegments + trailIndex, tempMatrix)

        color.set(typeColorMap[sourceNode.type]).lerp(new Color("#ffffff"), trailIndex === 0 ? 0.22 : 0.08)
        mesh.setColorAt(flowIndex * trailSegments + trailIndex, color)
      }
    })

    mesh.instanceMatrix.needsUpdate = true
    if (mesh.instanceColor) {
      mesh.instanceColor.needsUpdate = true
    }
  })

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, flows.length * trailSegments]} frustumCulled={false}>
      <sphereGeometry args={[0.12, 14, 14]} />
      <meshBasicMaterial color="#ffffff" transparent opacity={0.98} depthWrite={false} blending={AdditiveBlending} />
    </instancedMesh>
  )
}
