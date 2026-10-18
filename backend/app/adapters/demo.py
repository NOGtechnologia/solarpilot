"""Demo-Simulator: realistische 10-kWp-Anlage mit 10-kWh-Batterie.

Die Simulation ist deterministisch (gleicher Zeitpunkt ⇒ gleiche Wolken und Verbraucher),
damit Live-Werte und nachträglich erzeugte Historie zusammenpassen.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.services.sun import clear_sky_ghi, plane_of_array, solar_position

from .base import Capabilities, ConfigField, InverterAdapter, LiveSnapshot, StringValue
from .registry import register

PERFORMANCE_RATIO = 0.78


def _noise(n: float) -> float:
    """Schnelles deterministisches Rauschen in [0, 1)."""
    x = math.sin(n * 12.9898 + 78.233) * 43758.5453
    return x - math.floor(x)


@dataclass
class _State:
    ts: datetime
    soc_wh: float
    energy_today_wh: float
    day: date


@dataclass
class _Sample:
    ts: datetime
    pv: float
    load: float
    grid: float
    battery: float | None
    soc: float | None
    energy_today: float


class DemoSimulator:
    def __init__(
        self,
        lat: float,
        lon: float,
        tz: str = "Europe/Berlin",
        kwp: float = 10.0,
        battery_kwh: float = 10.0,
        tilt: float = 35.0,
        azimuth: float = 180.0,
        seed: str = "solarpilot",
    ) -> None:
        self.lat, self.lon = lat, lon
        self.tz = ZoneInfo(tz)
        self.kwp = kwp
        self.capacity_wh = battery_kwh * 1000
        self.tilt, self.azimuth = tilt, azimuth
        self.seed = seed
        self.max_batt_w = min(5000.0, self.capacity_wh / 2) if self.capacity_wh else 0.0
        self.min_soc_wh = self.capacity_wh * 0.05
        self._day_cache = lru_cache(maxsize=512)(self._day_profile)

    # --- Wetter -----------------------------------------------------------------
    def _day_profile(self, ordinal: int) -> tuple[float, list[float], float]:
        rng = random.Random(f"{self.seed}:{ordinal}")
        d = date.fromordinal(ordinal)
        season = 0.5 + 0.5 * math.cos((d.timetuple().tm_yday - 172) / 365 * 2 * math.pi)
        r = rng.random()
        if r < 0.06 + 0.3 * season:
            clear = 0.9 + 0.1 * rng.random()  # sonnig
        elif r < 0.4 + 0.25 * season:
            clear = 0.45 + 0.3 * rng.random()  # wechselhaft
        else:
            clear = 0.08 + 0.22 * rng.random()  # bedeckt
        knots = [rng.random() for _ in range(98)]
        soc0 = 0.25 + 0.3 * rng.random()
        return clear, knots, soc0

    def day_clearness(self, d: date) -> float:
        return self._day_cache(d.toordinal())[0]

    def cloud_factor(self, local: datetime) -> float:
        base, knots, _ = self._day_cache(local.toordinal())
        knot = (local.hour * 60 + local.minute + local.second / 60) / 15
        k0 = int(knot)
        frac = knot - k0
        w = (1 - math.cos(frac * math.pi)) / 2
        noise = knots[k0] * (1 - w) + knots[k0 + 1] * w
        variability = 1 - base if base < 0.9 else 0.08
        return max(0.05, min(1.0, base + (noise - 0.5) * 2 * variability))

    # --- Erzeugung und Verbrauch ------------------------------------------------
    def pv_w(self, ts: datetime, local: datetime | None = None) -> float:
        sun = solar_position(ts, self.lat, self.lon)
        if sun.elevation_deg <= 0:
            return 0.0
        local = local or ts.astimezone(self.tz)
        ghi = clear_sky_ghi(sun.elevation_deg)
        poa = plane_of_array(ghi, sun, self.tilt, self.azimuth)
        return max(0.0, self.kwp * poa * PERFORMANCE_RATIO * self.cloud_factor(local))

    def load_w(self, ts: datetime, local: datetime | None = None) -> float:
        local = local or ts.astimezone(self.tz)
        o = local.toordinal()
        h = local.hour + local.minute / 60
        load = 260.0
        load += 70 * (1 + math.sin(local.minute / 60 * 2 * math.pi * 3))  # Kühlschrank
        load += 650 * math.exp(-(((h - 7.2) / 0.6) ** 2))  # Morgen
        load += 500 * math.exp(-(((h - 12.5) / 0.7) ** 2))  # Mittag
        load += 900 * math.exp(-(((h - 19.0) / 1.6) ** 2))  # Abend
        if o % 3 == 0 and 10.0 <= h < 11.3:
            load += 1900  # Waschmaschine
        if o % 2 == 0 and 20.0 <= h < 21.0:
            load += 1600  # Spülmaschine
        if local.weekday() >= 5 and 12.0 <= h < 12.8:
            load += 2200  # Backofen am Wochenende
        load += (_noise(ts.timestamp() // 30) - 0.5) * 120
        return max(120.0, load)

    # --- Simulation -------------------------------------------------------------
    def _midnight(self, ts: datetime) -> datetime:
        local = ts.astimezone(self.tz)
        return datetime(local.year, local.month, local.day, tzinfo=self.tz).astimezone(UTC)

    def initial_state(self, ts: datetime) -> _State:
        d = ts.astimezone(self.tz).date()
        soc = self.capacity_wh * self._day_cache(d.toordinal())[2]
        return _State(ts=self._midnight(ts), soc_wh=soc, energy_today_wh=0.0, day=d)

    def advance(self, state: _State, ts: datetime, max_step_s: int = 60) -> _Sample:
        """Simuliert vom letzten Zustand bis ``ts``."""
        sample: _Sample | None = None
        while state.ts < ts or sample is None:
            nxt = min(ts, state.ts + timedelta(seconds=max_step_s))
            local = nxt.astimezone(self.tz)
            if local.date() != state.day:
                state.day = local.date()
                state.energy_today_wh = 0.0
            dt_h = max((nxt - state.ts).total_seconds(), 0.0) / 3600
            pv, load = self.pv_w(nxt, local), self.load_w(nxt, local)
            net = pv - load
            batt = 0.0
            if self.capacity_wh and dt_h:
                if net > 0:
                    room = (self.capacity_wh - state.soc_wh) / dt_h
                    batt = min(net, self.max_batt_w, max(room, 0))
                    state.soc_wh += batt * dt_h * 0.96
                else:
                    avail = (state.soc_wh - self.min_soc_wh) / dt_h
                    batt = -min(-net, self.max_batt_w, max(avail, 0))
                    state.soc_wh += batt * dt_h
            state.soc_wh = min(max(state.soc_wh, 0), self.capacity_wh)
            state.energy_today_wh += pv * dt_h
            state.ts = nxt
            sample = _Sample(
                ts=nxt,
                pv=pv,
                load=load,
                grid=load - pv + batt,
                battery=batt if self.capacity_wh else None,
                soc=state.soc_wh / self.capacity_wh * 100 if self.capacity_wh else None,
                energy_today=state.energy_today_wh,
            )
            if dt_h == 0:
                break
        return sample

    @staticmethod
    def to_snapshot(s: _Sample) -> LiveSnapshot:
        r = round
        return LiveSnapshot(
            timestamp_utc=s.ts,
            pv_power_w=r(s.pv, 1),
            load_power_w=r(s.load, 1),
            grid_power_w=r(s.grid, 1),
            battery_power_w=r(s.battery, 1) if s.battery is not None else None,
            battery_soc_pct=r(s.soc, 1) if s.soc is not None else None,
            energy_today_wh=r(s.energy_today, 1),
            temperature_c=r(18 + s.pv / 1000 * 3.5, 1),
            strings=[
                StringValue(name="String 1", power_w=r(s.pv * 0.55, 1)),
                StringValue(name="String 2", power_w=r(s.pv * 0.45, 1)),
            ],
        )

    def step(self, state: _State, ts: datetime) -> LiveSnapshot:
        return self.to_snapshot(self.advance(state, ts))

    def simulate_raw(self, start: datetime, end: datetime, step_s: int = 60) -> Iterator[_Sample]:
        state = self.initial_state(start)
        t = state.ts
        while t + timedelta(seconds=step_s) <= start:
            t += timedelta(seconds=step_s)
            self.advance(state, t, max_step_s=step_s)
        t += timedelta(seconds=step_s)
        while t <= end:
            yield self.advance(state, t, max_step_s=step_s)
            t += timedelta(seconds=step_s)

    def simulate(self, start: datetime, end: datetime, step_s: int = 60) -> Iterator[LiveSnapshot]:
        for s in self.simulate_raw(start, end, step_s):
            yield self.to_snapshot(s)


@register
class DemoAdapter(InverterAdapter):
    type_name = "demo"
    display_name = "Demo-Simulator"
    vendor = "SolarPilot"
    connection = "simulated"
    status = "stable"
    default_role = "hybrid"
    capabilities = Capabilities(
        pv=True, load=True, grid=True, battery=True, strings=True, history=True
    )
    config_schema = [
        ConfigField(
            name="kwp",
            label_de="Leistung (kWp)",
            label_en="Peak power (kWp)",
            type="number",
            default=10.0,
        ),
        ConfigField(
            name="battery_kwh",
            label_de="Batterie (kWh)",
            label_en="Battery (kWh)",
            type="number",
            default=10.0,
        ),
    ]
    docs = "demo"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.sim = DemoSimulator(
            lat=self.site.lat,
            lon=self.site.lon,
            tz=self.site.timezone,
            kwp=float(self.config.get("kwp") or 10),
            battery_kwh=float(self.config.get("battery_kwh") or 0),
        )
        self._state: _State | None = None

    async def read_live(self) -> LiveSnapshot:
        now = datetime.now(UTC)
        if self._state is None:
            self._state = self.sim.initial_state(now)
        return self.sim.step(self._state, now)

    async def read_history(self, start: datetime, end: datetime) -> list[LiveSnapshot]:
        return list(self.sim.simulate(start, end, step_s=60))
