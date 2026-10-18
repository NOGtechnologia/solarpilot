"use client";

import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/form";
import { useI18n } from "@/lib/i18n";
import type { PvArray } from "@/lib/types";
import { cn } from "@/lib/utils";

const PRESETS = [
  { key: "setup.east", az: 90 },
  { key: "setup.south", az: 180 },
  { key: "setup.west", az: 270 },
];

export function ArraysEditor({ arrays, onChange }: { arrays: PvArray[]; onChange: (a: PvArray[]) => void }) {
  const { t } = useI18n();
  const update = (i: number, patch: Partial<PvArray>) => onChange(arrays.map((a, j) => (i === j ? { ...a, ...patch } : a)));
  return (
    <div className="space-y-3">
      {arrays.map((a, i) => (
        <div key={i} className="rounded-xl border border-border bg-card-2 p-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-[1fr_1fr_1fr_auto]">
            <Field label={t("setup.kwp")} htmlFor={`kwp-${i}`}>
              <Input id={`kwp-${i}`} type="number" step="0.01" min="0" inputMode="decimal" value={a.kwp} onChange={(e) => update(i, { kwp: Number(e.target.value) })} />
            </Field>
            <Field label={t("setup.tilt")} htmlFor={`tilt-${i}`}>
              <Input id={`tilt-${i}`} type="number" min="0" max="90" value={a.tilt} onChange={(e) => update(i, { tilt: Number(e.target.value) })} />
            </Field>
            <Field label={t("setup.azimuth")} htmlFor={`az-${i}`} className="col-span-2 sm:col-span-1">
              <Input id={`az-${i}`} type="number" min="0" max="359" value={a.azimuth} onChange={(e) => update(i, { azimuth: Number(e.target.value) % 360 })} />
            </Field>
            <div className="col-span-2 flex items-end justify-between gap-2 sm:col-span-1">
              <div className="flex gap-1">
                {PRESETS.map((p) => (
                  <button
                    key={p.az}
                    type="button"
                    onClick={() => update(i, { azimuth: p.az })}
                    className={cn(
                      "h-10 cursor-pointer rounded-lg border px-2 text-xs",
                      a.azimuth === p.az ? "border-solar bg-solar/15" : "border-border text-muted",
                    )}
                  >
                    {t(p.key)}
                  </button>
                ))}
              </div>
              {arrays.length > 1 && (
                <Button size="icon" variant="ghost" aria-label={t("common.delete")} onClick={() => onChange(arrays.filter((_, j) => j !== i))}>
                  <Trash2 size={16} />
                </Button>
              )}
            </div>
          </div>
        </div>
      ))}
      <p className="text-xs text-muted">{t("setup.azimuth_hint")}</p>
      <Button size="sm" onClick={() => onChange([...arrays, { kwp: 1, tilt: 30, azimuth: 180, losses_pct: 14 }])}>
        <Plus size={14} /> {t("setup.add_array")}
      </Button>
    </div>
  );
}
