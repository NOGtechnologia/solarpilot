"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useMemo, useState } from "react";

import { EChart, chartTheme, type EChartsOption } from "@/components/charts/echart";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Segmented, Skeleton } from "@/components/ui/form";
import { fmtDate, fmtNumber, isoDate, localToday, shiftDate, type Lang } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { HistoryResponse } from "@/lib/types";
import { useFetch } from "@/lib/use-fetch";
import { COLORS } from "@/lib/utils";

type Range = "day" | "week" | "month" | "year";

function tooltipBase(dark: boolean) {
  const c = chartTheme(dark);
  return {
    trigger: "axis" as const,
    backgroundColor: c.tooltipBg,
    borderColor: c.tooltipBorder,
    textStyle: { color: c.fg, fontSize: 12 },
    confine: true,
  };
}

function axisBase(dark: boolean) {
  const c = chartTheme(dark);
  return {
    axisLine: { lineStyle: { color: c.grid } },
    axisTick: { show: false },
    axisLabel: { color: c.text, fontSize: 11 },
    splitLine: { lineStyle: { color: c.grid } },
  };
}

export function powerOption(
  h: HistoryResponse,
  lang: Lang,
  t: (k: string) => string,
  timeZone: string | undefined,
  dark: boolean,
): EChartsOption {
  const s = h.series!;
  const ms = (ts: number) => ts * 1000;
  const pv = s.ts.map((t0, i) => [ms(t0), s.pv[i]]);
  const load = s.ts.map((t0, i) => [ms(t0), s.load[i]]);
  const imp = s.ts.map((t0, i) => [ms(t0), s.grid[i] !== null ? Math.max(s.grid[i]!, 0) : null]);
  const exp = s.ts.map((t0, i) => [ms(t0), s.grid[i] !== null ? Math.min(s.grid[i]!, 0) : null]);
  const batt = s.ts.map((t0, i) => [ms(t0), s.battery[i]]);
  const soc = s.ts.map((t0, i) => [ms(t0), s.soc[i]]);
  const fc = (h.forecast?.ts ?? []).map((t0, i) => [ms(t0), h.forecast!.pv[i]]);
  const hasSoc = s.soc.some((v) => v !== null);
  const kw = (v: number) => `${fmtNumber(v / 1000, lang, 1)} kW`;
  const area = (color: string) => ({
    color: {
      type: "linear",
      x: 0,
      y: 0,
      x2: 0,
      y2: 1,
      colorStops: [
        { offset: 0, color: `${color}66` },
        { offset: 1, color: `${color}05` },
      ],
    },
  });
  const c = chartTheme(dark);
  const line = { showSymbol: false, smooth: 0.3, sampling: "lttb" as const };
  const fmtAxisTime = (v: number) =>
    h.range === "day"
      ? fmtDate(v / 1000, lang, { hour: "2-digit", minute: "2-digit" }, timeZone)
      : fmtDate(v / 1000, lang, { weekday: "short", day: "2-digit" }, timeZone);
  return {
    grid: { left: 8, right: hasSoc ? 36 : 8, top: 52, bottom: 8, containLabel: true },
    legend: {
      top: 0,
      left: 0,
      itemWidth: 10,
      itemHeight: 10,
      icon: "roundRect",
      textStyle: { color: c.text, fontSize: 11 },
    },
    tooltip: {
      ...tooltipBase(dark),
      valueFormatter: (v: unknown) => (typeof v === "number" ? kw(v) : "–"),
      axisPointer: { type: "line", lineStyle: { color: c.text, opacity: 0.4 } },
    },
    xAxis: { type: "time", ...axisBase(dark), splitLine: { show: false }, axisLabel: { ...axisBase(dark).axisLabel, formatter: fmtAxisTime, hideOverlap: true } },
    yAxis: [
      { type: "value", ...axisBase(dark), axisLabel: { ...axisBase(dark).axisLabel, formatter: (v: number) => fmtNumber(v / 1000, lang, 0) }, name: "kW", nameTextStyle: { color: c.text, fontSize: 10 } },
      ...(hasSoc
        ? [{ type: "value", min: 0, max: 100, ...axisBase(dark), splitLine: { show: false }, axisLabel: { ...axisBase(dark).axisLabel, formatter: "{value}%" } }]
        : []),
    ],
    series: [
      { name: t("chart.pv"), type: "line", data: pv, ...line, lineStyle: { width: 2, color: COLORS.solar }, itemStyle: { color: COLORS.solar }, areaStyle: area(COLORS.solar), z: 3 },
      { name: t("chart.load"), type: "line", data: load, ...line, lineStyle: { width: 2, color: COLORS.load }, itemStyle: { color: COLORS.load }, z: 4 },
      { name: t("chart.grid_import"), type: "line", data: imp, ...line, lineStyle: { width: 1, color: COLORS.gridImport }, itemStyle: { color: COLORS.gridImport }, areaStyle: { color: `${COLORS.gridImport}33` } },
      { name: t("chart.grid_export"), type: "line", data: exp, ...line, lineStyle: { width: 1, color: COLORS.gridExport }, itemStyle: { color: COLORS.gridExport }, areaStyle: { color: `${COLORS.gridExport}33` } },
      { name: t("chart.battery"), type: "line", data: batt, ...line, lineStyle: { width: 1.5, color: COLORS.battery }, itemStyle: { color: COLORS.battery } },
      ...(fc.length
        ? [{ name: t("chart.forecast"), type: "line", data: fc, showSymbol: false, smooth: 0.4, lineStyle: { width: 1.5, type: "dashed", color: COLORS.solar, opacity: 0.8 }, itemStyle: { color: COLORS.solar } }]
        : []),
      ...(hasSoc
        ? [{ name: t("chart.soc"), type: "line", yAxisIndex: 1, data: soc, ...line, lineStyle: { width: 1, type: "dotted", color: COLORS.battery }, itemStyle: { color: COLORS.battery }, tooltip: { valueFormatter: (v: unknown) => (typeof v === "number" ? `${Math.round(v)} %` : "–") } }]
        : []),
    ],
  };
}

