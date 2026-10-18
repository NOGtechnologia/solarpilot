import time
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
import respx
from sqlmodel import select

from app.adapters.base import LiveSnapshot
from app.models import DailyStats, Device, ForecastPoint, Measurement, NewsItem, PricePoint, Site
from app.services import cache, notify
from app.services.aggregate import aggregate_all, aggregate_site, average_snapshots
from app.services.forecast import array_power, correction_factor, om_azimuth, site_forecast
from app.services.mqtt_out import discovery_messages, slugify, state_payload
from app.services.news import clean_teaser, parse_feed, refresh_news
from app.services.prices import cheapest_window, fetch_awattar, get_prices, refresh_prices
from app.services.settings_store import MASK, get_section, public_section, update_section
from app.services.stats import compute_day, energy_from_rows
from app.services.sun import clear_sky_ghi, solar_position, sunrise_sunset
from app.services.weather import in_germany, shape_weather, site_weather


# --- Sonne ---------------------------------------------------------------------
def test_sunrise_bremen_midsummer():
    rise, set_ = sunrise_sunset(date(2026, 6, 21), 53.08, 8.80)
    # Bremen: Aufgang ca. 04:58 MESZ (02:58 UTC), Untergang ca. 21:53 MESZ (19:53 UTC)
    assert abs((rise - datetime(2026, 6, 21, 2, 58, tzinfo=UTC)).total_seconds()) < 600
    assert abs((set_ - datetime(2026, 6, 21, 19, 53, tzinfo=UTC)).total_seconds()) < 600


def test_solar_position_noon_and_night():
    noon = solar_position(datetime(2026, 6, 21, 11, 25, tzinfo=UTC), 53.08, 8.8)
    assert 59 < noon.elevation_deg < 61.5
    assert 170 < noon.azimuth_deg < 190
    assert solar_position(datetime(2026, 6, 21, 23, 0, tzinfo=UTC), 53.08, 8.8).elevation_deg < 0
    assert clear_sky_ghi(-5) == 0 and clear_sky_ghi(60) > 800
    assert sunrise_sunset(date(2026, 6, 21), 78.2, 15.6) == (None, None)  # Polartag


# --- Aggregation ---------------------------------------------------------------
def test_aggregate_site_uses_single_grid_meter():
    inv = LiveSnapshot(pv_power_w=5000, grid_power_w=-999, battery_power_w=1000, battery_soc_pct=50)
    dtu = LiveSnapshot(pv_power_w=600)
    meter = LiveSnapshot(grid_power_w=-2000)
    s = aggregate_site([("hybrid", inv), ("inverter", dtu), ("grid_meter", meter)])
    assert s.pv_power_w == 5600 and s.grid_power_w == -2000
    assert s.load_power_w == 5600 - 2000 - 1000
    s2 = aggregate_site([("hybrid", inv)])
    assert s2.grid_power_w == -999
    s3 = aggregate_site([("inverter", dtu)])
    assert s3.load_power_w is None and s3.pv_power_w == 600


def test_aggregate_all_and_average():
    a = LiveSnapshot(pv_power_w=100, battery_soc_pct=40)
    b = LiveSnapshot(pv_power_w=300, battery_soc_pct=60)
    t = aggregate_all([a, b])
    assert t.pv_power_w == 400 and t.battery_soc_pct == 50
    avg = average_snapshots([a, b])
    assert avg.pv_power_w == 200 and avg.battery_soc_pct == 60


# --- Poller --------------------------------------------------------------------
async def test_poller_isolates_failures(db):
    from app.services.poller import Poller

    site = Site(name="A", lat=53.08, lon=8.8, arrays=[{"kwp": 10}], battery_kwh=10)
    db.add(site)
    db.commit()
    db.refresh(site)
    db.add(Device(site_id=site.id, name="Demo", type="demo", role="hybrid", config={}))
    db.add(
        Device(site_id=site.id, name="Kaputt", type="fronius_local", config={"host": "127.0.0.1:9"})
    )
    db.commit()
    p = Poller(poll_interval_s=10, store_interval_s=60, timeout_s=3)
    await p.reload()
    assert len(p.runtimes) == 2
    payload = await p.poll_once()
    devs = {d["name"]: d for d in payload["devices"]}
    assert devs["Demo"]["online"] is True
    assert devs["Kaputt"]["online"] is False and devs["Kaputt"]["error"]
    assert payload["sites"][str(site.id)]["pv_power_w"] is not None
    # Backoff: Kaputt wird nicht sofort erneut abgefragt
    rt = next(r for r in p.runtimes.values() if r.name == "Kaputt")
    assert rt.next_poll > time.time()
    n = p.store(time.time() + 60)
    assert n == 2  # Site + Demo-Gerät
    assert db.exec(select(Measurement)).all()
    assert db.exec(select(DailyStats)).first() is not None
    await p.stop()


