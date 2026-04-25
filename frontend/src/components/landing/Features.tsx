"use client"

import { motion } from "framer-motion"
import { Shield, Zap, Cpu, Layers } from "lucide-react"

export function Features() {
  const features = [
    {
      id: "01",
      title: "High Internal Quality Control",
      description: "Automated validation loops ensure every agentic decision meets system-wide safety standards.",
      video: "/assets/landing/triugolnik.mp4",
      icon: <Shield className="w-6 h-6" />,
    },
    {
      id: "02",
      title: "24/7 Uninterrupted Operation",
      description: "Distributed node architecture guarantees zero downtime for your economic mesh.",
      video: "/assets/landing/ball.mp4",
      icon: <Zap className="w-6 h-6" />,
    },
    {
      id: "03",
      title: "Cross-Chain Economic Mesh",
      description: "Seamlessly integrate with liquidity pools across all major EVM and SVM networks.",
      video: "/assets/landing/abstract.mp4",
      icon: <Layers className="w-6 h-6" />,
    },
  ]

  return (
    <section className="py-24 bg-white/[0.02] border-y border-white/5" id="services">
      <div className="container mx-auto px-6">
        <div className="mb-20">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">Why Choose ARCOS?</h2>
          <p className="text-zinc-500 text-lg max-w-2xl">
            We provide the infrastructure for the next generation of digital labor. 
            Automate your wealth, governance, and simulation with a single click.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <motion.div
              key={feature.id}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.2 }}
              className="group relative p-8 rounded-3xl bg-white/5 border border-white/10 hover:border-blue-500/50 transition-all overflow-hidden"
            >
              {/* Video Background on Hover */}
              <div className="absolute inset-0 opacity-0 group-hover:opacity-20 transition-opacity">
                <video
                  autoPlay
                  loop
                  muted
                  playsInline
                  className="w-full h-full object-cover"
                >
                  <source src={feature.video} type="video/mp4" />
                </video>
              </div>

              <div className="relative z-10">
                <div className="w-12 h-12 rounded-xl bg-blue-600/20 flex items-center justify-center text-blue-400 mb-6 group-hover:scale-110 transition-transform">
                  {feature.icon}
                </div>
                <span className="text-xs font-mono text-zinc-600 mb-2 block">{feature.id}</span>
                <h3 className="text-2xl font-bold mb-4 group-hover:text-blue-400 transition-colors">{feature.title}</h3>
                <p className="text-zinc-400 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
