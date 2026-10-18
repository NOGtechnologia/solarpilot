import { describe, expect, it } from "vitest";

import de from "./de";
import en from "./en";
import { translate } from "./index";

describe("i18n", () => {
  it("de und en haben dieselben Schlüssel", () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(de).sort());
  });
  it("Platzhalter werden in beiden Sprachen gleich verwendet", () => {
    const ph = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort().join(",");
    for (const k of Object.keys(de) as (keyof typeof de)[]) {
      expect(ph(en[k]), k).toBe(ph(de[k]));
    }
  });
  it("ersetzt Parameter und fällt auf Deutsch bzw. den Schlüssel zurück", () => {
    expect(translate("de", "kpi.of_forecast", { pct: "80 %" })).toBe("80 % der Prognose");
    expect(translate("en", "kpi.of_forecast", { pct: "80 %" })).toBe("80 % of forecast");
    expect(translate("en", "gibt.es.nicht")).toBe("gibt.es.nicht");
  });
});
