"use client";

import { useEffect, useState } from "react";

const API_BASE = "http://localhost:8000";

interface EconomicsProof {
  transactions: number;
  avg_cost_per_tx: number;
  total_cost: number;
  traditional_cost_estimate: number;
  savings_factor: number;
}

function formatUSD(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 5,
  }).format(value);
}

export default function EconomicsProofBanner() {
  const [proof, setProof] = useState<EconomicsProof | null>(null);

  useEffect(() => {
    const fetchProof = async () => {
      try {
        const res = await fetch(`${API_BASE}/economics/proof`);
        if (!res.ok) return;
        const data = await res.json();
        setProof(data);
      } catch {
        // Silent catch
      }
    };

    fetchProof();
    const iv = setInterval(fetchProof, 2000);
    return () => clearInterval(iv);
  }, []);

  if (!proof || proof.transactions < 1) return null;

  return (
    <div className="panel-surface mb-4 px-5 py-4 border border-[var(--accent-blue)] bg-gradient-to-r from-[rgba(14,165,233,0.1)] to-transparent relative overflow-hidden">
      <div className="absolute top-0 right-0 p-2 opacity-10 pointer-events-none">
        <svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="var(--accent-blue)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>
      </div>
      
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--accent-blue)] mb-1">
            Real Economic Validation
          </div>
          <div className="text-sm text-[var(--text-secondary)]">
            Executing <strong className="text-white">{proof.transactions}+ nanopayment stream transactions</strong> autonomously.
          </div>
        </div>
        
        <div className="flex flex-wrap gap-4 md:gap-8">
          <div className="flex flex-col">
            <span className="text-[10px] uppercase text-[var(--text-secondary)] tracking-wider">Per-Action Cost</span>
            <span className="text-lg font-mono text-[var(--accent-cyan)] font-bold">{formatUSD(proof.avg_cost_per_tx)}</span>
          </div>

          <div className="flex flex-col">
            <span className="text-[10px] uppercase text-[var(--text-secondary)] tracking-wider">Total Arc Cost</span>
            <span className="text-lg font-mono text-[var(--accent-green)] font-bold">{formatUSD(proof.total_cost)}</span>
          </div>

          <div className="flex flex-col">
            <span className="text-[10px] uppercase text-[var(--text-secondary)] tracking-wider">Traditional Gas Estimate</span>
            <span className="text-lg font-mono text-[var(--accent-orange)] font-bold line-through opacity-70">{formatUSD(proof.traditional_cost_estimate)}</span>
          </div>
          
          <div className="flex flex-col">
            <span className="text-[10px] uppercase text-[var(--text-secondary)] tracking-wider">Margin Multiplier</span>
            <span className="text-lg font-mono text-[var(--accent-violet)] font-bold">{proof.savings_factor.toLocaleString()}x</span>
          </div>
        </div>
      </div>
    </div>
  );
}
