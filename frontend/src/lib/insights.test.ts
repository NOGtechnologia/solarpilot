import { describe, expect, it } from "vitest";

import { insightText } from "@/components/dashboard/insights-card";
import { heroGradient } from "@/components/dashboard/hero";
import { priceColor } from "@/components/dashboard/price-chart";

import { translate } from "./i18n";
import type { Insight } from "./types";
import { COLORS } from "./utils";

const t = (k: string, p?: Record<string, unknown>) => translate("de", k, p);

describe("insightText", () => {
  it("formatiert Überschuss-Tipp mit Uhrzeiten in der Zeitzone der Anlage", () => {
    const i: Insight = {
      id: "x",
      kind: "tip",
      key: "insight.surplus",
      params: { day: "today", kw: 3.74, kwh: 20, site: "Haus" },
      site_id: 1,
      start: Date.UTC(2026, 5, 21, 8) / 1000, // 10:00 MESZ
      end: Date.UTC(2026, 5, 21, 13) / 1000, // 15:00 MESZ
      priority: 10,
    };
    expect(insightText(i, t, "de", "Europe/Berlin")).toBe(
      "Heute 10:00–15:00 Uhr ca. 3,7 kW Überschuss → Waschmaschine, Spülmaschine oder E-Auto laden.",
    );
  });
  it("Offline-Hinweis ohne Fehlertext", () => {
    const i: Insight = { id: "o", kind: "warning", key: "insight.offline", params: { device: "WR", error: null }, site_id: 1, start: null, end: null, priority: 2 };
    expect(insightText(i, t, "de")).toBe("WR ist offline. ");
  });
});

describe("Farben", () => {
  it("Preisfarbe: günstig grün, teuer orange", () => {
    expect(priceColor(5, 5, 30)).toBe(COLORS.battery);
    expect(priceColor(29, 5, 30)).toBe(COLORS.gridImport);
    expect(priceColor(10, 10, 10)).toBe(COLORS.battery);
  });
  it("Kopf-Verlauf ändert sich mit Tageszeit", () => {
    expect(heroGradient(-20, 0)).toContain("76, 61, 160");
    expect(heroGradient(3, 0)).toContain("249, 115, 22");
    expect(heroGradient(40, 0)).toContain("245, 165, 36");
  });
});
