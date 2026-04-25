"use client"

import { useEffect, useMemo, useRef } from "react"
import { Bloom, EffectComposer } from "@react-three/postprocessing"
import { useFrame, Canvas } from "@react-three/fiber"
import { AdditiveBlending, BufferAttribute, Group, MeshBasicMaterial, Object3D, Points, PointsMaterial } from "three"
import { useArcosSimStore } from "@/lib/store/arcos-store"
import { updatePhysics } from "@/lib/sim/physics"
import { createSimulationStream } from "@/lib/sim/stream"
import { CameraController } from "./CameraController"
import { Connections } from "./Connections"
import { Flows } from "./Flows"
import { Nodes } from "./Nodes"
import { SystemCore } from "./SystemCore"
import { TemporalField } from "./TemporalField"

function AmbientField() {
  const pointsRef = useRef<Points>(null)
  const materialRef = useRef<PointsMaterial>(null)
  const elapsedRef = useRef(0)
  const particleCount = 960
  const { positions, colors } = useMemo(() => {
    const pos = new Float32Array(particleCount * 3)
    const col = new Float32Array(particleCount * 3)
    const palette = [
      [0.37, 0.64, 1],
      [0.73, 0.44, 1],
      [0.15, 0.84, 0.93],
      [0.99, 0.55, 0.17],
    ]

    for (let index = 0; index < particleCount; index += 1) {
      const i = index * 3
      pos[i] = (Math.random() - 0.5) * 28
      pos[i + 1] = (Math.random() - 0.5) * 18
      pos[i + 2] = (Math.random() - 0.5) * 16 - 2
      const color = palette[index % palette.length]
      col[i] = color[0]
      col[i + 1] = color[1]
      col[i + 2] = color[2]
    }

    return { positions: pos, colors: col }
  }, [])

  useFrame((_, delta) => {
    elapsedRef.current += delta
    const points = pointsRef.current
    const material = materialRef.current
    if (!points || !material) return

    material.opacity = 0.18 + Math.sin(elapsedRef.current * 0.2) * 0.016
    const attribute = points.geometry.getAttribute("position") as BufferAttribute
    const array = attribute.array as Float32Array
    for (let index = 0; index < particleCount; index += 1) {
      const i = index * 3
      array[i] += Math.sin(elapsedRef.current * 0.05 + index) * 0.00045
      array[i + 1] += Math.cos(elapsedRef.current * 0.04 + index * 1.3) * 0.00035
    }
    attribute.needsUpdate = true
  })

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial
        ref={materialRef}
        size={0.034}
        transparent
        opacity={0.18}
        depthWrite={false}
        vertexColors
        blending={AdditiveBlending}
      />
    </points>
  )
}

function SceneRuntime() {
  const systemGroupRef = useRef<Group>(null)
  const systemCoreRef = useRef<Group>(null)
  const nodeRefs = useRef(new Map<string, Object3D>())
  const streamRef = useRef<ReturnType<typeof createSimulationStream> | null>(null)
  const elapsedRef = useRef(0)

  useEffect(() => {
    streamRef.current = createSimulationStream()
    streamRef.current.start()

    return () => {
      streamRef.current?.stop()
      streamRef.current = null
    }
  }, [])

  useFrame((_, delta) => {
    const { mode, nodes } = useArcosSimStore.getState()
    const clampedDelta = Math.min(delta, 1 / 30)
    elapsedRef.current += clampedDelta
    const time = elapsedRef.current

    updatePhysics(nodes, clampedDelta, mode)

    nodes.forEach((node) => {
      node.position.x += Math.sin(time * 0.6 + node.activity * 5) * 0.0016
      node.position.y += Math.cos(time * 0.45 + node.activity * 4) * 0.0012
      node.position.z += Math.sin(time * 0.35 + node.activity * 6) * 0.0018

      const nodeObject = nodeRefs.current.get(node.id)
      if (nodeObject) {
        nodeObject.position.copy(node.position)
        nodeObject.rotation.y += clampedDelta * 0.5
      }
    })

    if (systemGroupRef.current) {
      const targetY = mode === "temporal" ? 0 : time * 0.08
      const targetX = mode === "temporal" ? 0.02 : Math.sin(time * 0.18) * 0.04
      systemGroupRef.current.rotation.y += (targetY - systemGroupRef.current.rotation.y) * Math.min(1, clampedDelta * 1.5)
      systemGroupRef.current.rotation.x += (targetX - systemGroupRef.current.rotation.x) * Math.min(1, clampedDelta * 1.5)
    }

    if (systemCoreRef.current) {
      const scaleBase = mode === "temporal" ? 0.72 : 1
      const scale = scaleBase + Math.sin(time * 1.4) * 0.025
      const currentScale = systemCoreRef.current.scale.x
      const nextScale = currentScale + (scale - currentScale) * Math.min(1, clampedDelta * 2.4)
      systemCoreRef.current.scale.setScalar(nextScale)

      const aura = systemCoreRef.current.getObjectByName("core-aura")
      if (aura && "material" in aura) {
        const material = aura.material as MeshBasicMaterial
        material.opacity += ((mode === "temporal" ? 0.08 : 0.18) - material.opacity) * Math.min(1, clampedDelta * 2.2)
      }
    }
  })

  return (
    <>
      <color attach="background" args={["#01030a"]} />
      <fog attach="fog" args={["#01030a", 7, 42]} />
      <ambientLight intensity={0.12} color="#60a5fa" />
      <directionalLight position={[5, 8, 10]} intensity={0.42} color="#a855f7" />
      <pointLight position={[-3, 2, 2]} intensity={2.05} distance={14} color="#2563eb" />
      <pointLight position={[3, 3, 1]} intensity={1.95} distance={13} color="#f97316" />
      <pointLight position={[0, -3, 2]} intensity={1.55} distance={12} color="#06b6d4" />
      <AmbientField />
      <TemporalField />

      <group ref={systemGroupRef}>
        <SystemCore groupRef={systemCoreRef} />
        <Nodes
          onNodeObject={(id, object) => {
            if (object) {
              nodeRefs.current.set(id, object)
            } else {
              nodeRefs.current.delete(id)
            }
          }}
        />
        <Connections />
        <Flows />
      </group>

      <CameraController />
      <EffectComposer>
        <Bloom intensity={1.35} luminanceThreshold={0.12} luminanceSmoothing={0.45} />
      </EffectComposer>
    </>
  )
}

export function ArcosExperience() {
  return (
    <Canvas
      camera={{ position: [0, 0, 12], fov: 45 }}
      dpr={[1, 1.35]}
      gl={{ antialias: false, alpha: false, powerPreference: "high-performance" }}
    >
      <SceneRuntime />
    </Canvas>
  )
}
