"use client";

import { ReactNode } from "react";

interface PanelProps {
  title: string;
  status?: {
    label: string;
    tone?: string;
  };
  actions?: ReactNode;
  children: ReactNode;
  contentClassName?: string;
  className?: string;
}

export default function Panel({
  title,
  status,
  actions,
  children,
  contentClassName = "",
  className = "",
}: PanelProps) {
  return (
    <section className={`panel-surface panel-muted flex min-h-0 flex-col ${className}`}>
      <header className="flex items-center justify-between gap-4 border-b px-5 py-4">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold tracking-[0.16em] text-[var(--text-secondary)] uppercase">
            {title}
          </h2>
          {status ? (
            <span
              className="inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.16em]"
              style={{
                color: status.tone ?? "var(--text-secondary)",
                borderColor: "color-mix(in srgb, var(--border-subtle) 84%, transparent)",
                background: "color-mix(in srgb, var(--bg-surface) 88%, transparent)",
              }}
            >
              <span
                className="h-2 w-2 rounded-full"
                style={{ background: status.tone ?? "var(--text-secondary)" }}
              />
              {status.label}
            </span>
          ) : null}
        </div>

        {actions ? <div className="shrink-0">{actions}</div> : null}
      </header>

      <div className={`min-h-0 flex-1 ${contentClassName}`}>{children}</div>
    </section>
  );
}
