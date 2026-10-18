"""PV-Ertragsprognose pro Site aus Open-Meteo ``global_tilted_irradiance``.

Pro Modulfeld: ``P = kWp · GTI/1000 · (1 − Verluste) · Temperaturfaktor``. Open-Meteo-Strahlung ist
der Mittelwert der *vorangegangenen* Stunde, daher wird der Wert dem Stundenbeginn ``t − 1 h``
zugeordnet. Optional liefert Forecast.Solar eine zweite Meinung (Tagessummen).
Ein Korrekturfaktor pro Anlage wird aus den letzten 30 Tagen gelernt.
"""

from __future__ import annotations

import statistics
import time
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlmodel import Session, col, delete, select

from app.models import DailyStats, ForecastPoint, Site

from .cache import cached
from .http import client
from .settings_store import get_section
from .timeutil import local_day_of, local_today, tz

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
FORECAST_SOLAR = "https://api.forecast.solar"
FORECAST_TTL = 30 * 60
TEMP_COEFF = -0.0037  # pro °C, kristalline Module


def om_azimuth(compass_deg: float) -> float:
    """Kompass (180 = Süd) → Open-Meteo/Forecast.Solar (0 = Süd, −90 = Ost, 90 = West)."""
    a = (compass_deg - 180) % 360
    return a - 360 if a > 180 else a


async def fetch_gti(lat: float, lon: float, tilt: float, azimuth: float) -> dict[str, Any]:
    params = {
        "latitude": round(lat, 3),
        "longitude": round(lon, 3),
        "hourly": "global_tilted_irradiance,temperature_2m,cloud_cover",
        "tilt": tilt,
        "azimuth": om_azimuth(azimuth),
        "timezone": "UTC",
        "timeformat": "unixtime",
        "past_days": 1,
        "forecast_days": 7,
    }
    async with client() as c:
        r = await c.get(OPEN_METEO, params=params)
        r.raise_for_status()
        return r.json()


def array_power(
    raw: dict[str, Any], kwp: float, losses_pct: float = 14.0
) -> dict[int, tuple[float, float | None]]:
    h = raw.get("hourly", {})
    out: dict[int, tuple[float, float | None]] = {}
    times = h.get("time", [])
    gtis = h.get("global_tilted_irradiance", [])
    temps = h.get("temperature_2m", [])
    clouds = h.get("cloud_cover", [])
    for i, t in enumerate(times):
        gti = gtis[i] if i < len(gtis) and gtis[i] is not None else 0.0
        temp = temps[i] if i < len(temps) and temps[i] is not None else 15.0
        cloud = clouds[i] if i < len(clouds) else None
        tcell = temp + gti * 0.03
        factor = 1 + TEMP_COEFF * (tcell - 25)
        p = max(kwp * gti * (1 - losses_pct / 100) * factor, 0.0)
        out[int(t) - 3600] = (p, cloud)
    return out


async def fetch_forecast_solar(
    lat: float, lon: float, tilt: float, azimuth: float, kwp: float, key: str = ""
) -> dict[str, float]:
    prefix = f"/{key}" if key else ""
    url = (
        f"{FORECAST_SOLAR}{prefix}/estimate/{lat:.4f}/{lon:.4f}/{int(tilt)}/"
        f"{int(om_azimuth(azimuth))}/{kwp}"
    )
    async with client() as c:
        r = await c.get(url)
        r.raise_for_status()
        data = r.json()
    return {k: float(v) for k, v in (data.get("result", {}).get("watt_hours_day") or {}).items()}


def correction_factor(session: Session, site: Site, days: int = 30) -> dict[str, Any]:
    today = local_today(site.timezone)
    rows = session.exec(
        select(DailyStats).where(
            DailyStats.site_id == site.id,
            DailyStats.day >= (today - timedelta(days=days)).isoformat(),
            DailyStats.day < today.isoformat(),
        )
    ).all()
    pairs = [
        (r.pv_wh, r.forecast_wh)
        for r in rows
        if r.forecast_wh and r.forecast_wh > 500 and r.pv_wh > 0
    ]
    if len(pairs) < 5:
        return {"factor": 1.0, "accuracy_pct": None, "days": len(pairs)}
    factor = min(max(statistics.median(pv / fc for pv, fc in pairs), 0.6), 1.4)
    errors = [abs(pv - fc * factor) / (fc * factor) for pv, fc in pairs]
    accuracy = max(0.0, 100 - statistics.mean(errors) * 100)
    return {"factor": round(factor, 3), "accuracy_pct": round(accuracy, 1), "days": len(pairs)}


