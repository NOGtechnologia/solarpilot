"""Insights: kombiniert Prognose, Batteriestand und Strompreise zu konkreten Empfehlungen.

Die Regeln sind reine Funktionen (gut testbar); ``build_insights`` sammelt die Eingaben.
Texte werden im Frontend über i18n-Schlüssel (``key`` + ``params``) erzeugt.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import DailyStats, ForecastPoint, Measurement, Site

from .settings_store import get_section
from .timeutil import local_today, tz


@dataclass
class Insight:
    id: str
    kind: str  # tip | warning | info
    key: str
    params: dict[str, Any] = field(default_factory=dict)
    site_id: int | None = None
    start: int | None = None
    end: int | None = None
    priority: int = 50

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --- Reine Regeln ----------------------------------------------------------------


def surplus_window(
    forecast: list[tuple[int, float]],
    base_load: dict[int, float],
    tzname: str,
    min_surplus_w: float,
    after: int,
    until: int,
) -> dict[str, Any] | None:
    """Längstes zusammenhängendes Stundenfenster mit PV-Überschuss ≥ ``min_surplus_w``."""
    z = tz(tzname)
    best: dict[str, Any] | None = None
    cur: list[tuple[int, float]] = []

    def close() -> None:
        nonlocal best, cur
        if cur:
            energy = sum(s for _, s in cur)
            if best is None or energy > best["energy_wh"]:
                best = {
                    "start": cur[0][0],
                    "end": cur[-1][0] + 3600,
                    "energy_wh": round(energy),
                    "avg_surplus_w": round(energy / len(cur)),
                }
        cur = []

    for ts, pv in sorted(forecast):
        if ts + 3600 <= after or ts >= until:
            continue
        hour = datetime.fromtimestamp(ts, UTC).astimezone(z).hour
        surplus = pv - base_load.get(hour, 400.0)
        if surplus >= min_surplus_w and (not cur or cur[-1][0] + 3600 == ts):
            cur.append((ts, surplus))
        elif surplus >= min_surplus_w:
            close()
            cur.append((ts, surplus))
        else:
            close()
    close()
    return best


def battery_full_at(
    forecast: list[tuple[int, float]],
    base_load: dict[int, float],
    tzname: str,
    soc_pct: float,
    capacity_wh: float,
    after: int,
) -> int | None:
    if capacity_wh <= 0:
        return None
    z = tz(tzname)
    soc_wh = capacity_wh * soc_pct / 100
    seen_sun = False
    for ts, pv in sorted(forecast):
        if ts + 3600 <= after:
            continue
        hour = datetime.fromtimestamp(ts, UTC).astimezone(z).hour
        surplus = pv - base_load.get(hour, 400.0)
        if pv > 0:
            seen_sun = True
        if surplus <= 0:
            if pv <= 0 and seen_sun:
                return None  # Abend erreicht ohne volle Batterie
            continue
        frac = 1.0 if ts >= after else (ts + 3600 - after) / 3600
        need = capacity_wh - soc_wh
        gain = surplus * frac
        if gain >= need:
            return int(ts + (need / surplus) * 3600) if surplus > 0 else ts
        soc_wh += gain
    return None


def is_underperforming(
    days: list[dict[str, Any]], threshold: float = 0.7, consecutive: int = 3
) -> dict[str, Any] | None:
    """Ist < ``threshold`` · Prognose an ``consecutive`` aufeinanderfolgenden klaren Tagen."""
    recent = sorted(days, key=lambda d: d["day"])[-consecutive:]
    if len(recent) < consecutive:
        return None
    for d in recent:
        fc = d.get("forecast_wh")
        if not d.get("clear_sky") or not fc or fc < 1000:
            return None
        if d["pv_wh"] >= threshold * fc:
            return None
    ratio = sum(d["pv_wh"] for d in recent) / sum(d["forecast_wh"] for d in recent)
    return {"ratio_pct": round(ratio * 100), "days": consecutive}


def ev_charging_plan(
    hours: list[dict[str, Any]], energy_wh: float, power_w: float
) -> dict[str, Any] | None:
    """Wählt die günstigsten Stunden zum Laden.

    ``hours``: [{"ts", "surplus_w", "grid_ct"}]. Überschuss-Strom kostet nur die entgangene
    Einspeisevergütung (``feed_ct``), Netzstrom den (dynamischen) Preis.
    """
    if not hours or energy_wh <= 0 or power_w <= 0:
        return None
    scored = []
    for h in hours:
        pv_part = min(max(h.get("surplus_w", 0), 0), power_w)
        grid_part = power_w - pv_part
        cost = (pv_part * h.get("feed_ct", 8) + grid_part * h["grid_ct"]) / power_w
        scored.append((cost, h["ts"], pv_part))
    scored.sort()
    chosen, got = [], 0.0
    for cost, ts, pv_part in scored:
        chosen.append((ts, cost, pv_part))
        got += power_w
        if got >= energy_wh:
            break
    chosen.sort()
    avg = sum(c for _, c, _ in chosen) / len(chosen)
    solar_share = sum(p for _, _, p in chosen) / (power_w * len(chosen))
    return {
        "start": chosen[0][0],
        "end": chosen[-1][0] + 3600,
        "hours": [t for t, _, _ in chosen],
        "avg_ct_kwh": round(avg, 1),
        "solar_share_pct": round(solar_share * 100),
    }


# --- Eingaben sammeln ----------------------------------------------------------


def base_load_profile(
    session: Session, site: Site, default_w: float, days: int = 7
) -> dict[int, float]:
    since = int(time.time()) - days * 86400
    rows = session.exec(
        select(Measurement.ts, Measurement.load_w).where(
            Measurement.site_id == site.id,
            col(Measurement.device_id).is_(None),
            Measurement.ts >= since,
            col(Measurement.load_w).is_not(None),
        )
    ).all()
    if len(rows) < 60:
        return dict.fromkeys(range(24), default_w)
    z = tz(site.timezone)
    buckets: dict[int, list[float]] = defaultdict(list)
    for ts, load in rows:
        buckets[datetime.fromtimestamp(ts, UTC).astimezone(z).hour].append(load)
    # Median statt Mittelwert: einzelne Großverbraucher verzerren das Grundlast-Profil nicht
    out = {}
    for h in range(24):
        vals = sorted(buckets.get(h, []))
        out[h] = vals[len(vals) // 2] if vals else default_w
    return out


def site_forecast_points(
    session: Session, site: Site, start: int, end: int
) -> list[tuple[int, float]]:
    rows = session.exec(
        select(ForecastPoint.ts, ForecastPoint.power_w).where(
            ForecastPoint.site_id == site.id, ForecastPoint.ts >= start, ForecastPoint.ts < end
        )
    ).all()
    return [(int(t), float(p)) for t, p in rows]


def mark_clear_sky(session: Session, site: Site, day_iso: str) -> bool | None:
    from datetime import date

    from .timeutil import day_bounds

    start, end = day_bounds(date.fromisoformat(day_iso), site.timezone)
    avg = session.exec(
        select(func.avg(ForecastPoint.cloud_cover_pct)).where(
            ForecastPoint.site_id == site.id,
            ForecastPoint.ts >= start + 9 * 3600,
            ForecastPoint.ts < start + 16 * 3600,
        )
    ).one()
    return None if avg is None else bool(avg < 30)


def build_insights(
    session: Session,
    sites: list[Site],
    live: dict[str, Any] | None,
    prices: dict[str, Any] | None = None,
    now: int | None = None,
) -> list[dict[str, Any]]:
    now = now or int(time.time())
    general = get_section(session, "general")
    tariff = get_section(session, "tariff")
    out: list[Insight] = []
    live = live or {}
    price_pts = (prices or {}).get("points") or []

    for site in sites:
        if site.id is None:
            continue
        z = tz(site.timezone)
        local_now = datetime.fromtimestamp(now, UTC).astimezone(z)
        midnight = datetime(local_now.year, local_now.month, local_now.day, tzinfo=z)
        end_today = int((midnight + timedelta(days=1)).timestamp())
        end_tomorrow = int((midnight + timedelta(days=2)).timestamp())
        fc = site_forecast_points(session, site, int(midnight.timestamp()), end_tomorrow)
        base = base_load_profile(session, site, float(general["base_load_w"]))
        min_surplus = float(general["big_consumer_w"])

        # 1) Zeitfenster für große Verbraucher (heute, sonst morgen)
        win = surplus_window(fc, base, site.timezone, min_surplus, now, end_today)
        day_key = "today"
        if not win and local_now.hour >= 12:
            win = surplus_window(fc, base, site.timezone, min_surplus, end_today, end_tomorrow)
            day_key = "tomorrow"
        if win:
            out.append(
                Insight(
                    id=f"surplus:{site.id}:{datetime.fromtimestamp(win['start'], UTC).date()}",
                    kind="tip",
                    key="insight.surplus",
                    site_id=site.id,
                    start=win["start"],
                    end=win["end"],
                    priority=10,
                    params={
                        "day": day_key,
                        "kw": round(win["avg_surplus_w"] / 1000, 1),
                        "kwh": round(win["energy_wh"] / 1000, 1),
                        "site": site.name,
                    },
                )
            )

        # 2) Batterie voll um …
        snap = (live.get("sites") or {}).get(str(site.id))
        cap = (site.battery_kwh or 0) * 1000
        if snap and snap.get("battery_soc_pct") is not None and cap > 0:
            soc = float(snap["battery_soc_pct"])
            if soc < 98:
                full = battery_full_at(fc, base, site.timezone, soc, cap, now)
                if full and full < end_today:
                    out.append(
                        Insight(
                            id=f"battery_full:{site.id}:{local_now.date()}",
                            kind="info",
                            key="insight.battery_full",
                            site_id=site.id,
                            start=full,
                            priority=40,
                            params={"site": site.name},
                        )
                    )

        # 3) E-Auto laden: beste Stunden der nächsten 24 h
        hours = []
        fc_map = dict(fc)
        buy_ct = (site.buy_eur_kwh or float(tariff["buy_eur_kwh"])) * 100
        feed_ct = (site.feed_in_eur_kwh or float(tariff["feed_in_eur_kwh"])) * 100
        hourly_price: dict[int, float] = {}
        if tariff.get("dynamic") and price_pts:
            agg: dict[int, list[float]] = defaultdict(list)
            for p in price_pts:
                agg[p["ts"] // 3600 * 3600].append(
                    p["ct_kwh"] * 1.19 + float(tariff["markup_eur_kwh"]) * 100
                )
            hourly_price = {k: sum(v) / len(v) for k, v in agg.items()}
        start_h = now // 3600 * 3600
        for i in range(24):
            ts = start_h + i * 3600
            hour = datetime.fromtimestamp(ts, UTC).astimezone(z).hour
            hours.append(
                {
                    "ts": ts,
                    "surplus_w": fc_map.get(ts, 0) - base.get(hour, 400),
                    "grid_ct": hourly_price.get(ts, buy_ct),
                    "feed_ct": feed_ct,
                }
            )
        plan = ev_charging_plan(
            hours, float(general["ev_charge_kwh"]) * 1000, float(general["ev_charge_power_w"])
        )
        if plan and (plan["solar_share_pct"] >= 30 or hourly_price):
            out.append(
                Insight(
                    id=f"ev:{site.id}:{local_now.date()}",
                    kind="tip",
                    key="insight.ev",
                    site_id=site.id,
                    start=plan["start"],
                    end=plan["end"],
                    priority=30,
                    params={
                        "ct": plan["avg_ct_kwh"],
                        "solar": plan["solar_share_pct"],
                        "site": site.name,
                    },
                )
            )

        # 4) Minderertrag
        today = local_today(site.timezone)
        rows = session.exec(
            select(DailyStats).where(
                DailyStats.site_id == site.id,
                DailyStats.day < today.isoformat(),
                DailyStats.day >= (today - timedelta(days=7)).isoformat(),
            )
        ).all()
        under = is_underperforming(
            [
                {
                    "day": r.day,
                    "pv_wh": r.pv_wh,
                    "forecast_wh": r.forecast_wh,
                    "clear_sky": r.clear_sky,
                }
                for r in rows
            ]
        )
        if under:
            out.append(
                Insight(
                    id=f"under:{site.id}:{today}",
                    kind="warning",
                    key="insight.underperformance",
                    site_id=site.id,
                    priority=1,
                    params={**under, "site": site.name},
                )
            )

    # 5) Geräte offline
    for dev in live.get("devices") or []:
        if not dev.get("online"):
            since = dev.get("last_seen")
            if since is None or now - since > 15 * 60:
                out.append(
                    Insight(
                        id=f"offline:{dev['id']}:{since}",
                        kind="warning",
                        key="insight.offline",
                        site_id=dev.get("site_id"),
                        start=since,
                        priority=2,
                        params={"device": dev.get("name"), "error": dev.get("error")},
                    )
                )

    # 6) Strompreis: günstigstes Fenster
    if prices and prices.get("cheapest_3h"):
        w = prices["cheapest_3h"]
        out.append(
            Insight(
                id=f"cheap:{w['start']}",
                kind="info",
                key="insight.cheap_power",
                start=w["start"],
                end=w["end"],
                priority=35,
                params={"ct": w["avg_ct_kwh"]},
            )
        )
        cur = prices.get("current")
        if cur and price_pts:
            avg = sum(p["ct_kwh"] for p in price_pts) / len(price_pts)
            if cur["ct_kwh"] > avg * 1.4 and cur["ct_kwh"] > 15:
                out.append(
                    Insight(
                        id=f"expensive:{cur['ts']}",
                        kind="info",
                        key="insight.expensive_now",
                        start=cur["ts"],
                        end=cur["ts"] + cur["duration_s"],
                        priority=20,
                        params={"ct": round(cur["ct_kwh"], 1)},
                    )
                )

    out.sort(key=lambda i: i.priority)
    return [i.to_dict() for i in out]
