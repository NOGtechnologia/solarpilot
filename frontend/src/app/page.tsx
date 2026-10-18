"use client";

import { BatteryCharging, Coins, Gauge, Home as HomeIcon, Leaf, Sun } from "lucide-react";
import { useMemo } from "react";

import { CountUp } from "@/components/dashboard/count-up";
import { DeviceList } from "@/components/dashboard/device-list";
import { EmptyState } from "@/components/dashboard/empty-state";
import { EnergyFlow } from "@/components/dashboard/energy-flow";
import { Hero } from "@/components/dashboard/hero";
import { HistoryChart } from "@/components/dashboard/history-chart";
import { InsightsCard } from "@/components/dashboard/insights-card";
import { KpiTile } from "@/components/dashboard/kpi-tile";
import { NewsCard } from "@/components/dashboard/news-card";
import { PriceChart } from "@/components/dashboard/price-chart";
import { SiteSwitcher } from "@/components/dashboard/site-switcher";
import { WeatherCard } from "@/components/dashboard/weather-card";
import { useApp } from "@/components/providers";
import { Skeleton } from "@/components/ui/form";
import { fmtCurrency, fmtEnergy, fmtNumber, fmtPct, fmtPower } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { DayStats, ForecastSite, Insight, NewsItem, PricesResponse, WeatherResponse } from "@/lib/types";
import { useFetch } from "@/lib/use-fetch";
import { useLive } from "@/lib/use-live";
import { COLORS } from "@/lib/utils";