# --- Statistik -----------------------------------------------------------------
def test_energy_from_rows():
    rows = [(3600, 1000, -2000, 600, 3600), (0, 500, 500, -500, 3600)]
    e = energy_from_rows(rows)
    assert e["pv_wh"] == 3600 and e["export_wh"] == 2000 and e["import_wh"] == 500
    assert e["charge_wh"] == 600 and e["discharge_wh"] == 500
    assert e["self_consumption_wh"] == 1600


def test_compute_day(db):
    site = Site(name="A", lat=53, lon=8.8)
    db.add(site)
    db.commit()
    db.refresh(site)
    day = date(2026, 6, 21)
    from app.services.timeutil import day_bounds

    start, _ = day_bounds(day, site.timezone)
    for h in range(24):
        db.add(
            Measurement(
                site_id=site.id,
                ts=start + (h + 1) * 3600,
                dt_s=3600,
                pv_w=2000 if 8 <= h < 18 else 0,
                load_w=500,
                grid_w=-1500 if 8 <= h < 18 else 500,
                battery_w=0,
            )
        )
    db.add(ForecastPoint(site_id=site.id, ts=start + 12 * 3600, power_w=25000))
    db.commit()
    s = compute_day(db, site, day)
    assert s.pv_wh == 20000 and s.load_wh == 12000 and s.export_wh == 15000
    assert s.forecast_wh == 25000
    assert s.savings_eur == pytest.approx(5 * 0.32 + 15 * 0.08)


# --- Einstellungen -------------------------------------------------------------
def test_settings_secrets(db):
    out = update_section(db, "mqtt", {"enabled": True, "host": "broker", "password": "pw1"})
    assert out["password"] == MASK
    assert get_section(db, "mqtt")["password"] == "pw1"
    raw = db.get(__import__("app.models", fromlist=["Setting"]).Setting, "mqtt").value
    assert raw["password"].startswith("enc:")
    update_section(db, "mqtt", {"password": MASK, "port": 1884})
    assert get_section(db, "mqtt")["password"] == "pw1"
    assert get_section(db, "mqtt")["port"] == 1884
    assert public_section(db, "ai")["api_key"] == ""


def test_settings_api(admin):
    r = admin.put("/api/settings/tariff", json={"buy_eur_kwh": 0.35})
    assert r.json()["buy_eur_kwh"] == 0.35
    assert admin.put("/api/settings/tariff", json={"evil": 1}).status_code == 422
    assert admin.put("/api/settings/tariff", json={"price_zone": "FR"}).status_code == 422
    assert admin.get("/api/settings/nope").status_code == 404
    assert set(admin.get("/api/settings").json()) >= {"tariff", "mqtt", "notifications"}
    r = admin.put("/api/settings/notifications", json={"telegram": {"bot_token": "123:abc"}})
    assert r.json()["telegram"]["bot_token"] == MASK


# --- Wetter / Prognose ---------------------------------------------------------
def _om_hourly(start: int, hours: int = 48):
    times = [start + i * 3600 for i in range(hours)]
    gti = [max(0, 800 * __import__("math").sin((i % 24 - 6) / 12 * 3.14159)) for i in range(hours)]
    return {
        "hourly": {
            "time": times,
            "global_tilted_irradiance": gti,
            "temperature_2m": [20] * hours,
            "cloud_cover": [10] * hours,
        }
    }


def test_array_power_and_azimuth():
    assert om_azimuth(180) == 0 and om_azimuth(90) == -90 and om_azimuth(270) == 90
    assert om_azimuth(0) == 180 or om_azimuth(0) == -180
    pts = array_power(
        {
            "hourly": {
                "time": [7200],
                "global_tilted_irradiance": [1000],
                "temperature_2m": [25],
                "cloud_cover": [0],
            }
        },
        10,
        14,
    )
    p, _ = pts[3600]
    # 10 kWp · 0,86 · (1 − 0,0037 · (55 − 25)) bei Zelltemperatur 55 °C
    assert p == pytest.approx(10000 * 0.86 * (1 - 0.0037 * 30))


