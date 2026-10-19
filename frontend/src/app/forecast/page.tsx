"use client";

import { CloudSun, Target, TrendUp } from "@phosphor-icons/react";
import { useCallback } from "react";

import { EChart, chartTheme } from "@/components/charts/echart";
import { KpiTile } from "@/components/dashboard/kpi-tile";
import { SiteSwitcher } from "@/components/dashboard/site-switcher";
import { WeatherCard } from "@/components/dashboard/weather-card";
import { useApp } from "@/components/providers";
import { Card, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/form";
import { fmtDate, fmtEnergy, fmtNumber } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { ForecastSite, WeatherResponse } from "@/lib/types";
import { useFetch } from "@/lib/use-fetch";
import { COLORS } from "@/lib/utils";

export default function ForecastPage() {
  const { t, lang } = useI18n();
  const { site, sites } = useApp();
  const hasSites = !!sites?.length;
  const primary = site === "all" ? sites?.[0] : sites?.find((s) => String(s.id) === site);
  const { data, loading } = useFetch<{ sites: ForecastSite[] }>(hasSites ? `/api/forecast?site=${site}` : null, 30 * 60_000);
  const weather = useFetch<WeatherResponse>(primary ? `/api/weather?site=${primary.id}` : null, 15 * 60_000);
  const tz = primary?.timezone;

  // Mehrere Sites zu einer Kurve addieren
  const merged = (() => {
    const pts = new Map<number, { w: number; cloud: number | null }>();
    const daily = new Map<string, { wh: number; second: number | null }>();
    const acc = new Map<string, { actual: number; fc: number | null }>();
    for (const s of data?.sites ?? []) {
      for (const p of s.points) {
        const cur = pts.get(p.ts) ?? { w: 0, cloud: p.cloud_cover };
        cur.w += p.power_w;
        pts.set(p.ts, cur);
      }
      for (const d of s.daily) {
        const cur = daily.get(d.day) ?? { wh: 0, second: null };
        cur.wh += d.energy_wh;
        if (d.forecast_solar_wh != null) cur.second = (cur.second ?? 0) + d.forecast_solar_wh;
        daily.set(d.day, cur);
      }
      for (const a of s.accuracy_history) {
        const cur = acc.get(a.day) ?? { actual: 0, fc: null };
        cur.actual += a.actual_wh;
        if (a.forecast_wh != null) cur.fc = (cur.fc ?? 0) + a.forecast_wh;
        acc.set(a.day, cur);
      }
    }
    return {
      points: [...pts.entries()].sort((a, b) => a[0] - b[0]),
      daily: [...daily.entries()].sort(),
      acc: [...acc.entries()].sort(),
    };
  })();
  const correction = data?.sites.length === 1 ? data.sites[0].correction : undefined;
  const accuracy = data?.sites.map((s) => s.correction?.accuracy_pct).filter((v): v is number => v != null);
  const noArrays = data?.sites.every((s) => s.error === "no_arrays");

  const hourlyOption = useCallback(
    (dark: boolean) => {
      const c = chartTheme(dark);
      const now = Date.now();
      const future = merged.points.filter(([ts]) => (ts + 3600) * 1000 >= now - 6 * 3600_000);
      return {
        grid: { left: 8, right: 36, top: 52, bottom: 8, containLabel: true },
        legend: { top: 0, left: 0, textStyle: { color: c.text, fontSize: 11 }, itemWidth: 10, itemHeight: 10, icon: "roundRect" },
        tooltip: { trigger: "axis", backgroundColor: c.tooltipBg, borderColor: c.tooltipBorder, textStyle: { color: c.fg, fontSize: 12 }, confine: true },
        xAxis: {
          type: "time",
          axisLine: { lineStyle: { color: c.grid } },
          axisLabel: { color: c.text, fontSize: 11, hideOverlap: true, formatter: (v: number) => fmtDate(v / 1000, lang, { weekday: "short", day: "2-digit" }, tz) },
          splitLine: { show: false },
        },
        yAxis: [
          { type: "value", name: "kW", nameTextStyle: { color: c.text, fontSize: 10 }, axisLabel: { color: c.text, fontSize: 11, formatter: (v: number) => fmtNumber(v / 1000, lang, 0) }, splitLine: { lineStyle: { color: c.grid } } },
          { type: "value", min: 0, max: 100, axisLabel: { color: c.text, fontSize: 11, formatter: "{value}%" }, splitLine: { show: false } },
        ],
        series: [
          {
            name: t("chart.forecast"),
            type: "line",
            showSymbol: false,
            smooth: 0.4,
            data: future.map(([ts, v]) => [(ts + 1800) * 1000, Math.round(v.w)]),
            lineStyle: { color: COLORS.solar, width: 2 },
            itemStyle: { color: COLORS.solar },
            areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: `${COLORS.solar}66` }, { offset: 1, color: `${COLORS.solar}05` }] } },
            tooltip: { valueFormatter: (v: unknown) => (typeof v === "number" ? `${fmtNumber(v / 1000, lang, 2)} kW` : "–") },
            markLine: { symbol: "none", silent: true, label: { show: false }, lineStyle: { color: c.fg, opacity: 0.4, type: "solid" }, data: [{ xAxis: now }] },
          },
          {
            name: t("weather.clouds"),
            type: "line",
            yAxisIndex: 1,
            showSymbol: false,
            data: future.map(([ts, v]) => [(ts + 1800) * 1000, v.cloud]),
            lineStyle: { color: c.text, width: 1, type: "dotted" },
            itemStyle: { color: c.text },
            tooltip: { valueFormatter: (v: unknown) => (typeof v === "number" ? `${v} %` : "–") },
          },
        ],
      };
    },
    [merged.points, lang, t, tz],
  );

  const accOption = useCallback(
    (dark: boolean) => {
      const c = chartTheme(dark);
      return {
        grid: { left: 8, right: 8, top: 52, bottom: 8, containLabel: true },
        legend: { top: 0, left: 0, textStyle: { color: c.text, fontSize: 11 }, itemWidth: 10, itemHeight: 10, icon: "roundRect" },
        tooltip: {
          trigger: "axis",
          backgroundColor: c.tooltipBg,
          borderColor: c.tooltipBorder,
          textStyle: { color: c.fg, fontSize: 12 },
          valueFormatter: (v: unknown) => (typeof v === "number" ? `${fmtNumber(v, lang, 1)} kWh` : "–"),
        },
        xAxis: { type: "category", data: merged.acc.map(([d]) => fmtDate(d, lang)), axisLabel: { color: c.text, fontSize: 10 }, axisLine: { lineStyle: { color: c.grid } }, axisTick: { show: false } },
        yAxis: { type: "value", name: "kWh", nameTextStyle: { color: c.text, fontSize: 10 }, axisLabel: { color: c.text, fontSize: 11 }, splitLine: { lineStyle: { color: c.grid } } },
        series: [
          { name: t("forecast.actual"), type: "bar", data: merged.acc.map(([, v]) => +(v.actual / 1000).toFixed(2)), itemStyle: { color: COLORS.solar, borderRadius: [3, 3, 0, 0] }, barMaxWidth: 14 },
          { name: t("chart.forecast"), type: "line", data: merged.acc.map(([, v]) => (v.fc != null ? +(v.fc / 1000).toFixed(2) : null)), showSymbol: false, lineStyle: { color: c.fg, type: "dashed", width: 1.5 }, itemStyle: { color: c.fg } },
        ],
      };
    },
    [merged.acc, lang, t],
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("forecast.title")}</h1>
          <p className="text-sm text-muted">{t("forecast.subtitle")}</p>
        </div>
        <SiteSwitcher />
      </div>

      {noArrays ? (
        <Card>
          <p className="text-sm text-muted">{t("forecast.no_arrays")}</p>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {merged.daily.slice(0, 2).map(([day, v], i) => {
              const e = fmtEnergy(v.wh, lang);
              return (
                <KpiTile
                  key={day}
                  label={i === 0 ? t("common.today") : t("common.tomorrow")}
                  icon={<CloudSun size={14} />}
                  accent={COLORS.solar}
                  value={e.value}
                  unit={e.unit}
                  sub={v.second != null ? `${t("forecast.second_opinion")}: ${fmtEnergy(v.second, lang).value} ${fmtEnergy(v.second, lang).unit}` : undefined}
                />
              );
            })}
            <KpiTile
              label={t("forecast.accuracy")}
              icon={<Target size={14} />}
              accent={COLORS.battery}
              value={accuracy?.length ? fmtNumber(accuracy.reduce((a, b) => a + b, 0) / accuracy.length, lang) : "–"}
              unit={accuracy?.length ? "%" : undefined}
              sub={accuracy?.length ? t("forecast.accuracy_hint") : t("forecast.need_days")}
            />
            <KpiTile
              label={t("forecast.correction")}
              icon={<TrendUp size={14} />}
              accent={COLORS.load}
              value={correction ? `× ${fmtNumber(correction.factor, lang, 2)}` : "–"}
              sub={correction ? `${correction.days} d` : undefined}
            />
          </div>

          <Card>
            <CardHeader title={t("forecast.hourly")} />
            {loading && !data ? <Skeleton className="h-72" /> : <EChart option={hourlyOption} height={290} ariaLabel={t("forecast.hourly")} />}
          </Card>

          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader title={t("forecast.vs_actual")} />
              {loading && !data ? <Skeleton className="h-64" /> : <EChart option={accOption} height={260} ariaLabel={t("forecast.vs_actual")} />}
            </Card>
            <WeatherCard data={weather.data} forecast={data?.sites.find((s) => s.site_id === primary?.id)} timeZone={tz} />
          </div>

          <Card>
            <CardHeader title={t("forecast.daily")} />
            <ul className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-7">
              {merged.daily.map(([day, v]) => {
                const e = fmtEnergy(v.wh, lang);
                return (
                  <li key={day} className="rounded-xl bg-card-2 p-3">
                    <div className="text-[12px] text-muted">{fmtDate(day, lang, { weekday: "short", day: "2-digit", month: "2-digit" })}</div>
                    <div className="num mt-1 text-lg font-semibold">
                      {e.value} <span className="text-xs font-normal text-muted">{e.unit}</span>
                    </div>
                  </li>
                );
              })}
            </ul>
          </Card>
        </>
      )}
    </div>
  );
}
