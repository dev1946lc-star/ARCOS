"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import * as d3 from "d3-force";

import type { AgentInfo } from "@/hooks/useAgentBalances";
import type { ArcosEvent } from "@/hooks/useWebSocket";

interface NetworkGraphProps {
  agents: AgentInfo[];
  events: ArcosEvent[];
}

interface AnimatedEffect {
  update: () => boolean;
}

interface NodeData {
  wallet: string;
  agentId: string;
  role: string;
  baseScale: number;
  pulseRing?: THREE.Mesh;
  targetPos: THREE.Vector3;
  flashUntil: number;
}

const ROLE_COLORS: Record<string, number> = {
  research: 0x8b5cf6,
  compute: 0x06b6d4,
};

const ROLE_SIZES: Record<string, number> = {
  research: 0.42,
  compute: 0.28,
};

const GRAPH_BOUNDS_X = 7.5;
const GRAPH_BOUNDS_Y = 4.2;

export default function NetworkGraph({ agents, events }: NetworkGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const stateRef = useRef<{
    renderer: THREE.WebGLRenderer | null;
    scene: THREE.Scene | null;
    camera: THREE.PerspectiveCamera | null;
    nodes: Map<string, THREE.Mesh>;
    links: { source: string; target: string; line: THREE.Line }[];
    effects: AnimatedEffect[];
    frameId: number;
    time: number;
    lastProcessedEventId: string | null;
  }>({
    renderer: null,
    scene: null,
    camera: null,
    nodes: new Map(),
    links: [],
    effects: [],
    frameId: 0,
    time: 0,
    lastProcessedEventId: null,
  });
  const [targetPositions, setTargetPositions] = useState<Map<string, THREE.Vector3>>(new Map());

  useEffect(() => {
    if (agents.length === 0) return;

    const nodesData = agents.map((agent, index) => ({
      id: index,
      wallet: agent.wallet,
      x: 0,
      y: 0,
    }));

    const linksData = nodesData
      .map((node, index) => ({ source: 0, target: index }))
      .filter((link) => link.source !== link.target);

    const simulation = d3
      .forceSimulation(nodesData as d3.SimulationNodeDatum[])
      .force("charge", d3.forceManyBody().strength(-280))
      .force("center", d3.forceCenter(0, 0).strength(0.1))
      .force("link", d3.forceLink(linksData).distance(4.5))
      .force("collision", d3.forceCollide(0.75))
      .force("x", d3.forceX().strength(0.015))
      .force("y", d3.forceY().strength(0.015))
      .alphaDecay(0.05)
      .stop();

    for (let i = 0; i < 200; i += 1) {
      simulation.tick();
      nodesData.forEach((node) => {
        const n = node as d3.SimulationNodeDatum;
        n.x = Math.max(-GRAPH_BOUNDS_X, Math.min(GRAPH_BOUNDS_X, n.x ?? 0));
        n.y = Math.max(-GRAPH_BOUNDS_Y, Math.min(GRAPH_BOUNDS_Y, n.y ?? 0));
      });
    }

    const nextPositions = new Map<string, THREE.Vector3>();
    nodesData.forEach((node, index) => {
      const point = node as d3.SimulationNodeDatum;
      const z = (index % 3 - 1) * 0.32;
      nextPositions.set(node.wallet, new THREE.Vector3(point.x ?? 0, point.y ?? 0, z));
    });

    setTargetPositions(nextPositions);
  }, [agents]);

  const spawnStream = useCallback((start: THREE.Vector3, end: THREE.Vector3, color: number, count = 3) => {
    const scene = stateRef.current.scene;
    if (!scene) return;

    const distance = start.distanceTo(end);
    const control = start.clone().lerp(end, 0.5);
    control.y += distance * 0.16;
    control.z += distance * 0.08;
    const curve = new THREE.QuadraticBezierCurve3(start, control, end);

    for (let i = 0; i < count; i += 1) {
      const particle = new THREE.Mesh(
        new THREE.SphereGeometry(0.12, 12, 12),
        new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 1.0, blending: THREE.AdditiveBlending })
      );

      particle.position.copy(start);
      scene.add(particle);

      let progress = i * -0.15;

      stateRef.current.effects.push({
        update: () => {
          progress += 0.035;
          if (progress < 0) return true;

          if (progress >= 1) {
            scene.remove(particle);
            particle.geometry.dispose();
            (particle.material as THREE.Material).dispose();
            return false;
          }

          particle.position.copy(curve.getPoint(progress));
          return true;
        },
      });
    }
  }, []);

  const spawnShockwave = useCallback((position: THREE.Vector3, color: number) => {
    const scene = stateRef.current.scene;
    if (!scene) return;

    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.12, 0.20, 32),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.9, side: THREE.DoubleSide, blending: THREE.AdditiveBlending })
    );

    ring.position.copy(position);
    scene.add(ring);

    let progress = 0;
    stateRef.current.effects.push({
      update: () => {
        progress += 0.03;
        ring.scale.setScalar(1 + progress * 18);
        (ring.material as THREE.MeshBasicMaterial).opacity = 0.7 * (1 - progress);

        if (progress >= 1) {
          scene.remove(ring);
          ring.geometry.dispose();
          (ring.material as THREE.Material).dispose();
          return false;
        }

        return true;
      },
    });
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const width = container.clientWidth;
    const height = container.clientHeight;
    const state = stateRef.current;

    const scene = new THREE.Scene();
    state.scene = scene;

    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
    camera.position.set(0, 0, 13.0);
    state.camera = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);
    state.renderer = renderer;

    const grid = new THREE.GridHelper(12, 24, 0x334155, 0x334155);
    grid.rotation.x = Math.PI / 2;
    grid.position.z = -1.2;
    (grid.material as THREE.Material).transparent = true;
    (grid.material as THREE.Material).opacity = 0.06;
    scene.add(grid);

    scene.add(new THREE.AmbientLight(0xffffff, 0.5));
    const pointLight = new THREE.PointLight(0x60a5fa, 1.1, 20);
    pointLight.position.set(1.5, 2, 5);
    scene.add(pointLight);

    const animate = () => {
      state.frameId = requestAnimationFrame(animate);
      state.time += 0.01;

      camera.position.x = Math.sin(state.time * 0.3) * 0.5;
      camera.position.y = Math.cos(state.time * 0.25) * 0.35;
      camera.lookAt(0, 0, 0);
      
      scene.rotation.y = Math.sin(state.time * 0.1) * 0.05;
      scene.rotation.x = Math.cos(state.time * 0.12) * 0.05;

      state.nodes.forEach((mesh) => {
        const data = mesh.userData as NodeData;
        mesh.position.lerp(data.targetPos, 0.05);

        const material = mesh.material as THREE.MeshStandardMaterial;
        const baseEmissive = ROLE_COLORS[data.role] ?? 0xffffff;

        if (state.time < data.flashUntil) {
          material.emissive.setHex(0xffffff);
          material.emissiveIntensity = 2.8;
        } else {
          material.emissive.setHex(baseEmissive);
          material.emissiveIntensity = 0.9 + Math.sin(state.time * 4.0 + data.wallet.length) * 0.28;
        }

        const pulse = 1 + Math.sin(state.time * 3.5 + data.wallet.length) * 0.08;
        mesh.scale.setScalar(pulse * data.baseScale);

        if (data.pulseRing) {
          data.pulseRing.scale.addScalar(0.006);
          (data.pulseRing.material as THREE.MeshBasicMaterial).opacity -= 0.005;
          if ((data.pulseRing.material as THREE.MeshBasicMaterial).opacity <= 0) {
            data.pulseRing.scale.setScalar(1);
            (data.pulseRing.material as THREE.MeshBasicMaterial).opacity = 0.18;
          }
        }
      });

      state.links.forEach(({ source, target, line }) => {
        const sourceMesh = state.nodes.get(source);
        const targetMesh = state.nodes.get(target);
        if (!sourceMesh || !targetMesh) return;

        const start = sourceMesh.position;
        const end = targetMesh.position;
        const distance = start.distanceTo(end);
        const mid = start.clone().lerp(end, 0.5);
        mid.y += distance * 0.18;
        mid.z += distance * 0.08;

        const curve = new THREE.QuadraticBezierCurve3(start, mid, end);
        line.geometry.setFromPoints(curve.getPoints(24));
      });

      state.effects = state.effects.filter((effect) => effect.update());
      renderer.render(scene, camera);
    };

    animate();

    const onResize = () => {
      const nextWidth = container.clientWidth;
      const nextHeight = container.clientHeight;
      camera.aspect = nextWidth / nextHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(nextWidth, nextHeight);
    };

    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      cancelAnimationFrame(state.frameId);
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  useEffect(() => {
    const state = stateRef.current;
    const scene = state.scene;
    if (!scene || targetPositions.size === 0) return;

    agents.forEach((agent) => {
      const targetPos = targetPositions.get(agent.wallet) ?? new THREE.Vector3();
      const existing = state.nodes.get(agent.wallet);

      if (existing) {
        (existing.userData as NodeData).targetPos.copy(targetPos);
        return;
      }

      const color = ROLE_COLORS[agent.role] ?? 0xffffff;
      const size = ROLE_SIZES[agent.role] ?? 0.3;
      const mesh = new THREE.Mesh(
        new THREE.SphereGeometry(size, 28, 28),
        new THREE.MeshStandardMaterial({
          color,
          emissive: color,
          emissiveIntensity: 0.9,
          roughness: 0.2,
          metalness: 0.65,
        })
      );

      mesh.position.copy(targetPos).add(new THREE.Vector3((Math.random() - 0.5) * 1.6, (Math.random() - 0.5) * 1.6, 0));

      const pulseRing = new THREE.Mesh(
        new THREE.RingGeometry(size + 0.08, size + 0.16, 32),
        new THREE.MeshBasicMaterial({
          color,
          transparent: true,
          opacity: 0.28,
          side: THREE.DoubleSide,
          blending: THREE.AdditiveBlending,
        })
      );

      mesh.add(pulseRing);
      mesh.userData = {
        wallet: agent.wallet,
        agentId: agent.agent_id,
        role: agent.role,
        baseScale: 1,
        pulseRing,
        targetPos: targetPos.clone(),
        flashUntil: state.time + 0.75,
      } satisfies NodeData;

      scene.add(mesh);
      state.nodes.set(agent.wallet, mesh);
    });

    state.links.forEach(({ line }) => {
      scene.remove(line);
      line.geometry.dispose();
      (line.material as THREE.Material).dispose();
    });
    state.links = [];

    const wallets = Array.from(state.nodes.keys());
    if (wallets.length > 1) {
      const hub = wallets[0];

      for (let i = 1; i < wallets.length; i += 1) {
        const line = new THREE.Line(
          new THREE.BufferGeometry(),
          new THREE.LineBasicMaterial({
            color: 0x0ea5e9,
            transparent: true,
            opacity: 0.45,
            blending: THREE.AdditiveBlending,
          })
        );

        scene.add(line);
        state.links.push({ source: hub, target: wallets[i], line });
      }
    }
  }, [agents, targetPositions]);

  const lastRawEvent = useMemo(() => events[events.length - 1] ?? null, [events]);

  useEffect(() => {
    const state = stateRef.current;
    if (!lastRawEvent || !state.scene || state.nodes.size === 0) return;

    const eventId = `${lastRawEvent.timestamp}-${lastRawEvent.type}-${String(lastRawEvent.data.task_id ?? "")}-${String(lastRawEvent.data.agent_id ?? "")}`;
    if (state.lastProcessedEventId === eventId) return;
    state.lastProcessedEventId = eventId;

    const nodes = Array.from(state.nodes.values());
    const researchNode = nodes.find((node) => (node.userData as NodeData).role === "research") ?? nodes[0];

    if (lastRawEvent.type === "job_created" && researchNode) {
      (researchNode.userData as NodeData).flashUntil = state.time + 0.4;
    }

    if (lastRawEvent.type === "job_accepted") {
      const compute = nodes.find((node) => (node.userData as NodeData).agentId === lastRawEvent.data.agent_id);
      if (researchNode && compute) {
        spawnStream(researchNode.position, compute.position, 0x06b6d4, 2);
      }
    }

    if (lastRawEvent.type === "job_completed") {
      const compute = nodes.find((node) => (node.userData as NodeData).agentId === lastRawEvent.data.agent_id);
      if (researchNode && compute) {
        spawnStream(compute.position, researchNode.position, 0x10b981, 2);
        (researchNode.userData as NodeData).flashUntil = state.time + 0.35;
      }
    }

    if (lastRawEvent.type === "payment_sent") {
      const sender = state.nodes.get(lastRawEvent.data.sender as string);
      const recipient = state.nodes.get(lastRawEvent.data.recipient as string);
      if (sender && recipient) {
        spawnStream(sender.position, recipient.position, 0x3b82f6, 3);
      }
    }

    if (lastRawEvent.type === "agent_spawned") {
      const node = state.nodes.get(lastRawEvent.data.wallet as string);
      if (node) {
        spawnShockwave(node.position, 0x8b5cf6);
      }
    }
  }, [lastRawEvent, spawnShockwave, spawnStream]);

  return (
    <div className="relative h-full min-h-[420px] w-full overflow-hidden" ref={containerRef}>
      <div className="pointer-events-none absolute inset-x-0 top-0 z-10 flex items-start justify-between px-5 py-4">
        <div className="space-y-1">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-[var(--text-secondary)]">
            Neural Infrastructure Topography
          </div>
          <div className="text-xs text-[var(--text-secondary)]">
            Settlement paths, compute activation, and topology health.
          </div>
        </div>

        <div className="rounded-2xl border px-3 py-2 text-[11px] text-[var(--text-secondary)] backdrop-blur">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: "var(--accent-violet)" }} />
            Research Node
          </div>
          <div className="mt-1 flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: "var(--accent-cyan)" }} />
            Compute Node
          </div>
        </div>
      </div>
    </div>
  );
}
