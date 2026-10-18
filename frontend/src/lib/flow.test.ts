import { describe, expect, it } from "vitest";

import { flowDots, flowDuration, flows } from "./flow";
import type { Snapshot } from "./types";
import { COLORS } from "./utils";

const snap = (s: Partial<Snapshot>): Snapshot => ({
  timestamp_utc: "2026-06-21T12:00:00Z",
  pv_power_w: 0,
  load_power_w: 0,
  grid_power_w: 0,
  battery_power_w: 0,
  battery_soc_pct: 50,
  energy_today_wh: 0,
  ...s,
});

describe("flows", () => {
  it("Mittag: PV versorgt Haus, lädt Batterie und speist ein", () => {
    const f = flows(snap({ pv_power_w: 6000, load_power_w: 800, battery_power_w: 2000, grid_power_w: -3200 }), COLORS);
    const keys = f.map((x) => `${x.from}>${x.to}`).sort();
    expect(keys).toEqual(["hub>battery", "hub>grid", "hub>home", "pv>hub"]);
    expect(f.find((x) => x.to === "grid")!.color).toBe(COLORS.gridExport);
  });
  it("Nacht: Batterie entlädt, Netzbezug", () => {
    const f = flows(snap({ load_power_w: 600, battery_power_w: -400, grid_power_w: 200 }), COLORS);
    expect(f.map((x) => `${x.from}>${x.to}`).sort()).toEqual(["battery>hub", "grid>hub", "hub>home"]);
    expect(f.find((x) => x.from === "grid")!.color).toBe(COLORS.gridImport);
  });
  it("ignoriert Rauschen und fehlende Daten", () => {
    expect(flows(snap({ pv_power_w: 5, load_power_w: 10 }), COLORS)).toEqual([]);
    expect(flows(null, COLORS)).toEqual([]);
  });
});

describe("Animation", () => {
  it("mehr Leistung = schneller und mehr Punkte", () => {
    expect(flowDuration(8000)).toBeLessThan(flowDuration(300));
    expect(flowDuration(1)).toBeLessThanOrEqual(4);
    expect(flowDuration(1e9)).toBeGreaterThanOrEqual(0.8);
    expect(flowDots(200)).toBe(1);
    expect(flowDots(6000)).toBe(4);
  });
});
