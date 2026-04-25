"use client"

import { useMemo, useRef } from "react"
import { useFrame } from "@react-three/fiber"
import { AdditiveBlending, BufferAttribute, Points, PointsMaterial } from "three"
import { useArcosSimStore, type NodeType } from "@/lib/store/arcos-store"

const typeOrder: NodeType[] = ["signals", "compute", "execution", "payments", "validation"]
const laneY: Record<NodeType, number> = { signals: 3.4, compute: 1.7, execution: 0, payments: -1.7, validation: -3.4 }
const colors: Record<NodeType, [number, number, number]> = {
  signals: [0.23, 0.51, 0.96], compute: [0.66, 0.33, 0.97], execution: [0.98, 0.45, 0.13],
  payments: [0.13, 0.82, 0.93], validation: [0.13, 0.77, 0.37],
}

export function TemporalField() {
  const pointsRef = useRef<Points>(null)
  const materialRef = useRef<PointsMaterial>(null)
  const elapsedRef = useRef(0)
  const particleCount = 720

  const { basePositions, livePositions, colorArray } = useMemo(() => {
    const base = new Float32Array(particleCount * 3)
    const live = new Float32Array(particleCount * 3)
    const color = new Float32Array(particleCount * 3)
    for (let i = 0; i < particleCount; i++) {
      const type = typeOrder[i % typeOrder.length]
      const x = -8 + (i / particleCount) * 16 + (Math.random() - 0.5) * 2
      const y = laneY[type] + (Math.random() - 0.5) * 0.9
      const z = (Math.random() - 0.5) * 8.5
      base[i * 3] = x; base[i * 3 + 1] = y; base[i * 3 + 2] = z
      live[i * 3] = x; live[i * 3 + 1] = y; live[i * 3 + 2] = z
      color[i * 3] = colors[type][0]; color[i * 3 + 1] = colors[type][1]; color[i * 3 + 2] = colors[type][2]
    }
    return { basePositions: base, livePositions: live, colorArray: color }
  }, [])

  useFrame((_, delta) => {
    const { mode } = useArcosSimStore.getState()
    const material = materialRef.current
    const points = pointsRef.current
    if (!material || !points) return
    const targetOpacity = mode === "temporal" ? 0.74 : 0.2
    material.opacity += (targetOpacity - material.opacity) * Math.min(1, delta * 2.8)
    const posAttr = points.geometry.getAttribute("position") as BufferAttribute
    elapsedRef.current += delta
    const t = elapsedRef.current
    for (let i = 0; i < particleCount; i++) {
      const j = i * 3
      livePositions[j] = basePositions[j] + Math.sin(t * 0.45 + i * 0.35) * 0.18
      livePositions[j + 1] = basePositions[j + 1] + Math.cos(t * 0.7 + i * 0.2) * 0.12
      livePositions[j + 2] = basePositions[j + 2] + Math.sin(t * 0.55 + i * 0.41) * 0.24
    }
    posAttr.needsUpdate = true
  })

  return (
    <group>
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[livePositions, 3]} />
          <bufferAttribute attach="attributes-color" args={[colorArray, 3]} />
        </bufferGeometry>
        <pointsMaterial ref={materialRef} size={0.065} transparent opacity={0.18} depthWrite={false} vertexColors blending={AdditiveBlending} />
      </points>
    </group>
  )
}
