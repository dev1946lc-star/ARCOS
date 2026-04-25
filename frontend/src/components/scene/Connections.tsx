"use client"

import { useMemo, useRef } from "react"
import { useFrame } from "@react-three/fiber"
import { AdditiveBlending, BufferAttribute, BufferGeometry, CatmullRomCurve3, LineBasicMaterial, Vector3 } from "three"
import { useArcosSimStore } from "@/lib/store/arcos-store"

const samples = 18

export function Connections() {
  const nodes = useArcosSimStore((state) => state.nodes)
  const pairs = useMemo(() => {
    const seen = new Set<string>()
    return nodes.flatMap((node) =>
      node.connections
        .filter((targetId) => {
          const key = [node.id, targetId].sort().join(":")
          if (seen.has(key)) return false
          seen.add(key)
          return true
        })
        .map((targetId) => ({ sourceId: node.id, targetId })),
    )
  }, [nodes])

  const geometryRefs = useRef<Array<BufferGeometry | null>>([])
  const materialRefs = useRef<Array<LineBasicMaterial | null>>([])
  const glowMaterialRefs = useRef<Array<LineBasicMaterial | null>>([])
  const pointA = useMemo(() => new Vector3(), [])
  const pointB = useMemo(() => new Vector3(), [])
  const mid = useMemo(() => new Vector3(), [])
  const lift = useMemo(() => new Vector3(), [])
  const startControl = useMemo(() => new Vector3(), [])
  const endControl = useMemo(() => new Vector3(), [])

  useFrame((_, delta) => {
    const { nodes: currentNodes, mode } = useArcosSimStore.getState()
    const nodeMap = new Map(currentNodes.map((node) => [node.id, node]))

    pairs.forEach((pair, index) => {
      const geometry = geometryRefs.current[index]
      const material = materialRefs.current[index]
      const glowMaterial = glowMaterialRefs.current[index]
      const source = nodeMap.get(pair.sourceId)
      const target = nodeMap.get(pair.targetId)

      if (!geometry || !material || !glowMaterial || !source || !target) return

      pointA.copy(source.position)
      pointB.copy(target.position)
      mid.copy(pointA).lerp(pointB, 0.5)
      lift.set(0, 0.55 + pointA.distanceTo(pointB) * 0.12, mode === "temporal" ? 0.35 : 0.8)
      startControl.copy(mid).lerp(pointA, 0.4).add(lift)
      endControl.copy(mid).lerp(pointB, 0.4).add(lift)

      const curve = new CatmullRomCurve3([pointA.clone(), startControl.clone(), endControl.clone(), pointB.clone()])
      const attribute = geometry.getAttribute("position") as BufferAttribute
      const array = attribute.array as Float32Array

      for (let sampleIndex = 0; sampleIndex < samples; sampleIndex += 1) {
        const samplePoint = curve.getPoint(sampleIndex / (samples - 1))
        const offset = sampleIndex * 3
        array[offset] = samplePoint.x
        array[offset + 1] = samplePoint.y
        array[offset + 2] = samplePoint.z
      }

      attribute.needsUpdate = true
      const activity = (source.activity + target.activity) * 0.5
      const targetOpacity = (mode === "temporal" ? 0.24 : 0.6) * activity
      material.opacity += (targetOpacity - material.opacity) * Math.min(1, delta * 3.2)
      glowMaterial.opacity += (((mode === "temporal" ? 0.1 : 0.26) * activity) - glowMaterial.opacity) * Math.min(1, delta * 3.2)
      const color = mode === "temporal" ? "#8b5cf6" : "#60a5fa"
      material.color.set(color)
      glowMaterial.color.set(color)
    })
  })

  return (
    <group>
      {pairs.map((pair, index) => (
        <group key={`${pair.sourceId}-${pair.targetId}`}>
          <line>
            <bufferGeometry ref={(geometry) => (geometryRefs.current[index] = geometry)}>
              <bufferAttribute attach="attributes-position" args={[new Float32Array(samples * 3), 3]} />
            </bufferGeometry>
            <lineBasicMaterial
              ref={(material) => (glowMaterialRefs.current[index] = material)}
              color="#7dd3fc"
              transparent
              opacity={0.16}
              blending={AdditiveBlending}
              depthWrite={false}
            />
          </line>
          <line>
            <bufferGeometry>
              <bufferAttribute attach="attributes-position" args={[new Float32Array(samples * 3), 3]} />
            </bufferGeometry>
            <lineBasicMaterial
              ref={(material) => (materialRefs.current[index] = material)}
              color="#7dd3fc"
              transparent
              opacity={0.24}
              blending={AdditiveBlending}
              depthWrite={false}
            />
          </line>
        </group>
      ))}
    </group>
  )
}
