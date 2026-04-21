"use client";

import type { MetricItem } from "@/hooks/useSystemStats";

export default function MetricsBar({ metrics }: { metrics: MetricItem[] }) {
  return (
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
      {metrics.map((metric) => (
        <article
          key={metric.key}
          className={`panel-surface px-4 py-4 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg ${metric.changed ? "metric-flash" : ""}`}
          style={{
            ["--hover-glow" as string]: metric.tone,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.boxShadow = `0 12px 32px color-mix(in srgb, ${metric.tone} 25%, transparent)`;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.boxShadow = "";
          }}
        >
          <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--text-secondary)] transition-colors duration-300">
            {metric.label}
          </div>
          <div
            className="mt-2 text-xl font-semibold tracking-tight transition-colors duration-300"
            style={{ color: metric.tone }}
          >
            {metric.value}
          </div>
        </article>
      ))}
    </section>
  );
}
