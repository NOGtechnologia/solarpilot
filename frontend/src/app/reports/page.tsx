"use client";

import { CaretLeft, CaretRight, Coins, DownloadSimple, HouseLine, Leaf, SolarPanel, Trophy } from "@phosphor-icons/react";
import { useCallback, useState } from "react";

import { EChart, chartTheme } from "@/components/charts/echart";
import { KpiTile } from "@/components/dashboard/kpi-tile";
import { SiteSwitcher } from "@/components/dashboard/site-switcher";
import { useApp } from "@/components/providers";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/form";
import { fmtCurrency, fmtDate, fmtEnergy, fmtNumber, fmtPct } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { MonthlyReport } from "@/lib/types";
import { useFetch } from "@/lib/use-fetch";
import { COLORS, cn } from "@/lib/utils";

function monthStr(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export default function ReportsPage() {
  const { t, lang } = useI18n();
  const { site, sites } = useApp();
  const [month, setMonth] = useState(() => monthStr(new Date()));
  const current = monthStr(new Date());
  const { data, loading } = useFetch<MonthlyReport>(sites?.length ? `/api/reports/monthly?site=${site}&month=${month}` : null);

  const move = (dir: number) => {
    const [y, m] = month.split("-").map(Number);
    const d = new Date(y, m - 1 + dir, 1);
    const next = monthStr(d);
    if (next <= current) setMonth(next);
  };

  const option = useCallback(
    (dark: boolean) => {
      if (!data) return {};
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
          axisPointer: { type: "shadow" },
        },
        xAxis: { type: "category", data: data.days.labels.map((d) => d.slice(8)), axisLabel: { color: c.text, fontSize: 10 }, axisLine: { lineStyle: { color: c.grid } }, axisTick: { show: false } },
        yAxis: { type: "value", name: "kWh", nameTextStyle: { color: c.text, fontSize: 10 }, axisLabel: { color: c.text, fontSize: 11 }, splitLine: { lineStyle: { color: c.grid } } },
        series: [
          { name: t("chart.self"), type: "bar", stack: "pv", data: data.days.self_kwh, itemStyle: { color: COLORS.load }, barMaxWidth: 16 },
          { name: t("chart.grid_export"), type: "bar", stack: "pv", data: data.days.export_kwh, itemStyle: { color: COLORS.gridExport, borderRadius: [3, 3, 0, 0] }, barMaxWidth: 16 },
          { name: t("chart.grid_import"), type: "line", data: data.days.import_kwh, showSymbol: false, lineStyle: { color: COLORS.gridImport, width: 1.5 }, itemStyle: { color: COLORS.gridImport } },
        ],
      };
    },
    [data, lang, t],
  );

  const tot = data?.total;
  const e = (wh: number | undefined) => (wh === undefined ? { value: "–", unit: "" } : fmtEnergy(wh, lang));
  const [y, m] = month.split("-").map(Number);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("reports.title")}</h1>
          <div className="mt-1 flex items-center gap-1">
            <Button size="icon" variant="ghost" aria-label={t("chart.prev")} onClick={() => move(-1)}>
              <CaretLeft size={18} />
            </Button>
            <span className="min-w-36 text-center text-sm font-medium">{fmtDate(`${month}-15`, lang, { month: "long", year: "numeric" })}</span>
            <Button size="icon" variant="ghost" aria-label={t("chart.next")} onClick={() => move(1)} disabled={month >= current}>
              <CaretRight size={18} />
            </Button>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <SiteSwitcher />
          <a
            href={`/api/reports/monthly.pdf?site=${site}&month=${month}&lang=${lang}`}
            className={cn(buttonVariants({ variant: "primary", size: "md" }))}
            download
          >
            <DownloadSimple size={16} /> {t("reports.pdf")}
          </a>
        </div>
      </div>

      {loading && !data ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <KpiTile
              label={t("reports.yield")}
              icon={<SolarPanel />}
              accent={COLORS.solar}
              value={e(tot?.pv_wh).value}
              unit={e(tot?.pv_wh).unit}
              sub={data?.change_pct != null ? `${data.change_pct > 0 ? "+" : ""}${fmtNumber(data.change_pct, lang, 1)} % ${t("reports.vs_last_year")}` : t("reports.no_prev")}
            />
            <KpiTile icon={<Coins />} label={t("reports.savings")} accent={COLORS.solar} value={fmtCurrency(tot?.savings_eur, lang)} />
            <KpiTile icon={<HouseLine />} label={t("reports.self")} accent={COLORS.load} value={fmtPct(tot?.self_consumption_pct, lang)} sub={`${t("reports.autarky")} ${fmtPct(tot?.autarky_pct, lang)}`} />
            <KpiTile icon={<Leaf />} label={t("reports.co2")} accent={COLORS.gridExport} value={tot ? fmtNumber(tot.co2_kg, lang) : "–"} unit="kg" />
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader title={t("reports.daily")} />
              <EChart option={option} height={300} ariaLabel={t("reports.daily")} />
            </Card>
            <Card>
              <CardHeader title={`${fmtDate(`${y}-${String(m).padStart(2, "0")}-15`, lang, { month: "long" })} · ${data?.sites.join(", ") ?? ""}`} />
              <dl className="space-y-2.5 text-sm">
                {[
                  [t("reports.load"), e(tot?.load_wh)],
                  [t("reports.import"), e(tot?.import_wh)],
                  [t("reports.export"), e(tot?.export_wh)],
                ].map(([k, v]) => (
                  <div key={k as string} className="flex justify-between border-b border-border pb-2">
                    <dt className="text-muted">{k as string}</dt>
                    <dd className="num font-medium">
                      {(v as { value: string }).value} {(v as { unit: string }).unit}
                    </dd>
                  </div>
                ))}
                {data?.best_day && (
                  <div className="flex items-center justify-between pt-1">
                    <dt className="flex items-center gap-1.5 text-muted">
                      <Trophy size={14} className="text-solar" /> {t("reports.best_day")}
                    </dt>
                    <dd className="num font-medium">
                      {fmtDate(data.best_day.day, lang)} · {fmtNumber(data.best_day.pv_kwh, lang, 1)} kWh
                    </dd>
                  </div>
                )}
              </dl>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