@respx.mock
async def test_site_forecast_and_cache(db):
    now_h = int(time.time()) // 3600 * 3600
    route = respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(200, json=_om_hourly(now_h - 24 * 3600, 96))
    )
    site = Site(name="A", lat=53.08, lon=8.8, arrays=[{"kwp": 5, "tilt": 30, "azimuth": 180}])
    db.add(site)
    db.commit()
    db.refresh(site)
    r = await site_forecast(db, site)
    assert r["points"] and r["daily"]
    assert route.calls[0].request.url.params["azimuth"] == "0.0"
    await site_forecast(db, site)
    assert route.call_count == 1  # Cache
    assert db.exec(select(ForecastPoint)).first() is not None
    # Quelle fällt aus → letzter Stand
    cache.clear()
    route.mock(return_value=httpx.Response(503))
    r2 = await site_forecast(db, site)
    assert r2["stale"] is True and r2["points"]


async def test_forecast_without_arrays(db):
    site = Site(name="A", lat=1, lon=1)
    assert (await site_forecast(db, site))["error"] == "no_arrays"


def test_correction_factor(db):
    site = Site(name="A", lat=53, lon=8.8)
    db.add(site)
    db.commit()
    db.refresh(site)
    today = date.today()
    for i in range(1, 11):
        db.add(
            DailyStats(
                site_id=site.id,
                day=(today - timedelta(days=i)).isoformat(),
                pv_wh=9000,
                forecast_wh=10000,
            )
        )
    db.commit()
    c = correction_factor(db, site)
    assert c["factor"] == pytest.approx(0.9)
    assert c["accuracy_pct"] == pytest.approx(100.0)


@respx.mock
async def test_weather(db):
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(
            200,
            json={
                "current": {
                    "time": 1,
                    "temperature_2m": 18.2,
                    "weather_code": 2,
                    "cloud_cover": 40,
                    "wind_speed_10m": 9,
                    "is_day": 1,
                },
                "hourly": {
                    "time": [1, 2],
                    "temperature_2m": [18, 19],
                    "cloud_cover": [40, 50],
                    "weather_code": [2, 3],
                    "shortwave_radiation": [300, 400],
                    "precipitation_probability": [0, 10],
                    "is_day": [1, 1],
                },
                "daily": {
                    "time": [0],
                    "weather_code": [3],
                    "temperature_2m_max": [21],
                    "temperature_2m_min": [9],
                    "sunrise": [10],
                    "sunset": [20],
                    "shortwave_radiation_sum": [12.3],
                    "precipitation_probability_max": [30],
                    "cloud_cover_mean": [55],
                },
            },
        )
    )
    respx.get("https://api.brightsky.dev/alerts").mock(
        return_value=httpx.Response(
            200,
            json={
                "alerts": [
                    {"headline_de": "Amtliche WARNUNG vor STURMBÖEN", "severity": "moderate"}
                ]
            },
        )
    )
    site = Site(name="A", lat=53.08, lon=8.8)
    w = await site_weather(site)
    assert w["weather"]["current"]["temperature"] == 18.2
    assert w["weather"]["daily"][0]["temp_max"] == 21
    assert w["alerts"][0]["severity"] == "moderate"
    assert w["sun"]["sunrise"] is not None
    assert in_germany(53, 8.8) and not in_germany(48.2, 16.4)
    assert shape_weather({})["daily"] == []


# --- Preise --------------------------------------------------------------------
@respx.mock
async def test_prices_energy_charts_with_awattar_fallback(db):
    z = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    start = int(z.timestamp()) - 6 * 3600
    ts = [start + i * 900 for i in range(4 * 30)]
    prices = [100 - (i % 40) * 2 for i in range(len(ts))]
    respx.get("https://api.energy-charts.info/price").mock(
        return_value=httpx.Response(
            200, json={"unix_seconds": ts, "price": prices, "unit": "EUR / MWh"}
        )
    )
    n = await refresh_prices(db, "DE-LU")
    assert n == len(ts)
    p = get_prices(db, "DE-LU")
    assert p["points"][0]["duration_s"] == 900
    assert p["cheapest"]["ct_kwh"] <= p["most_expensive"]["ct_kwh"]
    # Fallback auf aWATTar
    respx.get("https://api.energy-charts.info/price").mock(return_value=httpx.Response(500))
    respx.get("https://api.awattar.de/v1/marketdata").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {
                        "start_timestamp": start * 1000,
                        "end_timestamp": (start + 3600) * 1000,
                        "marketprice": 55.5,
                        "unit": "Eur/MWh",
                    }
                ]
            },
        )
    )
    assert await refresh_prices(db, "DE-LU") == 1
    assert db.exec(select(PricePoint).where(PricePoint.ts == start)).first().eur_mwh == 55.5


async def test_awattar_zone_check():
    with pytest.raises(ValueError):
        await fetch_awattar("FR", date.today(), date.today())


