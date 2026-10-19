"use client";

import { Lightning } from "@phosphor-icons/react";
import { useCallback } from "react";

import { EChart, chartTheme } from "@/components/charts/echart";
import { Card, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/form";
import { fmtNumber, fmtTime } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { PricesResponse } from "@/lib/types";
import { COLORS } from "@/lib/utils";

export function priceColor(ct: number, min: number, max: number): string {
  if (max <= min) return COLORS.battery;
  const f = (ct - min) / (max - min);
  if (f < 0.33) return COLORS.battery;
  if (f < 0.66) return COLORS.solar;
  return COLORS.gridImport;
}

export function PriceChart({ data }: { data: PricesResponse | undefined }) {
  const { t, lang } = useI18n();

  const option = useCallback(
    (dark: boolean) => {
      if (!data?.points.length) return {};
      const c = chartTheme(dark);
      const vals = data.points.map((p) => p.ct_kwh);
      const min = Math.min(...vals);
      const max = Math.max(...vals);
      const now = Date.now();
      return {
        grid: { left: 4, right: 8, top: 12, bottom: 4, containLabel: true },
        tooltip: {
          trigger: "axis",
          backgroundColor: c.tooltipBg,
          borderColor: c.tooltipBorder,
          textStyle: { color: c.fg, fontSize: 12 },
          valueFormatter: (v: unknown) => (typeof v === "number" ? `${fmtNumber(v, lang, 1)} ct/kWh` : "–"),
          axisPointer: { type: "shadow" },
        },
        xAxis: {
          type: "time",
          axisLine: { lineStyle: { color: c.grid } },
          axisTick: { show: false },
          axisLabel: { color: c.text, fontSize: 10, hideOverlap: true, formatter: (v: number) => fmtTime(v / 1000, lang) },
          splitLine: { show: false },
        },
        yAxis: {
          type: "value",
          axisLabel: { color: c.text, fontSize: 10 },
          splitLine: { lineStyle: { color: c.grid } },
        },
        series: [
          {
            type: "bar",
            name: t("prices.title"),
            barWidth: "70%",
            data: data.points.map((p) => ({
              value: [(p.ts + p.duration_s / 2) * 1000, p.ct_kwh],
              itemStyle: {
                color: priceColor(p.ct_kwh, min, max),
                opacity: (p.ts + p.duration_s) * 1000 < now ? 0.35 : 1,
                borderRadius: [2, 2, 0, 0],
              },
            })),
            markLine: {
              symbol: "none",
              silent: true,
              label: { show: false },
              lineStyle: { color: c.fg, opacity: 0.5, type: "solid", width: 1 },
              data: [{ xAxis: now }],
            },
          },
        ],
      };
    },
    [data, lang, t],
  );

  return (
    <Card>
      <CardHeader title={t("prices.title")} icon={<Lightning size={14} />} action={data?.zone ? <span className="text-[11px] text-muted">{data.zone}</span> : null} />
      {!data ? (
        <Skeleton className="h-48" />
      ) : !data.points.length ? (
        <p className="py-8 text-center text-sm text-muted">{t("prices.none")}</p>
      ) : (
        <>
          <div className="mb-2 grid grid-cols-3 gap-2 text-center">
            {[
              { k: "prices.now", p: data.current, c: "text-fg" },
              { k: "prices.cheapest", p: data.cheapest, c: "text-success" },
              { k: "prices.expensive", p: data.most_expensive, c: "text-grid-import" },
            ].map(({ k, p, c }) => (
              <div key={k} className="rounded-xl bg-card-2 px-2 py-2">
                <div className="text-[11px] text-muted">{t(k)}</div>
                <div className={`num text-lg font-semibold ${c}`}>{p ? fmtNumber(p.ct_kwh, lang, 1) : "–"}</div>
                <div className="num text-[10px] text-muted">{p && k !== "prices.now" ? fmtTime(p.ts, lang) : t("prices.unit")}</div>
              </div>
            ))}
          </div>
          <EChart option={option} height={170} ariaLabel={t("prices.title")} />
          <p className="mt-1 text-[11px] text-muted">{t("prices.hint")}</p>
        </>
      )}
    </Card>
  );
}
