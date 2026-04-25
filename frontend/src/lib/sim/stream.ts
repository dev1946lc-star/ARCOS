import { useArcosSimStore } from "@/lib/store/arcos-store"

function pickRandom<T>(items: T[]) {
  return items[Math.floor(Math.random() * items.length)]
}

export function createSimulationStream() {
  let timeoutId: number | null = null
  let counter = 0

  const schedule = () => {
    timeoutId = window.setTimeout(
      () => {
        const state = useArcosSimStore.getState()
        if (state.streamStatus !== "live") {
          schedule()
          return
        }

        const nodes = state.nodes
        if (nodes.length === 0) {
          schedule()
          return
        }

        const source = pickRandom(nodes)
        const connectionTargets = nodes.filter((node) => source.connections.includes(node.id))
        const target = connectionTargets.length > 0 ? pickRandom(connectionTargets) : pickRandom(nodes)

        counter += 1

        useArcosSimStore.setState((current) => ({
          ambientPulse: Math.min(1, current.ambientPulse * 0.45 + 0.55),
          nodes: current.nodes.map((node) => {
            const decay = Math.max(0.2, node.activity * 0.985)
            if (node.id === source.id || node.id === target.id) {
              return { ...node, activity: Math.min(1, decay + 0.16 + Math.random() * 0.12) }
            }
            return { ...node, activity: decay }
          }),
          flows: [
            ...current.flows.slice(-35),
            {
              id: `flow-live-${counter}`,
              sourceId: source.id,
              targetId: target.id,
              progress: 0,
              speed: 0.18 + Math.random() * 0.22,
            },
          ],
        }))

        schedule()
      },
      100 + Math.random() * 200,
    )
  }

  return {
    start() {
      if (timeoutId !== null) return
      schedule()
    },
    stop() {
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId)
        timeoutId = null
      }
    },
  }
}
