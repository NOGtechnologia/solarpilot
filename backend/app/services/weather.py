"""Wetter von Open-Meteo (frei, ohne Schlüssel) und DWD-Warnungen über Bright Sky."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from app.models import Site

from .cache import cached
from .http import client
from .sun import solar_position, sunrise_sunset
from .timeutil import tz

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
BRIGHT_SKY_ALERTS = "https://api.brightsky.dev/alerts"
WEATHER_TTL = 30 * 60


async def fetch_open_meteo(lat: float, lon: float, timezone: str = "UTC") -> dict[str, Any]:
    # Tageswerte in lokaler Zeit der Site (Unix-Zeitstempel = lokale Mitternacht)
    params = {
        "latitude": round(lat, 3),
        "longitude": round(lon, 3),
        "current": "temperature_2m,weather_code,cloud_cover,wind_speed_10m,is_day",
        "hourly": "temperature_2m,cloud_cover,weather_code,shortwave_radiation,"
        "precipitation_probability,is_day",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,"
        "shortwave_radiation_sum,precipitation_probability_max,cloud_cover_mean",
        "timezone": timezone,
        "timeformat": "unixtime",
        "forecast_days": 7,
    }
    async with client() as c:
        r = await c.get(OPEN_METEO, params=params)
        r.raise_for_status()
        return r.json()


async def fetch_alerts(lat: float, lon: float) -> list[dict[str, Any]]:
    async with client() as c:
        r = await c.get(BRIGHT_SKY_ALERTS, params={"lat": lat, "lon": lon})
        r.raise_for_status()
        data = r.json()
    out = []
    for a in data.get("alerts", []):
        out.append(
            {
                "headline_de": a.get("headline_de"),
                "headline_en": a.get("headline_en"),
                "severity": a.get("severity"),
                "event_de": a.get("event_de"),
                "event_en": a.get("event_en"),
                "onset": a.get("onset"),
                "expires": a.get("expires"),
            }
        )
    return out


def in_germany(lat: float, lon: float) -> bool:
    return 47.2 <= lat <= 55.1 and 5.8 <= lon <= 15.1


def shape_weather(raw: dict[str, Any]) -> dict[str, Any]:
    cur = raw.get("current", {})
    hourly = raw.get("hourly", {})
    daily = raw.get("daily", {})
    days = []
    for i, t in enumerate(daily.get("time", [])):

        def g(key: str, i: int = i) -> Any:
            vals = daily.get(key) or []
            return vals[i] if i < len(vals) else None

        days.append(
            {
                "ts": t,
                "weather_code": g("weather_code"),
                "temp_max": g("temperature_2m_max"),
                "temp_min": g("temperature_2m_min"),
                "sunrise": g("sunrise"),
                "sunset": g("sunset"),
                "radiation_mj": g("shortwave_radiation_sum"),
                "precipitation_probability": g("precipitation_probability_max"),
                "cloud_cover": g("cloud_cover_mean"),
            }
        )
    return {
        "current": {
            "ts": cur.get("time"),
            "temperature": cur.get("temperature_2m"),
            "weather_code": cur.get("weather_code"),
            "cloud_cover": cur.get("cloud_cover"),
            "wind_speed": cur.get("wind_speed_10m"),
            "is_day": cur.get("is_day"),
        },
        "hourly": {
            "ts": hourly.get("time", []),
            "temperature": hourly.get("temperature_2m", []),
            "cloud_cover": hourly.get("cloud_cover", []),
            "weather_code": hourly.get("weather_code", []),
            "radiation": hourly.get("shortwave_radiation", []),
            "precipitation_probability": hourly.get("precipitation_probability", []),
        },
        "daily": days,
    }


def sun_info(site: Site, when: datetime | None = None) -> dict[str, Any]:
    when = when or datetime.now(UTC)
    local_day: date = when.astimezone(tz(site.timezone)).date()
    rise, set_ = sunrise_sunset(local_day, site.lat, site.lon)
    pos = solar_position(when, site.lat, site.lon)
    return {
        "sunrise": int(rise.timestamp()) if rise else None,
        "sunset": int(set_.timestamp()) if set_ else None,
        "elevation": round(pos.elevation_deg, 2),
        "azimuth": round(pos.azimuth_deg, 2),
    }


async def site_weather(site: Site, alerts_enabled: bool = True) -> dict[str, Any]:
    key = f"weather:{site.lat:.3f}:{site.lon:.3f}:{site.timezone}"
    res = await cached(
        key, WEATHER_TTL, lambda: fetch_open_meteo(site.lat, site.lon, site.timezone)
    )
    out: dict[str, Any] = {
        "weather": shape_weather(res["data"]) if res["data"] else None,
        "fetched_at": res["fetched_at"],
        "stale": res["stale"],
        "error": res["error"],
        "sun": sun_info(site),
        "alerts": [],
    }
    if alerts_enabled and in_germany(site.lat, site.lon):
        a = await cached(
            f"alerts:{site.lat:.2f}:{site.lon:.2f}",
            WEATHER_TTL,
            lambda: fetch_alerts(site.lat, site.lon),
        )
        out["alerts"] = a["data"] or []
    return out
