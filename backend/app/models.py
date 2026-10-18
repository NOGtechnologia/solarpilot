"""Datenmodell (SQLModel). Zeitstempel als Unix-Sekunden (UTC)."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy import JSON, Column, Index, UniqueConstraint
from sqlmodel import Field, SQLModel

DEVICE_ROLES = ("inverter", "hybrid", "battery", "grid_meter", "meter", "ev_charger")


def now_ts() -> int:
    return int(time.time())


class Site(SQLModel, table=True):
    """Ein Standort / eine Anlage mit beliebig vielen Geräten."""

    id: int | None = Field(default=None, primary_key=True)
    name: str
    lat: float
    lon: float
    timezone: str = "Europe/Berlin"
    # Liste von Modulfeldern: {"kwp": 9.8, "tilt": 35, "azimuth": 180, "losses_pct": 14}
    arrays: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    battery_kwh: float | None = None
    buy_eur_kwh: float | None = None
    feed_in_eur_kwh: float | None = None
    color: str | None = None
    source: str = "ui"  # ui | file | demo
    created_at: int = Field(default_factory=now_ts)


class Device(SQLModel, table=True):
    """Wechselrichter, Batterie, Zähler, Wallbox – jeweils über einen Adapter angebunden."""

    id: int | None = Field(default=None, primary_key=True)
    site_id: int = Field(foreign_key="site.id", index=True)
    name: str
    type: str  # Adapter-Typname
    role: str = "inverter"
    config: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    secrets_enc: str = ""
    enabled: bool = True
    last_seen: int | None = None
    last_error: str | None = None
    created_at: int = Field(default_factory=now_ts)


class Measurement(SQLModel, table=True):
    """Mittelwerte eines Speicherintervalls. ``device_id`` None = Summe der Site."""

    __table_args__ = (Index("ix_meas_site_dev_ts", "site_id", "device_id", "ts"),)

    id: int | None = Field(default=None, primary_key=True)
    site_id: int = Field(foreign_key="site.id")
    device_id: int | None = Field(default=None, foreign_key="device.id")
    ts: int  # Ende des Intervalls, Unix-Sekunden UTC
    dt_s: int = 60
    pv_w: float | None = None
    load_w: float | None = None
    grid_w: float | None = None
    battery_w: float | None = None
    soc_pct: float | None = None
    energy_today_wh: float | None = None


class DailyStats(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("site_id", "day", name="uq_daily_site_day"),)

    id: int | None = Field(default=None, primary_key=True)
    site_id: int = Field(foreign_key="site.id", index=True)
    day: str  # YYYY-MM-DD in lokaler Zeit der Site
    pv_wh: float = 0
    load_wh: float = 0
    import_wh: float = 0
    export_wh: float = 0
    charge_wh: float = 0
    discharge_wh: float = 0
    self_consumption_wh: float = 0
    forecast_wh: float | None = None
    clear_sky: bool | None = None
    savings_eur: float = 0
    co2_kg: float = 0
    updated_at: int = Field(default_factory=now_ts)


class ForecastPoint(SQLModel, table=True):
    """Letzte Prognose je Stunde (Beginn der Stunde, UTC)."""

    __table_args__ = (UniqueConstraint("site_id", "ts", name="uq_fc_site_ts"),)

    id: int | None = Field(default=None, primary_key=True)
    site_id: int = Field(foreign_key="site.id", index=True)
    ts: int
    power_w: float
    cloud_cover_pct: float | None = None
    created_at: int = Field(default_factory=now_ts)


class PricePoint(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("zone", "ts", name="uq_price_zone_ts"),)

    id: int | None = Field(default=None, primary_key=True)
    zone: str
    ts: int  # Beginn des Intervalls
    duration_s: int = 3600
    eur_mwh: float


class NewsItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    guid: str = Field(index=True, unique=True)
    title: str
    source: str
    link: str
    published: int
    teaser: str = ""
    lang: str = "de"
    fetched_at: int = Field(default_factory=now_ts)


class Setting(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: Any = Field(default=None, sa_column=Column(JSON))
    updated_at: int = Field(default_factory=now_ts)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    is_admin: bool = False
    created_at: int = Field(default_factory=now_ts)