def store_points(
    session: Session, site_id: int, points: dict[int, tuple[float, float | None]]
) -> None:
    """Zukünftige Stunden überschreiben, vergangene nur auffüllen (Prognose bleibt vergleichbar)."""
    now_hour = int(time.time()) // 3600 * 3600
    future = {t: v for t, v in points.items() if t >= now_hour}
    past = {t: v for t, v in points.items() if t < now_hour and t >= now_hour - 86400}
    if future:
        session.exec(  # type: ignore[call-overload]
            delete(ForecastPoint).where(
                ForecastPoint.site_id == site_id, col(ForecastPoint.ts).in_(list(future))
            )
        )
    existing = set()
    if past:
        existing = set(
            session.exec(
                select(ForecastPoint.ts).where(
                    ForecastPoint.site_id == site_id, col(ForecastPoint.ts).in_(list(past))
                )
            ).all()
        )
    for t, (p, cloud) in {**past, **future}.items():
        if t in existing:
            continue
        session.add(
            ForecastPoint(site_id=site_id, ts=t, power_w=round(p, 1), cloud_cover_pct=cloud)
        )
    session.commit()


async def site_forecast(session: Session, site: Site) -> dict[str, Any]:
    arrays = [a for a in (site.arrays or []) if float(a.get("kwp") or 0) > 0]
    if not arrays:
        return {"points": [], "daily": [], "error": "no_arrays", "stale": False}
    total: dict[int, float] = defaultdict(float)
    clouds: dict[int, float | None] = {}
    stale, error, fetched = False, None, None
    for a in arrays:
        tilt, az = float(a.get("tilt", 30)), float(a.get("azimuth", 180))
        key = f"gti:{site.lat:.3f}:{site.lon:.3f}:{tilt:.0f}:{az:.0f}"
        res = await cached(
            key, FORECAST_TTL, lambda t=tilt, z=az: fetch_gti(site.lat, site.lon, t, z)
        )
        stale = stale or res["stale"]
        error = error or res["error"]
        fetched = res["fetched_at"]
        if not res["data"]:
            continue
        for t, (p, cloud) in array_power(
            res["data"], float(a["kwp"]), float(a.get("losses_pct", 14))
        ).items():
            total[t] += p
            clouds.setdefault(t, cloud)
    if total and site.id is not None and not stale:
        store_points(session, site.id, {t: (p, clouds.get(t)) for t, p in total.items()})
    corr = correction_factor(session, site)
    f = corr["factor"]
    daily: dict[str, float] = defaultdict(float)
    hours: dict[str, int] = defaultdict(int)
    for t, p in total.items():
        d = local_day_of(t, site.timezone).isoformat()
        daily[d] += p * f
        hours[d] += 1
    # Tage am Rand des Prognosezeitraums sind unvollständig – weglassen
    daily = defaultdict(float, {d: wh for d, wh in daily.items() if hours[d] >= 22})
    today = local_today(site.timezone).isoformat()
    second: dict[str, float] = {}
    wcfg = get_section(session, "weather")
    if wcfg.get("forecast_solar"):
        for a in arrays:
            tilt, az, kwp = float(a.get("tilt", 30)), float(a.get("azimuth", 180)), float(a["kwp"])
            key = f"fsolar:{site.lat:.3f}:{site.lon:.3f}:{tilt:.0f}:{az:.0f}:{kwp}"
            res = await cached(
                key,
                60 * 60,
                lambda t=tilt, z=az, k=kwp: fetch_forecast_solar(
                    site.lat, site.lon, t, z, k, wcfg.get("forecast_solar_key", "")
                ),
            )
            for d, wh in (res["data"] or {}).items():
                second[d] = second.get(d, 0) + wh
    return {
        "points": [
            {
                "ts": t,
                "power_w": round(p * f, 1),
                "raw_w": round(p, 1),
                "cloud_cover": clouds.get(t),
            }
            for t, p in sorted(total.items())
        ],
        "daily": [
            {"day": d, "energy_wh": round(wh, 0), "forecast_solar_wh": second.get(d)}
            for d, wh in sorted(daily.items())
            if d >= today
        ],
        "correction": corr,
        "fetched_at": fetched,
        "stale": stale,
        "error": error,
        "timezone": str(tz(site.timezone)),
    }


def accuracy_history(session: Session, site: Site, days: int = 30) -> list[dict[str, Any]]:
    today = local_today(site.timezone)
    rows = session.exec(
        select(DailyStats)
        .where(
            DailyStats.site_id == site.id,
            DailyStats.day >= (today - timedelta(days=days)).isoformat(),
        )
        .order_by(DailyStats.day)
    ).all()
    return [{"day": r.day, "actual_wh": round(r.pv_wh), "forecast_wh": r.forecast_wh} for r in rows]


def forecast_for_day(session: Session, site: Site, day: date) -> list[tuple[int, float]]:
    from .timeutil import day_bounds

    start, end = day_bounds(day, site.timezone)
    rows = session.exec(
        select(ForecastPoint.ts, ForecastPoint.power_w)
        .where(ForecastPoint.site_id == site.id, ForecastPoint.ts >= start, ForecastPoint.ts < end)
        .order_by(ForecastPoint.ts)
    ).all()
    return [(int(t), float(p)) for t, p in rows]
