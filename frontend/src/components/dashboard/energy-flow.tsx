"use client";

import { motion, useReducedMotion } from "framer-motion";
import { HouseLine, PlugsConnected, SolarPanel } from "@phosphor-icons/react";
import type { ReactNode } from "react";

import { flowDots, flowDuration, flows, type NodeId } from "@/lib/flow";
import { fmtPower } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { Snapshot } from "@/lib/types";
import { COLORS } from "@/lib/utils";

import { BatteryLiquid } from "./battery-liquid";

const W = 360;
const H = 300;
const HUB = { x: W / 2, y: 150 };
const POS: Record<NodeId, { x: number; y: number }> = {
  pv: { x: W / 2, y: 46 },
  grid: { x: 52, y: 150 },
  home: { x: W - 52, y: 150 },
  battery: { x: W / 2, y: 254 },
};
const R = 34;

function edge(from: NodeId | "hub", to: NodeId | "hub") {
  const a = from === "hub" ? HUB : POS[from];
  const b = to === "hub" ? HUB : POS[to];
  // Linie am Kreisrand beginnen/enden lassen
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy) || 1;
  const ra = from === "hub" ? 6 : R + 4;
  const rb = to === "hub" ? 6 : R + 4;
  return {
    x1: a.x + (dx / len) * ra,
    y1: a.y + (dy / len) * ra,
    x2: b.x - (dx / len) * rb,
    y2: b.y - (dy / len) * rb,
  };
}

function Node({
  id,
  color,
  icon,
  active,
}: {
  id: NodeId;
  color: string;
  icon: ReactNode;
  active: boolean;
}) {
  const p = POS[id];
  return (
    <g>
      {active && <circle cx={p.x} cy={p.y} r={R + 8} fill={color} opacity={0.12} />}
      <circle cx={p.x} cy={p.y} r={R} fill="var(--card-2)" stroke={color} strokeWidth={active ? 2.5 : 1.5} />
      <foreignObject x={p.x - 17} y={p.y - 17} width={34} height={34}>
        <div style={{ color, display: "flex", width: 34, height: 34, alignItems: "center", justifyContent: "center" }}>{icon}</div>
      </foreignObject>
    </g>
  );
}

function Label({ id, title, value, sub, color }: { id: NodeId; title: string; value: string; sub?: string; color: string }) {
  const p = POS[id];
  // PV und Batterie: Beschriftung rechts (die Leitung zum Zentrum verläuft senkrecht)
  const side = id === "pv" || id === "battery";
  const x = side ? p.x + R + 14 : p.x;
  const y = side ? p.y - (sub ? 14 : 8) : p.y + R + 18;
  return (
    <g textAnchor={side ? "start" : "middle"}>
      <text x={x} y={y} fontSize={11} fill="var(--muted)">
        {title}
      </text>
      <text x={x} y={y + 17} fontSize={15} fontWeight={600} fill={color} className="num">
        {value}
      </text>
      {sub && (
        <text x={x} y={y + 31} fontSize={10.5} fill="var(--muted)">
          {sub}
        </text>
      )}
    </g>
  );
}

export function EnergyFlow({ snapshot }: { snapshot: Snapshot | null | undefined }) {
  const { t, lang } = useI18n();
  const reduce = useReducedMotion();
  const fl = flows(snapshot, COLORS);
  const pv = snapshot?.pv_power_w ?? 0;
  const grid = snapshot?.grid_power_w ?? 0;
  const batt = snapshot?.battery_power_w;
  const soc = snapshot?.battery_soc_pct;
  const load = snapshot?.load_power_w;
  const p = (w: number | null | undefined) => {
    const f = fmtPower(w === null || w === undefined ? null : Math.abs(w), lang);
    return `${f.value} ${f.unit}`.trim();
  };
  const gridColor = grid < 0 ? COLORS.gridExport : COLORS.gridImport;
  const hasBattery = batt !== null && batt !== undefined;

  const aria = t("flow.aria", { pv: p(pv), home: p(load), battery: hasBattery ? p(batt) : "–", grid: p(grid) });

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mx-auto h-auto w-full max-w-[460px]" role="img" aria-label={aria}>
      {/* Leitungen */}
      {(["pv", "grid", "home", ...(hasBattery ? (["battery"] as const) : [])] as NodeId[]).map((n) => {
        const e = edge(n, "hub");
        return (
          <line key={n} {...e} stroke="var(--border)" strokeWidth={3} strokeLinecap="round" />
        );
      })}
      <circle cx={HUB.x} cy={HUB.y} r={5} fill="var(--muted)" opacity={0.6} />

      {/* Fließende Punkte */}
      {fl.map((f) => {
        const e = edge(f.from, f.to);
        const dur = flowDuration(f.watts);
        const n = flowDots(f.watts);
        const key = `${f.from}-${f.to}`;
        if (reduce) {
          const mx = (e.x1 + e.x2) / 2;
          const my = (e.y1 + e.y2) / 2;
          return <circle key={key} cx={mx} cy={my} r={4} fill={f.color} />;
        }
        return (
          <g key={key}>
            <line {...e} stroke={f.color} strokeWidth={3} strokeLinecap="round" opacity={0.35} />
            {Array.from({ length: n }).map((_, i) => (
              <motion.circle
                key={i}
                r={4.5}
                fill={f.color}
                style={{ filter: `drop-shadow(0 0 4px ${f.color})` }}
                initial={{ cx: e.x1, cy: e.y1, opacity: 0 }}
                animate={{ cx: [e.x1, e.x2], cy: [e.y1, e.y2], opacity: [0, 1, 1, 0] }}
                transition={{
                  duration: dur,
                  repeat: Infinity,
                  ease: "linear",
                  delay: (i * dur) / n,
                  times: [0, 1],
                  opacity: { duration: dur, repeat: Infinity, delay: (i * dur) / n, times: [0, 0.1, 0.85, 1] },
                }}
              />
            ))}
          </g>
        );
      })}

      <Node id="pv" color={COLORS.solar} icon={<SolarPanel size={34} />} active={pv > 15} />
      <Node id="grid" color={gridColor} icon={<PlugsConnected size={32} />} active={Math.abs(grid) > 15} />
      <Node id="home" color={COLORS.load} icon={<HouseLine size={32} />} active={(load ?? 0) > 15} />
      {hasBattery && (
        <g>
          <circle cx={POS.battery.x} cy={POS.battery.y} r={R} fill="var(--card-2)" stroke={COLORS.battery} strokeWidth={Math.abs(batt ?? 0) > 15 ? 2.5 : 1.5} />
          <BatteryLiquid x={POS.battery.x - 13} y={POS.battery.y - 20} width={26} height={40} soc={soc ?? 0} />
        </g>
      )}

      <Label id="pv" title={t("flow.pv")} value={p(pv)} color={COLORS.solar} />
      <Label
        id="grid"
        title={grid < -15 ? t("flow.grid_export") : grid > 15 ? t("flow.grid_import") : t("flow.grid")}
        value={p(grid)}
        color={gridColor}
      />
      <Label id="home" title={t("flow.home")} value={p(load)} color={COLORS.load} />
      {hasBattery && (
        <Label
          id="battery"
          title={`${t("flow.battery")} · ${soc !== null && soc !== undefined ? Math.round(soc) : "–"} %`}
          value={p(batt)}
          color={COLORS.battery}
          sub={(batt ?? 0) > 15 ? t("flow.charging") : (batt ?? 0) < -15 ? t("flow.discharging") : t("flow.idle")}
        />
      )}
    </svg>
  );
}
