"use client";

import type { ReactNode } from "react";

/** Weicher Farbverlauf im Kopfbereich – abhängig von Sonnenhöhe und Bewölkung. */
export function heroGradient(elevation: number | undefined, cloud: number | undefined): string {
  const e = elevation ?? 30;
  const c = Math.min(Math.max(cloud ?? 30, 0), 100) / 100;
  let a: string;
  let b: string;
  if (e < -6) {
    a = "rgba(76, 61, 160, 0.30)"; // Nacht: Violett
    b = "rgba(30, 58, 138, 0.18)";
  } else if (e < 8) {
    a = "rgba(249, 115, 22, 0.32)"; // Dämmerung: Orange/Rosé
    b = "rgba(236, 72, 153, 0.16)";
  } else {
    a = `rgba(245, 165, 36, ${0.34 - c * 0.18})`; // Tag: Amber, bei Wolken blasser
    b = `rgba(56, 189, 248, ${0.2 - c * 0.08})`;
  }
  return `radial-gradient(120% 90% at 15% 0%, ${a} 0%, transparent 60%), radial-gradient(100% 80% at 95% 10%, ${b} 0%, transparent 55%)`;
}

export function Hero({ elevation, cloud, children }: { elevation?: number; cloud?: number; children: ReactNode }) {
  return (
    <section className="relative overflow-hidden rounded-[24px] border border-border bg-card">
      <div aria-hidden className="pointer-events-none absolute inset-0 transition-[background] duration-1000" style={{ background: heroGradient(elevation, cloud) }} />
      <div className="relative p-4 sm:p-6">{children}</div>
    </section>
  );
}
