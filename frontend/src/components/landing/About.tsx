"use client"

import { motion } from "framer-motion"

export function About() {
  return (
    <section className="py-24 md:py-40 relative overflow-hidden" id="about">
      <div className="container mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="relative"
          >
            <div className="relative rounded-3xl overflow-hidden aspect-square max-w-lg mx-auto border border-white/5 shadow-2xl">
              <video
                autoPlay
                loop
                muted
                playsInline
                className="w-full h-full object-cover"
              >
                <source src="/assets/landing/helix.mp4" type="video/mp4" />
              </video>
              <div className="absolute inset-0 bg-gradient-to-t from-[#02050d] via-transparent to-transparent" />
            </div>
            
            {/* Decorative Elements */}
            <div className="absolute -top-10 -left-10 w-40 h-40 bg-blue-600/20 blur-[100px]" />
            <div className="absolute -bottom-10 -right-10 w-40 h-40 bg-purple-600/20 blur-[100px]" />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <span className="text-blue-500 font-mono text-sm tracking-widest uppercase mb-4 block">
              The Architecture
            </span>
            <h2 className="text-4xl md:text-6xl font-bold tracking-tight mb-8">
              Engineered for <br /> <span className="text-zinc-500 italic">Scale & Resilience.</span>
            </h2>
            <div className="space-y-6 text-lg text-zinc-400 leading-relaxed">
              <p>
                ARCOS is a spatial interface for exploring how autonomous agents
                coordinate, exchange value, and respond to changing conditions in
                real time. It turns abstract system behavior into something teams
                can actually inspect and reason about.
              </p>
              <p>
                Instead of leaning on inflated metrics, we focus on clarity:
                simulation, observability, and economic feedback loops designed to
                help early operators understand what their agent systems are doing.
              </p>
            </div>

            <div className="mt-12 grid grid-cols-2 gap-8">
              <div>
                <h4 className="text-3xl font-bold text-white mb-1">Spatial</h4>
                <p className="text-zinc-500 text-sm">System visualization</p>
              </div>
              <div>
                <h4 className="text-3xl font-bold text-white mb-1">Adaptive</h4>
                <p className="text-zinc-500 text-sm">Economic feedback loops</p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
