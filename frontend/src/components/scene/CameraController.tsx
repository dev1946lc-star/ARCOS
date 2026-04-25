"use client"

import { OrbitControls } from "@react-three/drei"
import { useFrame, useThree } from "@react-three/fiber"
import { useMemo, useRef } from "react"
import { Vector3 } from "three"
import { useArcosSimStore } from "@/lib/store/arcos-store"

export function CameraController() {
  const controlsRef = useRef<React.ElementRef<typeof OrbitControls>>(null)
  const { camera } = useThree()
  const desiredPosition = useMemo(() => new Vector3(), [])
  const desiredTarget = useMemo(() => new Vector3(), [])
  const idleOffset = useMemo(() => new Vector3(), [])
  const elapsedRef = useRef(0)

  useFrame((_, delta) => {
    const { nodes, mode, selectedEntity } = useArcosSimStore.getState()
    const selectedNode = nodes.find((node) => node.id === selectedEntity) ?? null
    elapsedRef.current += delta
    const time = elapsedRef.current

    desiredTarget.set(0, mode === "temporal" ? 0.2 : 0, 0)
    desiredPosition.set(0, mode === "temporal" ? 0.4 : 1.4, mode === "temporal" ? 13.5 : 12)

    if (selectedNode) {
      desiredTarget.copy(selectedNode.position)
      desiredPosition.copy(selectedNode.position).add(mode === "temporal" ? new Vector3(0, 1.2, 5.6) : new Vector3(0, 2.1, 4.8))
    }

    idleOffset.set(Math.sin(time * 0.24) * 0.15, Math.cos(time * 0.18) * 0.12, 0)
    desiredPosition.add(idleOffset)

    const alpha = Math.min(1, delta * 2.2)
    // Only lerp position if we are following a selected node or switching modes
    // To allow free panning, we only enforce the target/position smoothly when a node is selected
    if (selectedNode) {
      camera.position.lerp(desiredPosition, alpha)
      controlsRef.current?.target.lerp(desiredTarget, alpha)
    } else if (mode === "temporal") {
      camera.position.lerp(desiredPosition, alpha)
      controlsRef.current?.target.lerp(desiredTarget, alpha)
    }

    controlsRef.current?.update()
  })

  return (
    <OrbitControls
      ref={controlsRef}
      enablePan={true}
      enableZoom={true}
      enableDamping
      dampingFactor={0.08}
      minDistance={6}
      maxDistance={40}
      minPolarAngle={0.2}
      maxPolarAngle={Math.PI - 0.2}
    />
  )
}
