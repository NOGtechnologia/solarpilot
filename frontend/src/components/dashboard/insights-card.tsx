"use client";

import { AlertTriangle, BatteryFull, Car, Info, Lightbulb, Sparkles, WashingMachine, Zap } from "lucide-react";

import { Card, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/form";
import { fmtNumber, fmtRelative, fmtTime } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { Insight } from "@/lib/types";
import { cn } from "@/lib/utils";

const ICONS: Record<string, typeof Info> = {
  "insight.surplus": WashingMachine,
  "insight.battery_full": BatteryFull,
  "insight.ev": Car,
  "insight.underperformance": AlertTriangle,
  "insight.offline": AlertTriangle,
  "insight.cheap_power": Zap,
  "insight.expensive_now": Zap,
};

export function insightText(i: Insight, t: (k: string, p?: Record<string, unknown>) => string, lang: "de" | "en", tz?: string) {
  const p: Record<string, unknown> = { ...i.params };
  p.start = fmtTime(i.start, lang, tz);
  p.end = fmtTime(i.end, lang, tz);
  if (typeof p.kw === "number") p.kw = fmtNumber(p.kw, lang, 1);
  if (typeof p.ct === "number") p.ct = fmtNumber(p.ct, lang, 1);
  if (i.key === "insight.surplus") p.day = t(`insight.surplus.${i.params.day ?? "today"}`);
  if (i.key === "insight.offline") {
    p.since = i.start ? ` (${fmtRelative(i.start, lang)})` : "";
    p.error = i.params.error ?? "";
  }
  return t(i.key, p);
}

export function InsightsCard({
  data,
  timeZone,
}: {
  data: { items: Insight[]; summary: { text: string; created_at: number } | null } | undefined;
  timeZone?: string;
}) {
  const { t, lang } = useI18n();
  return (
    <Card>
      <CardHeader title={t("insights.title")} icon={<Lightbulb size={14} />} />
      {!data ? (
        <div className="space-y-2">
          <Skeleton className="h-14" />
          <Skeleton className="h-14" />
        </div>
      ) : (
        <div className="space-y-2">
          {data.summary?.text && (
            <div className="rounded-xl border border-grid-export/30 bg-grid-export/10 p-3 text-sm">
              <div className="mb-1 flex items-center gap-1.5 text-[12px] font-medium text-grid-export">
                <Sparkles size={13} /> {t("insights.ai")}
              </div>
              <p className="leading-relaxed">{data.summary.text}</p>
            </div>
          )}
          {!data.items.length && !data.summary?.text && <p className="text-sm text-muted">{t("insights.none")}</p>}
          <ul className="space-y-2">
            {data.items.slice(0, 6).map((i) => {
              const Icon = ICONS[i.key] ?? Info;
              return (
                <li
                  key={i.id}
                  className={cn(
                    "flex items-start gap-3 rounded-xl border p-3 text-sm leading-snug",
                    i.kind === "warning" ? "border-danger/30 bg-danger/5" : "border-border bg-card-2",
                  )}
                >
                  <span
                    className={cn(
                      "mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg",
                      i.kind === "warning" ? "bg-danger/15 text-danger" : i.kind === "tip" ? "bg-solar/15 text-solar-text" : "bg-load/15 text-load",
                    )}
                  >
                    <Icon size={15} aria-hidden />
                  </span>
                  <span>{insightText(i, t, lang, timeZone)}</span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </Card>
  );
}
