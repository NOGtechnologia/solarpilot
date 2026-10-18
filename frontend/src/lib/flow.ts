import type { Snapshot } from "./types";

export type NodeId = "pv" | "grid" | "battery" | "home";

export interface Flow {
  from: NodeId | "hub";
  to: NodeId | "hub";
  watts: number;
  color: string;
}

const THRESHOLD_W = 15;

/**
 * Leitet die Energieflüsse für das Diagramm ab. Alle Flüsse laufen über den zentralen Knoten
 * ("hub"): Quellen (PV, Netzbezug, Batterie-Entladung) → hub → Senken (Haus, Einspeisung, Laden).
 */
export function flows(s: Snapshot | null | undefined, colors: Record<string, string>): Flow[] {
  if (!s) return [];
  const out: Flow[] = [];
  const pv = Math.max(s.pv_power_w ?? 0, 0);
  const grid = s.grid_power_w ?? 0;
  const batt = s.battery_power_w ?? 0;
  const load = Math.max(s.load_power_w ?? 0, 0);
  if (pv > THRESHOLD_W) out.push({ from: "pv", to: "hub", watts: pv, color: colors.solar });
  if (grid > THRESHOLD_W) out.push({ from: "grid", to: "hub", watts: grid, color: colors.gridImport });
  if (grid < -THRESHOLD_W) out.push({ from: "hub", to: "grid", watts: -grid, color: colors.gridExport });
  if (batt > THRESHOLD_W) out.push({ from: "hub", to: "battery", watts: batt, color: colors.battery });
  if (batt < -THRESHOLD_W) out.push({ from: "battery", to: "hub", watts: -batt, color: colors.battery });
  if (load > THRESHOLD_W) out.push({ from: "hub", to: "home", watts: load, color: colors.load });
  return out;
}

/** Dauer einer Punkt-Animation in Sekunden: mehr Leistung = schneller (0,8–4 s). */
export function flowDuration(watts: number): number {
  const kw = Math.max(watts, 1) / 1000;
  return Math.min(4, Math.max(0.8, 3.2 - Math.log10(kw + 1) * 2.2));
}

/** Anzahl leuchtender Punkte pro Leitung (1–4). */
export function flowDots(watts: number): number {
  if (watts < 500) return 1;
  if (watts < 2000) return 2;
  if (watts < 5000) return 3;
  return 4;
}