export function energyOption(h: HistoryResponse, lang: Lang, t: (k: string) => string, dark: boolean): EChartsOption {
  const e = h.energy!;
  const c = chartTheme(dark);
  const labels = e.labels.map((l) =>
    h.range === "year"
      ? fmtDate(`${l}-15`, lang, { month: "short" })
      : fmtDate(l, lang, h.range === "week" ? { weekday: "short", day: "2-digit" } : { day: "2-digit" }),
  );
  const kwh = (v: unknown) => (typeof v === "number" ? `${fmtNumber(v, lang, 1)} kWh` : "–");
  return {
    grid: { left: 8, right: 8, top: 52, bottom: 8, containLabel: true },
    legend: { top: 0, left: 0, itemWidth: 10, itemHeight: 10, icon: "roundRect", textStyle: { color: c.text, fontSize: 11 } },
    tooltip: { ...tooltipBase(dark), valueFormatter: kwh, axisPointer: { type: "shadow" } },
    xAxis: { type: "category", data: labels, ...axisBase(dark), splitLine: { show: false } },
    yAxis: { type: "value", ...axisBase(dark), name: "kWh", nameTextStyle: { color: c.text, fontSize: 10 } },
    series: [
      { name: t("chart.pv"), type: "bar", data: e.pv_kwh, itemStyle: { color: COLORS.solar, borderRadius: [4, 4, 0, 0] }, barMaxWidth: 18 },
      { name: t("chart.load"), type: "bar", data: e.load_kwh, itemStyle: { color: COLORS.load, borderRadius: [4, 4, 0, 0] }, barMaxWidth: 18 },
      { name: t("chart.grid_import"), type: "line", data: e.import_kwh, showSymbol: false, lineStyle: { color: COLORS.gridImport, width: 1.5 }, itemStyle: { color: COLORS.gridImport } },
      { name: t("chart.grid_export"), type: "line", data: e.export_kwh, showSymbol: false, lineStyle: { color: COLORS.gridExport, width: 1.5 }, itemStyle: { color: COLORS.gridExport } },
      ...(e.forecast_kwh.some((v) => v !== null)
        ? [{ name: t("chart.forecast"), type: "line", data: e.forecast_kwh, showSymbol: false, lineStyle: { color: COLORS.solar, type: "dashed", width: 1.5 }, itemStyle: { color: COLORS.solar } }]
        : []),
    ],
  };
}

