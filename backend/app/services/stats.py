"""Tagesstatistik (Energie, Eigenverbrauch, Autarkie, Ersparnis) und Verlaufsdaten."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import DailyStats, ForecastPoint, Measurement, Site, now_ts

from .settings_store import get_section
from .timeutil import day_bounds, local_today


def tariff_for(session: Session, site: Site) -> tuple[float, float]:
    t = get_section(session, "tariff")
    buy = site.buy_eur_kwh if site.buy_eur_kwh is not None else float(t["buy_eur_kwh"])
    feed = site.feed_in_eur_kwh if site.feed_in_eur_kwh is not None else float(t["feed_in_eur_kwh"])
    return buy, feed


def energy_from_rows(rows: list[tuple]) -> dict[str, float]:
    """Rows: (pv_w, load_w, grid_w, battery_w, dt_s) → Wh-Summen."""
    e = defaultdict(float)
    for pv, load, grid, batt, dt in rows:
        h = (dt or 60) / 3600
        e["pv_wh"] += max(pv or 0, 0) * h
        e["load_wh"] += max(load or 0, 0) * h
        e["import_wh"] += max(grid or 0, 0) * h
        e["export_wh"] += max(-(grid or 0), 0) * h
        e["charge_wh"] += max(batt or 0, 0) * h
        e["discharge_wh"] += max(-(batt or 0), 0) * h
    e["self_consumption_wh"] = max(e["pv_wh"] - e["export_wh"], 0)
    return dict(e)


def derived(e: dict[str, float], buy: float, feed: float, co2_factor: float) -> dict[str, Any]:
    pv, load, imp = e.get("pv_wh", 0), e.get("load_wh", 0), e.get("import_wh", 0)
    self_c = e.get("self_consumption_wh", 0)
    return {
        "self_consumption_pct": round(self_c / pv * 100, 1) if pv > 0 else None,
        "autarky_pct": round(max(load - imp, 0) / load * 100, 1) if load > 0 else None,
        "savings_eur": round(self_c / 1000 * buy + e.get("export_wh", 0) / 1000 * feed, 2),
        "co2_kg": round(pv / 1000 * co2_factor, 2),
    }


def compute_day(session: Session, site: Site, day: date, persist: bool = True) -> DailyStats:
    start, end = day_bounds(day, site.timezone)
    rows = session.exec(
        select(
            Measurement.pv_w,
            Measurement.load_w,
            Measurement.grid_w,
            Measurement.battery_w,
            Measurement.dt_s,
        ).where(
            Measurement.site_id == site.id,
            col(Measurement.device_id).is_(None),
            Measurement.ts > start,
            Measurement.ts <= end,
        )
    ).all()
    e = energy_from_rows(list(rows))
    buy, feed = tariff_for(session, site)
    co2 = float(get_section(session, "general")["co2_kg_per_kwh"])
    d = derived(e, buy, feed, co2)
    fc = session.exec(
        select(func.sum(ForecastPoint.power_w)).where(
            ForecastPoint.site_id == site.id, ForecastPoint.ts >= start, ForecastPoint.ts < end
        )
    ).one()
    stats = session.exec(
        select(DailyStats).where(DailyStats.site_id == site.id, DailyStats.day == day.isoformat())
    ).first()
    if stats is None:
        stats = DailyStats(site_id=site.id, day=day.isoformat())  # type: ignore[arg-type]
    if rows:
        for k in (
            "pv_wh",
            "load_wh",
            "import_wh",
            "export_wh",
            "charge_wh",
            "discharge_wh",
            "self_consumption_wh",
        ):
            setattr(stats, k, round(e.get(k, 0), 1))
        stats.savings_eur = d["savings_eur"]
        stats.co2_kg = d["co2_kg"]
    if fc:
        stats.forecast_wh = round(float(fc), 1)
    stats.updated_at = now_ts()
    if persist and (rows or fc):
        session.add(stats)
        session.commit()
        session.refresh(stats)
    return stats


def stats_dict(s: DailyStats, buy: float, feed: float, co2: float) -> dict[str, Any]:
    e = {
        k: getattr(s, k)
        for k in (
            "pv_wh",
            "load_wh",
            "import_wh",
            "export_wh",
            "charge_wh",
            "discharge_wh",
            "self_consumption_wh",
        )
    }
    out = {"day": s.day, **e, "forecast_wh": s.forecast_wh}
    out.update(derived(e, buy, feed, co2))
    return out


def sum_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    keys = (
        "pv_wh",
        "load_wh",
        "import_wh",
        "export_wh",
        "charge_wh",
        "discharge_wh",
        "self_consumption_wh",
        "savings_eur",
        "co2_kg",
    )
    out: dict[str, Any] = {k: round(sum(i.get(k) or 0 for i in items), 2) for k in keys}
    fcs = [i["forecast_wh"] for i in items if i.get("forecast_wh") is not None]
    out["forecast_wh"] = round(sum(fcs), 1) if fcs else None
    pv, load, imp = out["pv_wh"], out["load_wh"], out["import_wh"]
    out["self_consumption_pct"] = (
        round(out["self_consumption_wh"] / pv * 100, 1) if pv > 0 else None
    )
    out["autarky_pct"] = round(max(load - imp, 0) / load * 100, 1) if load > 0 else None
    return out


def today_kpis(session: Session, sites: list[Site]) -> dict[str, Any]:
    co2 = float(get_section(session, "general")["co2_kg_per_kwh"])
    items = []
    for site in sites:
        s = compute_day(session, site, local_today(site.timezone), persist=False)
        buy, feed = tariff_for(session, site)
        items.append(stats_dict(s, buy, feed, co2))
    return sum_stats(items)


# --- Verlauf -------------------------------------------------------------------


def _bucketed(session: Session, site_ids: list[int], start: int, end: int, bucket: int):
    b = Measurement.ts - (Measurement.ts % bucket)
    q = (
        select(
            Measurement.site_id,
            b.label("b"),
            func.avg(Measurement.pv_w),
            func.avg(Measurement.load_w),
            func.avg(Measurement.grid_w),
            func.avg(Measurement.battery_w),
            func.avg(Measurement.soc_pct),
        )
        .where(
            col(Measurement.site_id).in_(site_ids),
            col(Measurement.device_id).is_(None),
            Measurement.ts > start,
            Measurement.ts <= end,
        )
        .group_by(Measurement.site_id, "b")
        .order_by("b")
    )
    return session.exec(q).all()


def power_history(
    session: Session, sites: list[Site], start: int, end: int, bucket: int
) -> dict[str, Any]:
    ids = [s.id for s in sites if s.id is not None]
    rows = _bucketed(session, ids, start, end, bucket)
    by_ts: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    per_site: dict[int, dict[int, float]] = defaultdict(dict)
    for site_id, b, pv, load, grid, batt, soc in rows:
        slot = by_ts[int(b)]
        for key, v in (("pv", pv), ("load", load), ("grid", grid), ("battery", batt), ("soc", soc)):
            if v is not None:
                slot[key].append(float(v))
        if pv is not None:
            per_site[site_id][int(b)] = round(float(pv), 1)
    ts_sorted = sorted(by_ts)
    series: dict[str, list] = {"ts": [t + bucket // 2 for t in ts_sorted]}
    for key in ("pv", "load", "grid", "battery"):
        series[key] = [round(sum(by_ts[t][key]), 1) if by_ts[t][key] else None for t in ts_sorted]
    series["soc"] = [
        round(sum(by_ts[t]["soc"]) / len(by_ts[t]["soc"]), 1) if by_ts[t]["soc"] else None
        for t in ts_sorted
    ]
    fc_rows = session.exec(
        select(ForecastPoint.ts, func.sum(ForecastPoint.power_w))
        .where(
            col(ForecastPoint.site_id).in_(ids), ForecastPoint.ts >= start, ForecastPoint.ts < end
        )
        .group_by(ForecastPoint.ts)
        .order_by(ForecastPoint.ts)
    ).all()
    return {
        "resolution_s": bucket,
        "start": start,
        "end": end,
        "series": series,
        "forecast": {
            "ts": [int(t) + 1800 for t, _ in fc_rows],
            "pv": [round(float(p), 1) for _, p in fc_rows],
        },
        "per_site": {str(sid): [vals.get(t) for t in ts_sorted] for sid, vals in per_site.items()},
    }


def energy_history(
    session: Session, sites: list[Site], days: list[date], group: str = "day"
) -> dict[str, Any]:
    ids = [s.id for s in sites]
    co2 = float(get_section(session, "general")["co2_kg_per_kwh"])
    tariffs = {s.id: tariff_for(session, s) for s in sites}
    rows = session.exec(
        select(DailyStats).where(
            col(DailyStats.site_id).in_(ids),
            DailyStats.day >= days[0].isoformat(),
            DailyStats.day <= days[-1].isoformat(),
        )
    ).all()
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        key = r.day if group == "day" else r.day[:7]
        buy, feed = tariffs[r.site_id]
        buckets[key].append(stats_dict(r, buy, feed, co2))
    if group == "day":
        labels = [d.isoformat() for d in days]
    else:
        labels = sorted({d.isoformat()[:7] for d in days})
    summed = [sum_stats(buckets.get(lbl, [])) for lbl in labels]
    return {
        "labels": labels,
        "pv_kwh": [round(s["pv_wh"] / 1000, 2) for s in summed],
        "load_kwh": [round(s["load_wh"] / 1000, 2) for s in summed],
        "import_kwh": [round(s["import_wh"] / 1000, 2) for s in summed],
        "export_kwh": [round(s["export_wh"] / 1000, 2) for s in summed],
        "self_kwh": [round(s["self_consumption_wh"] / 1000, 2) for s in summed],
        "forecast_kwh": [
            round(s["forecast_wh"] / 1000, 2) if s["forecast_wh"] is not None else None
            for s in summed
        ],
        "savings_eur": [s["savings_eur"] for s in summed],
        "total": sum_stats([i for lbl in labels for i in buckets.get(lbl, [])]),
    }


def history(session: Session, sites: list[Site], rng: str, day: date) -> dict[str, Any]:
    tzname = sites[0].timezone if sites else "Europe/Berlin"
    if rng == "day":
        start, end = day_bounds(day, tzname)
        out = power_history(session, sites, start, end, 300)
    elif rng == "week":
        start, _ = day_bounds(day - timedelta(days=6), tzname)
        _, end = day_bounds(day, tzname)
        out = power_history(session, sites, start, end, 3600)
        out["energy"] = energy_history(
            session, sites, [day - timedelta(days=i) for i in range(6, -1, -1)]
        )
    elif rng == "month":
        first = day.replace(day=1)
        nxt = (first + timedelta(days=32)).replace(day=1)
        days = [first + timedelta(days=i) for i in range((nxt - first).days)]
        out = {"energy": energy_history(session, sites, days)}
    elif rng == "year":
        first = date(day.year, 1, 1)
        days = [first + timedelta(days=i) for i in range((date(day.year + 1, 1, 1) - first).days)]
        out = {"energy": energy_history(session, sites, days, group="month")}
    else:
        raise ValueError("range muss day, week, month oder year sein")
    out["range"] = rng
    out["date"] = day.isoformat()
    return out
