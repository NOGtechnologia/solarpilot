import { describe, expect, it } from "vitest";

import { fmtEnergy, fmtPct, fmtPower, localToday, shiftDate } from "./format";

describe("fmtPower", () => {
  it("zeigt W unter 1 kW und kW darüber", () => {
    expect(fmtPower(532, "de")).toEqual({ value: "532", unit: "W" });
    expect(fmtPower(5432, "de")).toEqual({ value: "5,43", unit: "kW" });
    expect(fmtPower(12345, "en")).toEqual({ value: "12.3", unit: "kW" });
    expect(fmtPower(-2500, "de")).toEqual({ value: "-2,50", unit: "kW" });
  });
  it("behandelt fehlende Werte", () => {
    expect(fmtPower(null, "de")).toEqual({ value: "–", unit: "" });
    expect(fmtPower(Number.NaN, "de").value).toBe("–");
  });
});

describe("fmtEnergy", () => {
  it("wählt passende Einheit", () => {
    expect(fmtEnergy(800, "de")).toEqual({ value: "800", unit: "Wh" });
    expect(fmtEnergy(12_345, "de")).toEqual({ value: "12,3", unit: "kWh" });
    expect(fmtEnergy(250_000, "en")).toEqual({ value: "250", unit: "kWh" });
    expect(fmtEnergy(9_800_000, "de")).toEqual({ value: "9,80", unit: "MWh" });
  });
});

describe("Datum", () => {
  it("verschiebt Tage", () => {
    expect(shiftDate("2026-03-01", -1)).toBe("2026-02-28");
    expect(shiftDate("2026-12-31", 1)).toBe("2027-01-01");
  });
  it("berechnet heute in einer Zeitzone", () => {
    const t = new Date("2026-10-18T23:30:00Z");
    expect(localToday("Europe/Berlin", t)).toBe("2026-10-19");
    expect(localToday("America/Los_Angeles", t)).toBe("2026-10-18");
  });
  it("formatiert Prozent", () => {
    expect(fmtPct(57.4, "de")).toBe("57 %");
    expect(fmtPct(null, "de")).toBe("–");
  });
});
