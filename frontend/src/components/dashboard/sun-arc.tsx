"use client";

import { fmtTime } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { COLORS } from "@/lib/utils";

/** Halbkreis vom Sonnenaufgang bis -untergang mit aktuellem Sonnenstand. */
export function SunArc({
  sunrise,
  sunset,
  timeZone,
  now = Date.now() / 1000,
}: {
  sunrise: number | null;
  sunset: number | null;
  timeZone?: string;
  now?: number;
}) {
  const { t, lang } = useI18n();
  const w = 220;
  const h = 120;
  const cx = w / 2;
  const cy = 104;
  const r = 88;
  const frac = sunrise && sunset ? (now - sunrise) / (sunset - sunrise) : -1;
  const up = frac >= 0 && frac <= 1;
  const angle = Math.PI * (1 - Math.min(Math.max(frac, 0), 1));
  const sx = cx + r * Math.cos(angle);
  const sy = cy - r * Math.sin(angle);
  const arc = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;
  const progressArc = up ? `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${sx} ${sy}` : "";

  return (
    <figure className="flex flex-col items-center">
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full max-w-[260px]" role="img" aria-label={`${t("sun.sunrise")} ${fmtTime(sunrise, lang, timeZone)}, ${t("sun.sunset")} ${fmtTime(sunset, lang, timeZone)}`}>
        <path d={arc} fill="none" stroke="var(--border)" strokeWidth={2} strokeDasharray="3 5" />
        {up && <path d={progressArc} fill="none" stroke={COLORS.solar} strokeWidth={2.5} strokeLinecap="round" />}
        <line x1={cx - r - 10} y1={cy} x2={cx + r + 10} y2={cy} stroke="var(--border)" strokeWidth={1.5} />
        {up ? (
          <>
            <circle cx={sx} cy={sy} r={14} fill={COLORS.solar} opacity={0.18} />
            <circle cx={sx} cy={sy} r={8} fill={COLORS.solar} />
          </>
        ) : (
          <text x={cx} y={cy - 30} textAnchor="middle" fontSize={11} fill="var(--muted)">
            {t("sun.below")}
          </text>
        )}
      </svg>
      <figcaption className="mt-1 flex w-full max-w-[260px] justify-between text-xs text-muted">
        <span>
          {t("sun.sunrise")} <span className="num font-medium text-fg">{fmtTime(sunrise, lang, timeZone)}</span>
        </span>
        <span>
          {t("sun.sunset")} <span className="num font-medium text-fg">{fmtTime(sunset, lang, timeZone)}</span>
        </span>
      </figcaption>
    </figure>
  );
}
