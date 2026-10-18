"""Legt eine Demo-Anlage an und erzeugt Historie, damit alle Ansichten sofort Daten zeigen."""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, delete

from app.adapters.demo import DemoSimulator
from app.models import DailyStats, Device, ForecastPoint, Measurement, Site

from .stats import derived, energy_from_rows, tariff_for
from .timeutil import local_day_of, tz

DEMO_LAT, DEMO_LON = 53.08, 8.80  # Bremen


def create_demo_site(
    session: Session,
    name: str = "Demo-Anlage",
    lat: float = DEMO_LAT,
    lon: float = DEMO_LON,
    timezone: str = "Europe/Berlin",
    minute_days: int = 7,
    daily_days: int = 400,
) -> Site:
    site = Site(
        name=name,
        lat=lat,
        lon=lon,
        timezone=timezone,
        battery_kwh=10.0,
        source="demo",
        arrays=[{"kwp": 10.0, "tilt": 35, "azimuth": 180, "losses_pct": 14}],
        color="#F5A524",
    )
    session.add(site)
    session.commit()
    session.refresh(site)
    dev = Device(
        site_id=site.id,
        name="Demo-Wechselrichter",
        type="demo",
        role="hybrid",  # type: ignore[arg-type]
        config={"kwp": 10.0, "battery_kwh": 10.0},
    )
    session.add(dev)
    session.commit()
    session.refresh(dev)
    backfill(session, site, dev, minute_days=minute_days, daily_days=daily_days)
    return site


def backfill(
    session: Session, site: Site, dev: Device, minute_days: int = 7, daily_days: int = 400
) -> None:
    sim = DemoSimulator(site.lat, site.lon, site.timezone, kwp=10.0, battery_kwh=10.0)
    z = tz(site.timezone)
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    local_midnight = datetime.now(z).replace(hour=0, minute=0, second=0, microsecond=0)
    start_min = (local_midnight - timedelta(days=minute_days)).astimezone(UTC)
    rng = random.Random(f"{site.id}")
    buy, feed = tariff_for(session, site)
    session.commit()  # Lesetransaktion beenden: erst rechnen, dann kurz schreiben

    # Minutenwerte der letzten Tage (für Tages-/Wochenansicht)
    rows: list[dict] = []
    hourly_pv: dict[int, list[float]] = defaultdict(list)
    for sm in sim.simulate_raw(start_min, now - timedelta(minutes=1), step_s=60):
        ts = int(sm.ts.timestamp())
        base = dict(
            site_id=site.id,
            ts=ts,
            dt_s=60,
            pv_w=round(sm.pv, 1),
            load_w=round(sm.load, 1),
            grid_w=round(sm.grid, 1),
            battery_w=round(sm.battery or 0, 1),
            soc_pct=round(sm.soc or 0, 1),
            energy_today_wh=round(sm.energy_today, 1),
        )
        rows.append({**base, "device_id": None})
        if ts >= now.timestamp() - 2 * 86400:
            rows.append({**base, "device_id": dev.id})
        hourly_pv[(ts - 1) // 3600 * 3600].append(sm.pv)

    # Prognose-Punkte (Ist ± Abweichung), damit die Prognoselinie sichtbar ist
    fc_rows = []
    for hour, vals in hourly_pv.items():
        avg = sum(vals) / len(vals)
        fc_rows.append(
            dict(
                site_id=site.id,
                ts=hour,
                power_w=round(avg * rng.uniform(0.85, 1.15), 1),
                cloud_cover_pct=None,
            )
        )

    # Tageswerte für Monats-/Jahresansicht (10-Minuten-Simulation)
    first = (local_midnight - timedelta(days=daily_days)).astimezone(UTC)
    by_day: dict[str, list[tuple]] = defaultdict(list)
    for sm in sim.simulate_raw(first, local_midnight.astimezone(UTC), 600):
        d = local_day_of(int(sm.ts.timestamp()) - 1, site.timezone).isoformat()
        by_day[d].append((sm.pv, sm.load, sm.grid, sm.battery, 600))
    stats = []
    for day, drow in by_day.items():
        e = energy_from_rows(drow)
        d = derived(e, buy, feed, 0.38)
        clear = sim.day_clearness(datetime.fromisoformat(day).date()) >= 0.9
        stats.append(
            dict(
                site_id=site.id,
                day=day,
                **{k: round(v, 1) for k, v in e.items()},
                forecast_wh=round(e["pv_wh"] * rng.uniform(0.85, 1.15), 1),
                clear_sky=clear,
                savings_eur=d["savings_eur"],
                co2_kg=d["co2_kg"],
            )
        )
    for model in (Measurement, DailyStats, ForecastPoint):
        session.exec(delete(model).where(model.site_id == site.id))  # type: ignore[call-overload]
    session.bulk_insert_mappings(Measurement, rows)  # type: ignore[arg-type]
    session.bulk_insert_mappings(ForecastPoint, fc_rows)  # type: ignore[arg-type]
    session.bulk_insert_mappings(DailyStats, stats)  # type: ignore[arg-type]
    session.commit()