def test_cheapest_window():
    pts = [
        {"ts": i * 3600, "duration_s": 3600, "ct_kwh": c}
        for i, c in enumerate([30, 20, 5, 6, 7, 25])
    ]
    w = cheapest_window(pts, 3)
    assert w["start"] == 2 * 3600 and w["end"] == 5 * 3600 and w["avg_ct_kwh"] == 6
    assert cheapest_window(pts, 10) is None


# --- News ----------------------------------------------------------------------
RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>pv</title>
<item><title>Rekord bei Solarausbau</title><link>https://example.org/a</link>
<guid>a1</guid><pubDate>Sat, 17 Oct 2026 08:00:00 GMT</pubDate>
<description>&lt;p&gt;Im September wurden &lt;b&gt;so viele&lt;/b&gt; Anlagen wie nie installiert.&lt;/p&gt;</description></item>
<item><title>Rekord bei Solarausbau!</title><link>https://example.org/dup</link><guid>a2</guid></item>
<item><title>Böser Link</title><link>javascript:alert(1)</link></item>
</channel></rss>"""


def test_parse_feed_and_teaser():
    items = parse_feed(RSS, "pv magazine")
    assert len(items) == 2
    assert items[0]["teaser"] == "Im September wurden so viele Anlagen wie nie installiert."
    assert clean_teaser("wort " * 100).endswith("…")
    assert len(clean_teaser("wort " * 100)) <= 222


@respx.mock
async def test_refresh_news_dedup(db):
    respx.get("https://example.org/feed").mock(return_value=httpx.Response(200, text=RSS))
    respx.get("https://broken.example/feed").mock(return_value=httpx.Response(500))
    n = await refresh_news(
        db,
        [{"url": "https://example.org/feed", "name": "X"}, {"url": "https://broken.example/feed"}],
    )
    assert n == 1  # Duplikat-Titel und javascript:-Link verworfen
    assert await refresh_news(db, [{"url": "https://example.org/feed", "name": "X"}]) == 0
    assert db.exec(select(NewsItem)).first().source == "X"


def test_news_api(admin):
    assert admin.get("/api/news").json()["items"] == []
    admin.put("/api/settings/news", json={"enabled": False})
    assert admin.get("/api/news").json()["enabled"] is False


# --- MQTT / Benachrichtigungen -------------------------------------------------
def test_mqtt_discovery():
    msgs = discovery_messages("1_wohnhaus", "Wohnhaus", "solarpilot", "homeassistant")
    topics = [t for t, _ in msgs]
    assert "homeassistant/sensor/solarpilot_1_wohnhaus_pv_power_w/config" in topics
    cfg = dict(msgs)["homeassistant/sensor/solarpilot_1_wohnhaus_battery_soc_pct/config"]
    assert cfg["device_class"] == "battery" and cfg["state_topic"] == "solarpilot/1_wohnhaus/state"
    assert slugify("Garage Balkonkraftwerk Ä") == "garage_balkonkraftwerk_ae"
    assert state_payload({"pv_power_w": 5, "timestamp_utc": "x"})["pv_power_w"] == 5


@respx.mock
async def test_notify_channels():
    ntfy = respx.post("https://ntfy.sh/").mock(return_value=httpx.Response(200))
    tg = respx.post(url__regex=r"https://api\.telegram\.org/bot.*/sendMessage").mock(
        return_value=httpx.Response(400)
    )
    cfg = {
        "ntfy": {"enabled": True, "url": "https://ntfy.sh", "topic": "solar"},
        "telegram": {"enabled": True, "bot_token": "123:secret", "chat_id": "9"},
        "email": {"enabled": False},
    }
    assert notify.enabled_channels(cfg) == ["ntfy", "telegram"]
    res = await notify.send(cfg, "Titel", "Text")
    assert res["ntfy"] == "ok" and res["telegram"] != "ok"
    assert "123:secret" not in res["telegram"]  # Bot-Token wird aus Fehlermeldungen entfernt
    assert (
        notify.redact("https://x/bot1:abc/send", {"bot_token": "1:abc"}) == "https://x/bot***/send"
    )
    import json

    sent = json.loads(ntfy.calls[0].request.content)
    assert sent == {"topic": "solar", "title": "Titel", "message": "Text", "tags": ["sunny"]}
    assert tg.called
    title, body = notify.render("insight.offline", {"device": "WR", "error": None}, "de")
    assert title == "Gerät offline" and "WR" in body


def test_notification_test_endpoint(admin):
    assert admin.post("/api/notifications/test", json={"channel": "fax"}).status_code == 422
