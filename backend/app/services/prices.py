"""Day-Ahead-Börsenstrompreise (Energy-Charts / Fraunhofer ISE, aWATTar) für DE-LU und AT.

Seit Oktober 2025 liefert der Day-Ahead-Markt 15-Minuten-Werte; die Auflösung wird aus den
Zeitstempeln abgeleitet. Neu abgerufen wird stündlich, solange die Preise für morgen fehlen
(sie erscheinen gegen 13–14 Uhr), sonst alle 6 Stunden.
"""

from __future__ import annotations

import time
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlmodel import Session, col, delete, select

from app.models import PricePoint

from .http import client
from .timeutil import tz

ENERGY_CHARTS = "https://api.energy-charts.info/price"
AWATTAR = {
    "DE-LU": "https://api.awattar.de/v1/marketdata",
    "AT": "https://api.awattar.at/v1/marketdata",
}
ZONES = ("DE-LU", "AT")
ZONE_TZ = "Europe/Berlin"


async def fetch_energy_charts(zone: str, start: date, end: date) -> list[tuple[int, int, float]]:
    async with client() as c:
        r = await c.get(
            ENERGY_CHARTS,
            params={"bzn": zone, "start": start.isoformat(), "end": end.isoformat()},
        )
        r.raise_for_status()
        data = r.json()
    ts = data.get("unix_seconds") or []
    prices = data.get("price") or []
    out = []
    for i, t in enumerate(ts):
        p = prices[i] if i < len(prices) else None
        if p is None:
            continue
        dur = (ts[i + 1] - t) if i + 1 < len(ts) else (ts[i] - ts[i - 1] if i else 3600)
        out.append((int(t), int(dur), float(p)))
    return out


async def fetch_awattar(zone: str, start: date, end: date) -> list[tuple[int, int, float]]:
    url = AWATTAR.get(zone)
    if not url:
        raise ValueError(f"aWATTar unterstützt {zone} nicht")
    z = tz(ZONE_TZ)
    s = int(datetime(start.year, start.month, start.day, tzinfo=z).timestamp() * 1000)
    e = int(datetime(end.year, end.month, end.day, tzinfo=z).timestamp() * 1000) + 86400_000
    async with client() as c:
        r = await c.get(url, params={"start": s, "end": e})
        r.raise_for_status()
        data = r.json()
    return [
        (
            int(d["start_timestamp"] // 1000),
            int((d["end_timestamp"] - d["start_timestamp"]) // 1000),
            float(d["marketprice"]),
        )
        for d in data.get("data", [])
    ]


async def refresh_prices(session: Session, zone: str, provider: str = "energy_charts") -> int:
    today = datetime.now(tz(ZONE_TZ)).date()
    start, end = today - timedelta(days=1), today + timedelta(days=1)
    fetchers = [fetch_energy_charts, fetch_awattar]
    if provider == "awattar":
        fetchers.reverse()
    last_exc: Exception | None = None
    for fetch in fetchers:
        try:
            points = await fetch(zone, start, end)
            break
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
    else:
        raise RuntimeError(f"Keine Preisquelle erreichbar: {last_exc}")
    if not points:
        return 0
    ts_list = [p[0] for p in points]
    session.exec(  # type: ignore[call-overload]
        delete(PricePoint).where(PricePoint.zone == zone, col(PricePoint.ts).in_(ts_list))
    )
    for t, dur, eur in points:
        session.add(PricePoint(zone=zone, ts=t, duration_s=dur, eur_mwh=eur))
    # alte Werte (> 60 Tage) entfernen
    session.exec(  # type: ignore[call-overload]
        delete(PricePoint).where(PricePoint.zone == zone, PricePoint.ts < time.time() - 60 * 86400)
    )
    session.commit()
    return len(points)


def has_tomorrow(session: Session, zone: str) -> bool:
    z = tz(ZONE_TZ)
    tomorrow = datetime.now(z).date() + timedelta(days=1)
    start = int(datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=z).timestamp())
    return (
        session.exec(
            select(PricePoint.id).where(PricePoint.zone == zone, PricePoint.ts >= start + 3600 * 20)
        ).first()
        is not None
    )


def cheapest_window(
    points: list[dict[str, Any]], hours: float = 3.0, after: int | None = None
) -> dict[str, Any] | None:
    """Günstigstes zusammenhängendes Zeitfenster der Länge ``hours``."""
    pts = [p for p in points if after is None or p["ts"] + p["duration_s"] > after]
    if not pts:
        return None
    best: dict[str, Any] | None = None
    for i in range(len(pts)):
        dur, cost, j = 0, 0.0, i
        while j < len(pts) and dur < hours * 3600:
            if j > i and pts[j]["ts"] != pts[j - 1]["ts"] + pts[j - 1]["duration_s"]:
                break
            dur += pts[j]["duration_s"]
            cost += pts[j]["ct_kwh"] * pts[j]["duration_s"]
            j += 1
        if dur < hours * 3600:
            continue
        avg = cost / dur
        if best is None or avg < best["avg_ct_kwh"]:
            best = {"start": pts[i]["ts"], "end": pts[i]["ts"] + dur, "avg_ct_kwh": round(avg, 2)}
    return best


def get_prices(session: Session, zone: str, markup_eur_kwh: float = 0.0) -> dict[str, Any]:
    z = tz(ZONE_TZ)
    today = datetime.now(z).date()
    start = int(datetime(today.year, today.month, today.day, tzinfo=z).timestamp())
    end = start + 2 * 86400 + 3600
    rows = session.exec(
        select(PricePoint)
        .where(PricePoint.zone == zone, PricePoint.ts >= start, PricePoint.ts < end)
        .order_by(PricePoint.ts)
    ).all()
    points = [
        {
            "ts": r.ts,
            "duration_s": r.duration_s,
            "eur_mwh": r.eur_mwh,
            "ct_kwh": round(r.eur_mwh / 10, 3),
            "total_ct_kwh": round(r.eur_mwh / 10 * 1.19 + markup_eur_kwh * 100, 2)
            if markup_eur_kwh
            else None,
        }
        for r in rows
    ]
    now = int(time.time())
    current = next((p for p in points if p["ts"] <= now < p["ts"] + p["duration_s"]), None)
    upcoming = [p for p in points if p["ts"] + p["duration_s"] > now]
    cheapest = min(upcoming, key=lambda p: p["ct_kwh"]) if upcoming else None
    priciest = max(upcoming, key=lambda p: p["ct_kwh"]) if upcoming else None
    return {
        "zone": zone,
        "points": points,
        "current": current,
        "cheapest": cheapest,
        "most_expensive": priciest,
        "cheapest_3h": cheapest_window(points, 3, after=now),
        "updated_at": max((r.ts for r in rows), default=None),
        "generated_at": datetime.now(UTC).isoformat(),
    }