export function HistoryChart({ site, timeZone }: { site: string; timeZone?: string }) {
  const { t, lang } = useI18n();
  const [range, setRange] = useState<Range>("day");
  // null = „heute“ in der Zeitzone der Anlage (bestimmt das Backend)
  const [picked, setPicked] = useState<string | null>(null);
  const today = useMemo(() => localToday(timeZone), [timeZone]);
  const date = picked ?? today;
  const { data, loading } = useFetch<HistoryResponse>(
    `/api/history?site=${site}&range=${range}${picked ? `&date=${picked}` : ""}`,
    !picked && (range === "day" || range === "week") ? 60_000 : undefined,
  );
  const setDate = (d: string) => setPicked(d >= today ? null : d);

  const step = range === "day" ? 1 : range === "week" ? 7 : range === "month" ? 31 : 366;
  const move = (dir: number) => {
    let next = shiftDate(date, dir * step);
    if (range === "month") {
      const d = new Date(`${date}T12:00:00`);
      d.setMonth(d.getMonth() + dir, 1);
      next = isoDate(d);
    }
    if (range === "year") next = `${Number(date.slice(0, 4)) + dir}-06-15`;
    if (next > today) next = today;
    setDate(next);
  };

  const option = useCallback(
    (dark: boolean) => {
      if (!data) return {};
      if ((range === "day" || range === "week") && data.series && data.series.ts.length)
        return powerOption(data, lang, t, timeZone, dark);
      if (data.energy) return energyOption(data, lang, t, dark);
      return {};
    },
    [data, range, lang, t, timeZone],
  );

  const label = useMemo(() => {
    if (range === "day") return date === today ? t("common.today") : fmtDate(date, lang, { weekday: "short", day: "2-digit", month: "short" });
    if (range === "week") return `${fmtDate(shiftDate(date, -6), lang)} – ${fmtDate(date, lang)}`;
    if (range === "month") return fmtDate(date, lang, { month: "long", year: "numeric" });
    return date.slice(0, 4);
  }, [range, date, today, lang, t]);

  const empty =
    data &&
    !((data.series && data.series.ts.length) || (data.energy && data.energy.pv_kwh.some((v) => v > 0)));

  return (
    <Card>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <Segmented
          label={t("chart.day")}
          value={range}
          onChange={(r) => setRange(r)}
          options={(["day", "week", "month", "year"] as const).map((r) => ({ value: r, label: t(`chart.${r}`) }))}
        />
        <div className="flex items-center gap-1">
          <Button size="icon" variant="ghost" aria-label={t("chart.prev")} onClick={() => move(-1)}>
            <ChevronLeft size={18} />
          </Button>
          <span className="num min-w-28 text-center text-sm font-medium">{label}</span>
          <Button size="icon" variant="ghost" aria-label={t("chart.next")} onClick={() => move(1)} disabled={date >= today}>
            <ChevronRight size={18} />
          </Button>
        </div>
      </div>
      {loading && !data ? (
        <Skeleton className="h-[300px]" />
      ) : empty ? (
        <div className="flex h-[300px] items-center justify-center text-sm text-muted">{t("chart.no_data")}</div>
      ) : (
        <EChart option={option} height={300} ariaLabel={`${t("dash.today")} – ${label}`} />
      )}
    </Card>
  );
}
