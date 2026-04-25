"use client"

import { motion, useScroll, useSpring } from "framer-motion"
import { Hero } from "./Hero"
import { Features } from "./Features"
import { About } from "./About"
import { CallToAction } from "./CallToAction"
import { Footer } from "./Footer"
import { Navbar } from "./Navbar"
import { useEffect, useState } from "react"

export default function LandingPage() {
  const { scrollYProgress } = useScroll()
  const scaleX = useSpring(scrollYProgress, {
    stiffness: 100,
    damping: 30,
    restDelta: 0.001,
  })

  const [isMounted, setIsMounted] = useState(false)

  useEffect(() => {
    setIsMounted(true)
  }, [])

  if (!isMounted) return null

  return (
    <div className="relative min-h-screen bg-[#02050d] text-white selection:bg-purple-500/30">
      {/* Progress Bar */}
      <motion.div
        className="fixed top-0 left-0 right-0 z-50 h-1 bg-gradient-to-right from-blue-500 to-purple-600 origin-left"
        style={{ scaleX }}
      />

      <Navbar />

      <main>
        <Hero />
        <About />
        <Features />
        <CallToAction />
      </main>

      <Footer />
    </div>
  )
}
