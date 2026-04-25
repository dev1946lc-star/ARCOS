"use client"

import { useEffect, useState } from "react"
import { ArcosExperience } from "@/components/scene/ArcosExperience"
import { BottomPanels } from "@/components/ui/BottomPanels"
import { CenterPanel } from "@/components/ui/CenterPanel"
import { LeftPanel } from "@/components/ui/LeftPanel"
import { RightPanel } from "@/components/ui/RightPanel"
import { TopBar } from "@/components/ui/TopBar"
import { TemporalLiveFeed } from "@/components/ui/TemporalLiveFeed"
import { ControlPanel } from "@/components/ui/ControlPanel"
import { useArcosSimStore } from "@/lib/store/arcos-store"

export default function DashboardPage() {
  const initBackend = useArcosSimStore((s) => s.initBackend)
  const cleanupBackend = useArcosSimStore((s) => s.cleanupBackend)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    initBackend()
    return () => cleanupBackend()
  }, [initBackend, cleanupBackend])

  return (
    <main className="relative h-screen overflow-hidden bg-[#02050d] text-white">
      {/* 3D Canvas Background */}
      <div className="absolute inset-0">
        <ArcosExperience />
      </div>

      {/* Gradient Overlay */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_35%,rgba(56,189,248,0.035),transparent_24%),radial-gradient(circle_at_60%_65%,rgba(168,85,247,0.04),transparent_22%),linear-gradient(180deg,rgba(2,5,13,0.22),rgba(2,5,13,0.72))]" />

      {/* UI Overlay Layer */}
      <div className="pointer-events-none absolute inset-0 z-10">
        {/* Top Bar */}
        <div className="pointer-events-auto absolute inset-x-0 top-0 p-3">
          <TopBar />
        </div>

        {mounted && (
          <>
            {/* Left Sidebar Panels */}
            <LeftPanel />

            {/* Right Sidebar Panels */}
            <RightPanel />

            {/* Bottom Panels */}
            <BottomPanels />

            {/* Temporal Main Live Feed */}
            <TemporalLiveFeed />

            {/* Center Agent Snapshot */}
            <CenterPanel />

            {/* System Controls */}
            <ControlPanel />
          </>
        )}
      </div>
    </main>
  )
}
