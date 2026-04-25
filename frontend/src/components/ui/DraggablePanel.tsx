"use client"

import { useRef, useCallback, useState, useEffect, type ReactNode } from "react"
import { motion } from "framer-motion"
import { GripHorizontal, Minimize2, Maximize2, X, RotateCcw } from "lucide-react"
import { useArcosSimStore } from "@/lib/store/arcos-store"
import { cn } from "@/lib/utils"

export type PositionValue = { x: number; y: number }
export type PositionInput = PositionValue | ((vp: { w: number; h: number }) => PositionValue)

const SSR_VP = { w: 1440, h: 900 }

function resolvePos(input: PositionInput, vp: { w: number; h: number }): PositionValue {
  return typeof input === "function" ? input(vp) : input
}

interface DraggablePanelProps {
  id: string
  title?: string
  children: ReactNode
  defaultPosition?: PositionInput
  className?: string
  showControls?: boolean
  constrainToViewport?: boolean
}

export function DraggablePanel({
  id,
  title,
  children,
  defaultPosition = { x: 0, y: 0 },
  className,
  showControls = true,
  constrainToViewport = true,
}: DraggablePanelProps) {
  const panelLayout = useArcosSimStore((s) => s.panelLayout)
  const updatePanelLayout = useArcosSimStore((s) => s.updatePanelLayout)
  const saved = panelLayout[id]
  const [collapsed, setCollapsed] = useState(saved?.collapsed ?? false)
  const constraintRef = useRef<HTMLDivElement>(null)

  const [computedDefault, setComputedDefault] = useState<PositionValue>(() =>
    resolvePos(defaultPosition, SSR_VP)
  )

  useEffect(() => {
    if (typeof defaultPosition === "function") {
      setComputedDefault(defaultPosition({ w: window.innerWidth, h: window.innerHeight }))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const initialX = saved?.x ?? computedDefault.x
  const initialY = saved?.y ?? computedDefault.y

  const handleDragEnd = useCallback(
    (_: unknown, info: { point: { x: number; y: number } }) => {
      updatePanelLayout(id, { x: info.point.x, y: info.point.y })
    },
    [id, updatePanelLayout],
  )

  useEffect(() => {
    if (constrainToViewport && constraintRef.current) {
      constraintRef.current.style.position = "fixed"
      constraintRef.current.style.inset = "0"
      constraintRef.current.style.pointerEvents = "none"
      constraintRef.current.style.zIndex = "-1"
    }
  }, [constrainToViewport])

  return (
    <>
      {constrainToViewport && <div ref={constraintRef} />}
      <motion.div
        drag
        dragMomentum={false}
        dragElastic={0.1}
        dragConstraints={constrainToViewport ? constraintRef : undefined}
        onDragEnd={handleDragEnd}
        initial={{ x: initialX, y: initialY, opacity: 0, scale: 0.95 }}
        animate={{ x: saved?.x ?? initialX, y: saved?.y ?? initialY, opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
        className={cn(
          "absolute top-0 left-0 pointer-events-auto rounded-[18px] border border-white/[0.08] bg-[#050b16]/[0.92] shadow-[0_18px_60px_rgba(0,0,0,0.34)] backdrop-blur-xl",
          "select-none",
          className,
        )}
        style={{ touchAction: "none" }}
      >
        {/* Drag Handle */}
        {(title || showControls) && (
          <div className="flex items-center justify-between px-3 pt-2.5 pb-1 cursor-grab active:cursor-grabbing">
            <div className="flex items-center gap-2">
              <GripHorizontal className="h-3 w-3 text-slate-600" />
              {title && (
                <h3 className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                  {title}
                </h3>
              )}
            </div>
            {showControls && (
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    setCollapsed(!collapsed)
                    updatePanelLayout(id, { collapsed: !collapsed })
                  }}
                  className="flex h-5 w-5 items-center justify-center rounded-md text-slate-500 hover:bg-white/[0.06] hover:text-slate-300 transition-colors"
                >
                  {collapsed ? <Maximize2 className="h-2.5 w-2.5" /> : <Minimize2 className="h-2.5 w-2.5" />}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Content */}
        <motion.div
          animate={{ height: collapsed ? 0 : "auto", opacity: collapsed ? 0 : 1 }}
          transition={{ duration: 0.25, ease: "easeInOut" }}
          className="overflow-hidden"
        >
          <div className="px-2.5 pb-2.5">{children}</div>
        </motion.div>
      </motion.div>
    </>
  )
}

// Reset all panels button
export function ResetLayoutButton() {
  const resetPanelLayout = useArcosSimStore((s) => s.resetPanelLayout)
  return (
    <button
      type="button"
      onClick={resetPanelLayout}
      className="flex h-7 items-center gap-1.5 rounded-[10px] border border-white/10 bg-[#050b16]/72 px-2.5 text-[9px] font-medium uppercase tracking-[0.14em] text-slate-400 hover:text-slate-200 backdrop-blur-md transition-colors"
    >
      <RotateCcw className="h-2.5 w-2.5" />
      Reset Layout
    </button>
  )
}
