"use client"

import { MeshTransmissionMaterial } from "@react-three/drei"
import type { RefObject } from "react"
import { AdditiveBlending, type Group } from "three"

interface SystemCoreProps {
  groupRef?: RefObject<Group | null>
}

export function SystemCore({ groupRef }: SystemCoreProps) {
  return (
    <group ref={groupRef}>
      <mesh rotation={[Math.PI / 2, 0, 0]}><torusGeometry args={[1.95, 0.026, 24, 240]} /><meshBasicMaterial color="#7c3aed" transparent opacity={0.4} blending={AdditiveBlending} depthWrite={false} /></mesh>
      <mesh rotation={[Math.PI / 2.6, 0.5, 0]}><torusGeometry args={[2.9, 0.02, 24, 220]} /><meshBasicMaterial color="#3b82f6" transparent opacity={0.16} blending={AdditiveBlending} depthWrite={false} /></mesh>
      <mesh rotation={[Math.PI / 2.35, -0.35, 0.4]}><torusGeometry args={[3.8, 0.016, 24, 220]} /><meshBasicMaterial color="#22d3ee" transparent opacity={0.1} blending={AdditiveBlending} depthWrite={false} /></mesh>
      <mesh rotation={[0.7, 0.2, 0.15]}><icosahedronGeometry args={[1.5, 2]} /><meshBasicMaterial color="#93c5fd" wireframe transparent opacity={0.08} blending={AdditiveBlending} depthWrite={false} /></mesh>
      <mesh rotation={[-0.55, 0.65, -0.2]}><sphereGeometry args={[1.78, 22, 22]} /><meshBasicMaterial color="#7dd3fc" wireframe transparent opacity={0.05} blending={AdditiveBlending} depthWrite={false} /></mesh>
      <mesh><sphereGeometry args={[2.4, 48, 48]} /><meshBasicMaterial color="#8b5cf6" transparent opacity={0.035} blending={AdditiveBlending} depthWrite={false} /></mesh>
      <mesh name="core-aura"><sphereGeometry args={[1.55, 64, 64]} /><meshBasicMaterial color="#38bdf8" transparent opacity={0.18} blending={AdditiveBlending} depthWrite={false} /></mesh>
      <mesh><sphereGeometry args={[1.15, 64, 64]} /><meshBasicMaterial color="#a855f7" transparent opacity={0.11} blending={AdditiveBlending} depthWrite={false} /></mesh>
      <mesh name="core-shell"><sphereGeometry args={[1.05, 64, 64]} /><MeshTransmissionMaterial backside samples={4} thickness={0.4} roughness={0.12} chromaticAberration={0.04} anisotropy={0.2} distortion={0.08} distortionScale={0.2} temporalDistortion={0.12} color="#60a5fa" attenuationColor="#6d28d9" attenuationDistance={1.2} /></mesh>
      <mesh name="core-heart"><sphereGeometry args={[0.4, 48, 48]} /><meshStandardMaterial color="#f8fafc" emissive="#c084fc" emissiveIntensity={3.4} metalness={0.15} roughness={0.08} /></mesh>
      <mesh><sphereGeometry args={[0.18, 32, 32]} /><meshBasicMaterial color="#ffffff" transparent opacity={1} blending={AdditiveBlending} depthWrite={false} /></mesh>
    </group>
  )
}