export default function Dashboard() {
  const { t, lang } = useI18n();
  const { sites, site, auth } = useApp();
  const ready = !!auth && (auth.authenticated || auth.public_dashboard);
  const hasSites = !!sites && sites.length > 0;
  const { payload, state } = useLive(ready && hasSites);

  const current = site === "all" ? null : sites?.find((s) => String(s.id) === site);
  const primary = current ?? sites?.[0];
  const tz = primary?.timezone;

  const kpis = useFetch<{ today: DayStats | null }>(hasSites ? `/api/kpis?site=${site}` : null, 60_000);
  const weather = useFetch<WeatherResponse>(hasSites && primary ? `/api/weather?site=${primary.id}` : null, 15 * 60_000);
  const forecast = useFetch<{ sites: ForecastSite[] }>(hasSites ? `/api/forecast?site=${site}` : null, 30 * 60_000);
  const prices = useFetch<PricesResponse>(hasSites ? "/api/prices" : null, 15 * 60_000);
  const news = useFetch<{ items: NewsItem[]; enabled: boolean }>(hasSites ? `/api/news?limit=8&lang=${lang}` : null, 30 * 60_000);
  const insights = useFetch<{ items: Insight[]; summary: { text: string; created_at: number } | null }>(
    hasSites ? `/api/insights?site=${site}` : null,
    5 * 60_000,
  );

  const snap = site === "all" ? payload?.all : payload?.sites?.[site];
  const devices = useMemo(
    () => (payload?.devices ?? []).filter((d) => site === "all" || String(d.site_id) === site),
    [payload, site],
  );
  const today = kpis.data?.today;
  const fcToday = useMemo(() => {
    const list = forecast.data?.sites ?? [];
    return list.reduce((sum, s) => sum + (s.daily[0]?.energy_wh ?? 0), 0) || today?.forecast_wh || null;
  }, [forecast.data, today]);

  if (!sites || !auth) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-[420px]" />
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      </div>
    );
  }
  if (!hasSites) return <EmptyState />;

  const pv = fmtPower(snap?.pv_power_w ?? null, lang);
  const yieldToday = fmtEnergy(today?.pv_wh ?? snap?.energy_today_wh ?? null, lang);
  const kwp = (current ? current.kwp : sites.reduce((s, x) => s + x.kwp, 0)) || null;
  const pctOfPeak = kwp && snap?.pv_power_w ? Math.round((snap.pv_power_w / (kwp * 1000)) * 100) : null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <SiteSwitcher />
        <span className="flex items-center gap-1.5 text-[12px] text-muted" aria-live="polite">
          <span className={`h-2 w-2 rounded-full ${state === "live" ? "bg-success" : "bg-solar"} ${state === "live" ? "animate-pulse" : ""}`} />
          {state === "live" ? t("dash.live") : t("dash.connecting")}
        </span>
      </div>

      {/* Was passiert gerade? */}
      <Hero elevation={weather.data?.sun.elevation} cloud={weather.data?.weather?.current.cloud_cover}>
        <h2 className="sr-only">{t("dash.now")}</h2>
        <div className="grid items-center gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
          <div>
            <p className="text-[13px] font-medium text-muted">{t("dash.pv_now")}</p>
            <p className="mt-1 flex items-baseline gap-2">
              <span className="num text-[48px] font-semibold leading-none tracking-tight sm:text-[56px]" style={{ color: COLORS.solar }}>
                {snap ? pv.value : "–"}
              </span>
              <span className="text-xl text-muted">{pv.unit}</span>
            </p>
            {pctOfPeak !== null && (
              <p className="mt-2 text-sm text-muted">
                <span className="num font-medium text-fg">{pctOfPeak} %</span> · {fmtNumber(kwp!, lang, 1)} kWp
              </p>
            )}
            <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-[12px] text-muted">{t("kpi.yield_today")}</div>
                <div className="num text-lg font-semibold">
                  {yieldToday.value} <span className="text-sm font-normal text-muted">{yieldToday.unit}</span>
                </div>
              </div>
              <div>
                <div className="text-[12px] text-muted">{t("kpi.forecast_today")}</div>
                <div className="num text-lg font-semibold">
                  {fcToday ? fmtEnergy(fcToday, lang).value : "–"}{" "}
                  <span className="text-sm font-normal text-muted">{fcToday ? fmtEnergy(fcToday, lang).unit : ""}</span>
                </div>
              </div>
            </div>
          </div>
          <EnergyFlow snapshot={snap} />
        </div>
      </Hero>

      {/* Wie war heute? */}
      <section aria-labelledby="today-h" className="space-y-4">
        <h2 id="today-h" className="sr-only">
          {t("dash.today")}
        </h2>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <KpiTile
            label={t("kpi.self_consumption")}
            icon={<HomeIcon size={14} />}
            accent={COLORS.load}
            value={today?.self_consumption_pct != null ? <CountUp id={`sc-${site}`} value={today.self_consumption_pct} format={(v) => fmtNumber(v, lang)} /> : "–"}
            unit="%"
            sub={today ? `${fmtEnergy(today.self_consumption_wh, lang).value} ${fmtEnergy(today.self_consumption_wh, lang).unit}` : undefined}
          />
          <KpiTile
            label={t("kpi.autarky")}
            icon={<Gauge size={14} />}
            accent={COLORS.battery}
            value={today?.autarky_pct != null ? <CountUp id={`au-${site}`} value={today.autarky_pct} format={(v) => fmtNumber(v, lang)} /> : "–"}
            unit="%"
            sub={today ? `${t("kpi.import_today")} ${fmtEnergy(today.import_wh, lang).value} ${fmtEnergy(today.import_wh, lang).unit}` : undefined}
          />
          <KpiTile
            label={t("kpi.savings")}
            icon={<Coins size={14} />}
            accent={COLORS.solar}
            value={today ? <CountUp id={`sv-${site}`} value={today.savings_eur} format={(v) => fmtCurrency(v, lang)} /> : "–"}
            sub={today ? `${t("kpi.export_today")} ${fmtEnergy(today.export_wh, lang).value} ${fmtEnergy(today.export_wh, lang).unit}` : undefined}
          />
          <KpiTile
            label={t("kpi.co2")}
            icon={<Leaf size={14} />}
            accent={COLORS.gridExport}
            value={today ? <CountUp id={`co-${site}`} value={today.co2_kg} format={(v) => fmtNumber(v, lang, 1)} /> : "–"}
            unit="kg"
            sub={
              today?.forecast_wh ? (
                <span className="inline-flex items-center gap-1">
                  <Sun size={11} /> {t("kpi.of_forecast", { pct: fmtPct((today.pv_wh / today.forecast_wh) * 100, lang) })}
                </span>
              ) : undefined
            }
          />
        </div>
        <HistoryChart site={site} timeZone={tz} />
      </section>

      {/* Was kommt? */}
      <section aria-labelledby="next-h" className="grid gap-4 lg:grid-cols-3">
        <h2 id="next-h" className="sr-only">
          {t("dash.next")}
        </h2>
        <div className="space-y-4 lg:col-span-1">
          <InsightsCard data={insights.data} timeZone={tz} />
          <DeviceList devices={devices} />
        </div>
        <div className="space-y-4">
          <WeatherCard data={weather.data} forecast={forecast.data?.sites.find((s) => s.site_id === primary?.id)} timeZone={tz} />
        </div>
        <div className="space-y-4">
          <PriceChart data={prices.data} />
          <NewsCard data={news.data} />
        </div>
      </section>
      <p className="flex items-center justify-center gap-1.5 pt-2 text-center text-[11px] text-muted">
        <BatteryCharging size={12} /> {t("dash.sources")}
      </p>
    </div>
  );
}
