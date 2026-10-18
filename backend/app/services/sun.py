"""Sonnenstand nach NOAA-Algorithmus, Sonnenauf-/-untergang und Clear-Sky-Einstrahlung."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta


@dataclass(frozen=True)
class SunPosition:
    elevation_deg: float
    azimuth_deg: float  # 0 = Nord, 90 = Ost, 180 = Süd


def _clamp(x: float) -> float:
    return max(-1.0, min(1.0, x))


def _solar_terms(ts: datetime) -> tuple[float, float]:
    """Gibt (Deklination°, Zeitgleichung in Minuten) zurück."""
    jd = ts.timestamp() / 86400 + 2440587.5
    jc = (jd - 2451545) / 36525
    l0 = (280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360
    m = 357.52911 + jc * (35999.05029 - 0.0001537 * jc)
    ecc = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)
    mr = math.radians(m)
    ctr = (
        math.sin(mr) * (1.914602 - jc * (0.004817 + 0.000014 * jc))
        + math.sin(2 * mr) * (0.019993 - 0.000101 * jc)
        + math.sin(3 * mr) * 0.000289
    )
    true_long = l0 + ctr
    omega = 125.04 - 1934.136 * jc
    app_long = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    mean_obliq = 23 + (26 + (21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813))) / 60) / 60
    obliq = mean_obliq + 0.00256 * math.cos(math.radians(omega))
    decl = math.degrees(math.asin(math.sin(math.radians(obliq)) * math.sin(math.radians(app_long))))
    y = math.tan(math.radians(obliq / 2)) ** 2
    l0r = math.radians(l0)
    eq_time = 4 * math.degrees(
        y * math.sin(2 * l0r)
        - 2 * ecc * math.sin(mr)
        + 4 * ecc * y * math.sin(mr) * math.cos(2 * l0r)
        - 0.5 * y * y * math.sin(4 * l0r)
        - 1.25 * ecc * ecc * math.sin(2 * mr)
    )
    return decl, eq_time


def solar_position(ts: datetime, lat: float, lon: float) -> SunPosition:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    ts = ts.astimezone(UTC)
    decl, eq_time = _solar_terms(ts)
    minutes = ts.hour * 60 + ts.minute + ts.second / 60
    tst = (minutes + eq_time + 4 * lon) % 1440
    ha = tst / 4 - 180
    latr, declr, har = math.radians(lat), math.radians(decl), math.radians(ha)
    cos_zen = _clamp(
        math.sin(latr) * math.sin(declr) + math.cos(latr) * math.cos(declr) * math.cos(har)
    )
    zen = math.degrees(math.acos(cos_zen))
    zenr = math.radians(zen)
    denom = math.cos(latr) * math.sin(zenr)
    if abs(denom) < 1e-9:
        az = 180.0
    else:
        a = math.degrees(
            math.acos(_clamp((math.sin(latr) * math.cos(zenr) - math.sin(declr)) / denom))
        )
        az = (a + 180) % 360 if ha > 0 else (540 - a) % 360
    return SunPosition(elevation_deg=90 - zen, azimuth_deg=az)


def sunrise_sunset(day: date, lat: float, lon: float) -> tuple[datetime | None, datetime | None]:
    """Sonnenauf- und -untergang (UTC). ``None`` bei Polartag/-nacht."""
    noon = datetime(day.year, day.month, day.day, 12, tzinfo=UTC) - timedelta(minutes=4 * lon)
    decl, eq_time = _solar_terms(noon)
    latr, declr = math.radians(lat), math.radians(decl)
    cos_ha = math.cos(math.radians(90.833)) / (math.cos(latr) * math.cos(declr)) - math.tan(
        latr
    ) * math.tan(declr)
    if cos_ha > 1 or cos_ha < -1:
        return None, None
    ha = math.degrees(math.acos(cos_ha))
    solar_noon = 720 - 4 * lon - eq_time
    base = datetime(day.year, day.month, day.day, tzinfo=UTC)
    return base + timedelta(minutes=solar_noon - 4 * ha), base + timedelta(
        minutes=solar_noon + 4 * ha
    )


def clear_sky_ghi(elevation_deg: float) -> float:
    """Globalstrahlung bei klarem Himmel (Haurwitz-Modell) in W/m²."""
    if elevation_deg <= 0:
        return 0.0
    cz = math.sin(math.radians(elevation_deg))
    return 1098 * cz * math.exp(-0.057 / max(cz, 0.01))


def plane_of_array(
    ghi: float,
    sun: SunPosition,
    tilt_deg: float,
    azimuth_deg: float,
    diffuse_fraction: float = 0.15,
) -> float:
    """Einstrahlung auf die geneigte Modulfläche (einfaches isotropes Modell)."""
    if ghi <= 0 or sun.elevation_deg <= 0:
        return 0.0
    zen = math.radians(90 - sun.elevation_deg)
    tilt = math.radians(tilt_deg)
    cos_inc = math.cos(zen) * math.cos(tilt) + math.sin(zen) * math.sin(tilt) * math.cos(
        math.radians(sun.azimuth_deg - azimuth_deg)
    )
    dhi = ghi * diffuse_fraction
    dni = (ghi - dhi) / max(math.cos(zen), 0.05)
    beam = dni * max(cos_inc, 0.0)
    diffuse = dhi * (1 + math.cos(tilt)) / 2
    reflected = ghi * 0.2 * (1 - math.cos(tilt)) / 2
    return max(0.0, beam + diffuse + reflected)
