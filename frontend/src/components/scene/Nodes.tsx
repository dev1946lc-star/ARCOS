"use client"

import { useMemo, useState } from "react"
import { useCursor, Html } from "@react-three/drei"
import { AdditiveBlending, type Group } from "three"
import { useArcosSimStore, type NodeType } from "@/lib/store/arcos-store"

const colorMap: Record<NodeType, string> = {
  signals: "#3b82f6",
  compute: "#a855f7",
  execution: "#f97316",
  payments: "#22d3ee",
  validation: "#22c55e",
}

interface NodesProps {
  onNodeObject?: (id: string, object: Group | null) => void
}

export function Nodes({ onNodeObject }: NodesProps) {
  const nodes = useArcosSimStore((s) => s.nodes)
  const selectedEntity = useArcosSimStore((s) => s.selectedEntity)
  const selectEntity = useArcosSimStore((s) => s.selectEntity)
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  useCursor(Boolean(hoveredId))

  const renderNodes = useMemo(() =>
    nodes.map((n) => ({ ...n, color: colorMap[n.type], selected: selectedEntity === n.id, hovered: hoveredId === n.id })),
    [hoveredId, nodes, selectedEntity],
  )

  return (
    <group>
      {renderNodes.map((n) => (
        <group key={n.id} ref={(o) => onNodeObject?.(n.id, o)} position={n.position}
          onPointerOver={(e) => { e.stopPropagation(); setHoveredId(n.id) }}
          onPointerOut={(e) => { e.stopPropagation(); setHoveredId((c) => (c === n.id ? null : c)) }}
          onClick={(e) => { e.stopPropagation(); selectEntity(n.id) }}>
          
          {n.hovered && (
            <Html position={[0, 1.2, 0]} center>
              <div className="pointer-events-none w-max rounded-lg border border-white/10 bg-[#050b16]/90 px-3 py-2 text-white shadow-xl backdrop-blur-md">
                <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">{n.type}</div>
                <div className="mt-0.5 text-sm font-medium">{n.id.toUpperCase()}</div>
                <div className="mt-1 flex items-center gap-2 text-[11px]">
                  <span className="text-slate-400">Load:</span>
                  <span className="text-emerald-400">{Math.round(n.activity * 100)}%</span>
                </div>
              </div>
            </Html>
          )}

          <mesh><sphereGeometry args={[n.selected ? 0.98 : n.hovered ? 0.88 : 0.78, 18, 18]} /><meshBasicMaterial color={n.color} transparent opacity={n.selected ? 0.05 : 0.026} blending={AdditiveBlending} depthWrite={false} /></mesh>
          <mesh><sphereGeometry args={[n.selected ? 0.72 : n.hovered ? 0.64 : 0.58, 18, 18]} /><meshBasicMaterial color={n.color} transparent opacity={n.selected ? 0.085 : n.hovered ? 0.06 : 0.042} blending={AdditiveBlending} depthWrite={false} /></mesh>
          <mesh><sphereGeometry args={[n.selected ? 0.44 : n.hovered ? 0.4 : 0.36, 20, 20]} /><meshStandardMaterial color={n.color} emissive={n.color} emissiveIntensity={n.selected ? 3.2 : n.hovered ? 2.25 : 1.75} metalness={0.08} roughness={0.16} /></mesh>
          <mesh><sphereGeometry args={[n.selected ? 0.18 : 0.16, 14, 14]} /><meshBasicMaterial color="#f8fbff" transparent opacity={0.95} blending={AdditiveBlending} depthWrite={false} /></mesh>
          <mesh><sphereGeometry args={[n.selected ? 0.68 : n.hovered ? 0.61 : 0.55, 16, 16]} /><meshBasicMaterial color={n.color} transparent opacity={n.selected ? 0.16 : n.hovered ? 0.11 : 0.08} blending={AdditiveBlending} depthWrite={false} /></mesh>
        </group>
      ))}
    </group>
  )
}
