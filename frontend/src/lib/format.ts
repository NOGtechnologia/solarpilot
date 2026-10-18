export type Lang = "de" | "en";

const locale = (lang: Lang) => (lang === "de" ? "de-DE" : "en-GB");

export function fmtNumber(value: number, lang: Lang, digits = 0): string {
  return new Intl.NumberFormat(locale(lang), {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

/** Leistung: < 1000 W in W, sonst kW mit 1–2 Nachkommastellen. */
export function fmtPower(w: number | null | undefined, lang: Lang): { value: string; unit: string } {
  if (w === null || w === undefined || Number.isNaN(w)) return { value: "–", unit: "" };
  const abs = Math.abs(w);
  if (abs < 1000) return { value: fmtNumber(Math.round(w), lang), unit: "W" };
  const digits = abs >= 10000 ? 1 : 2;
  return { value: fmtNumber(w / 1000, lang, digits), unit: "kW" };
}

export function fmtEnergy(wh: number | null | undefined, lang: Lang): { value: string; unit: string } {
  if (wh === null || wh === undefined || Number.isNaN(wh)) return { value: "–", unit: "" };
  const abs = Math.abs(wh);
  if (abs < 1000) return { value: fmtNumber(Math.round(wh), lang), unit: "Wh" };
  if (abs >= 1_000_000) return { value: fmtNumber(wh / 1_000_000, lang, 2), unit: "MWh" };
  return { value: fmtNumber(wh / 1000, lang, abs >= 100_000 ? 0 : 1), unit: "kWh" };
}

export function fmtCurrency(eur: number | null | undefined, lang: Lang, currency = "EUR"): string {
  if (eur === null || eur === undefined) return "–";
  return new Intl.NumberFormat(locale(lang), { style: "currency", currency }).format(eur);
}

export function fmtPct(v: number | null | undefined, lang: Lang): string {
  if (v === null || v === undefined) return "–";
  return `${fmtNumber(v, lang)} %`;
}

export function fmtTime(ts: number | null | undefined, lang: Lang, timeZone?: string): string {
  if (!ts) return "–";
  return new Intl.DateTimeFormat(locale(lang), { hour: "2-digit", minute: "2-digit", timeZone }).format(
    new Date(ts * 1000),
  );
}

export function fmtDate(
  ts: number | string,
  lang: Lang,
  opts: Intl.DateTimeFormatOptions = { day: "2-digit", month: "2-digit" },
  timeZone?: string,
): string {
  const d = typeof ts === "number" ? new Date(ts * 1000) : new Date(`${ts}T12:00:00`);
  return new Intl.DateTimeFormat(locale(lang), { ...opts, timeZone }).format(d);
}

export function fmtRelative(ts: number, lang: Lang, now = Date.now() / 1000): string {
  const diff = Math.round(ts - now);
  const rtf = new Intl.RelativeTimeFormat(locale(lang), { numeric: "auto" });
  const abs = Math.abs(diff);
  if (abs < 60) return rtf.format(diff, "second");
  if (abs < 3600) return rtf.format(Math.round(diff / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(diff / 3600), "hour");
  return rtf.format(Math.round(diff / 86400), "day");
}

export function isoDate(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

/** Heutiges Datum (YYYY-MM-DD) in einer bestimmten Zeitzone. */
export function localToday(timeZone?: string, now = new Date()): string {
  try {
    return new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).format(now);
  } catch {
    return isoDate(now);
  }
}

export function shiftDate(iso: string, days: number): string {
  const d = new Date(`${iso}T12:00:00`);
  d.setDate(d.getDate() + days);
  return isoDate(d);
}
