"use client";

import { AlertTriangle, CloudSun, Wind } from "lucide-react";

import { Card, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/form";
import { fmtDate, fmtEnergy, fmtNumber, fmtTime, localToday } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { ForecastSite, WeatherResponse } from "@/lib/types";
import { weatherInfo } from "@/lib/weather-codes";

import { SunArc } from "./sun-arc";

export function WeatherCard({
  data,
  forecast,
  timeZone,
}: {
  data: WeatherResponse | undefined;
  forecast?: ForecastSite;
  timeZone?: string;
}) {
  const { t, lang } = useI18n();
  if (!data) {
    return (
      <Card>
        <CardHeader title={t("weather.title")} icon={<CloudSun size={14} />} />
        <Skeleton className="h-40" />
      </Card>
    );
  }
  const w = data.weather;
  const cur = w?.current;
  const info = weatherInfo(cur?.weather_code, cur?.is_day !== 0);
  const fcByDay = new Map((forecast?.daily ?? []).map((d) => [d.day, d.energy_wh]));

  return (
    <Card>
      <CardHeader
        title={t("weather.title")}
        icon={<CloudSun size={14} />}
        action={
          data.stale && data.fetched_at ? (
            <span className="text-[11px] text-muted">{t("common.stale", { time: fmtTime(data.fetched_at, lang) })}</span>
          ) : null
        }
      />
      {data.alerts.length > 0 && (
        <div className="mb-3 flex items-start gap-2 rounded-xl border border-grid-import/40 bg-grid-import/10 p-2.5 text-[13px]">
          <AlertTriangle size={16} className="mt-0.5 shrink-0 text-grid-import" />
          <span>
            <strong className="font-medium">{t("weather.alerts")}:</strong>{" "}
            {lang === "de" ? data.alerts[0].headline_de : data.alerts[0].headline_en || data.alerts[0].headline_de}
          </span>
        </div>
      )}
      {!w ? (
        <p className="text-sm text-muted">{t("weather.unavailable")}</p>
      ) : (
        <>
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <info.icon size={40} className="text-solar" aria-hidden />
              <div>
                <div className="num text-[34px] font-semibold leading-none">{fmtNumber(cur!.temperature, lang)}°</div>
                <div className="mt-1 text-sm text-muted">{t(info.key)}</div>
              </div>
            </div>
            <div className="text-right text-xs text-muted">
              <div>
                {t("weather.clouds")} <span className="num font-medium text-fg">{cur!.cloud_cover} %</span>
              </div>
              <div className="mt-1 flex items-center justify-end gap-1">
                <Wind size={12} /> <span className="num font-medium text-fg">{fmtNumber(cur!.wind_speed, lang)} km/h</span>
              </div>
            </div>
          </div>
          <div className="mt-4">
            <SunArc sunrise={data.sun.sunrise} sunset={data.sun.sunset} timeZone={timeZone} />
          </div>
          <ul className="mt-4 grid grid-cols-7 gap-1 text-center">
            {w.daily.slice(0, 7).map((d) => {
              const di = weatherInfo(d.weather_code);
              const dayIso = localToday(timeZone, new Date((d.ts + 43200) * 1000));
              const e = fcByDay.get(dayIso);
              const ef = e !== undefined ? fmtEnergy(e, lang) : null;
              return (
                <li key={d.ts} className="flex flex-col items-center gap-1 rounded-xl py-1.5">
                  <span className="text-[11px] text-muted">{fmtDate(d.ts, lang, { weekday: "short" }, timeZone)}</span>
                  <di.icon size={18} className="text-solar" aria-label={t(di.key)} />
                  <span className="num text-xs font-medium">{Math.round(d.temp_max)}°</span>
                  <span className="num text-[11px] text-muted">{Math.round(d.temp_min)}°</span>
                  {ef && (
                    <span className="num text-[10px] font-medium text-solar-text" title={t("weather.forecast_kwh")}>
                      {ef.unit === "kWh" ? ef.value : fmtNumber(e! / 1000, lang, 1)}
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
          {forecast?.daily?.length ? (
            <p className="mt-1 text-right text-[10px] text-muted">{t("weather.forecast_kwh")} kWh</p>
          ) : null}
        </>
      )}
    </Card>
  );
}
