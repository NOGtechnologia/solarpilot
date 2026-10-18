"""Zusammenfassen mehrerer Geräte zu einer Site und mehrerer Sites zu „Alle Anlagen“."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from app.adapters.base import LiveSnapshot


def _sum(values: Iterable[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return round(sum(vals), 1) if vals else None


def _avg(values: Iterable[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


def aggregate_site(items: list[tuple[str, LiveSnapshot]]) -> LiveSnapshot:
    """``items`` = Liste von (Rolle, Snapshot) der *online* Geräte einer Site.

    Pro Site zählt genau ein ``grid_meter`` für den Netzwert; nur ohne Netzzähler werden
    Netzwerte der Wechselrichter verwendet (Summe). Verbrauch wird aus der Bilanz berechnet,
    wenn ein Netzwert vorhanden ist.
    """
    pv = _sum(s.pv_power_w for role, s in items if role != "grid_meter")
    battery = _sum(s.battery_power_w for _, s in items)
    soc = _avg(s.battery_soc_pct for _, s in items)
    meters = [
        s.grid_power_w for role, s in items if role == "grid_meter" and s.grid_power_w is not None
    ]
    grid = (
        meters[0] if meters else _sum(s.grid_power_w for role, s in items if role != "grid_meter")
    )
    if grid is not None:
        load: float | None = max((pv or 0) + grid - (battery or 0), 0.0)
        load = round(load, 1)
    else:
        load = _sum(s.load_power_w for _, s in items)
    ts = max((s.timestamp_utc for _, s in items), default=datetime.now(UTC))
    return LiveSnapshot(
        timestamp_utc=ts,
        pv_power_w=pv if pv is not None else (0.0 if items else None),
        load_power_w=load,
        grid_power_w=grid,
        battery_power_w=battery,
        battery_soc_pct=soc,
        energy_today_wh=_sum(s.energy_today_wh for role, s in items if role != "grid_meter"),
        temperature_c=_avg(s.temperature_c for _, s in items),
    )


def aggregate_all(snaps: list[LiveSnapshot]) -> LiveSnapshot:
    ts = max((s.timestamp_utc for s in snaps), default=datetime.now(UTC))
    return LiveSnapshot(
        timestamp_utc=ts,
        pv_power_w=_sum(s.pv_power_w for s in snaps),
        load_power_w=_sum(s.load_power_w for s in snaps),
        grid_power_w=_sum(s.grid_power_w for s in snaps),
        battery_power_w=_sum(s.battery_power_w for s in snaps),
        battery_soc_pct=_avg(s.battery_soc_pct for s in snaps),
        energy_today_wh=_sum(s.energy_today_wh for s in snaps),
    )


def average_snapshots(snaps: list[LiveSnapshot]) -> LiveSnapshot:
    """Mittelwert über ein Speicherintervall (SoC/Tagesenergie: letzter Wert)."""
    if not snaps:
        return LiveSnapshot()
    last = snaps[-1]
    return LiveSnapshot(
        timestamp_utc=last.timestamp_utc,
        pv_power_w=_avg(s.pv_power_w for s in snaps),
        load_power_w=_avg(s.load_power_w for s in snaps),
        grid_power_w=_avg(s.grid_power_w for s in snaps),
        battery_power_w=_avg(s.battery_power_w for s in snaps),
        battery_soc_pct=last.battery_soc_pct,
        energy_today_wh=last.energy_today_wh,
    )
