from datetime import UTC, date, datetime, timedelta

import pytest

from app.models import DailyStats, ForecastPoint, Site
from app.services.insights import (
    battery_full_at,
    build_insights,
    ev_charging_plan,
    is_underperforming,
    surplus_window,
)
from app.services.report import monthly_report, report_pdf

TZ = "Europe/Berlin"


def day_curve(day: date, peak: float = 8000) -> list[tuple[int, float]]:
    """Stündliche PV-Prognose (Beginn der Stunde UTC) mit Maximum um 13 Uhr MESZ."""
    import math

    base = int(datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp())
    out = []
    for h in range(24):
        local_h = h + 2
        p = max(0.0, peak * math.sin((local_h - 6) / 14 * math.pi)) if 6 <= local_h <= 20 else 0.0
        out.append((base + h * 3600, p))
    return out


def test_surplus_window_finds_midday():
    d = date(2026, 6, 21)
    fc = day_curve(d)
    base = dict.fromkeys(range(24), 500.0)
    w = surplus_window(fc, base, TZ, 2000, fc[0][0], fc[-1][0] + 3600)
    start = datetime.fromtimestamp(w["start"], UTC).astimezone(__import__("zoneinfo").ZoneInfo(TZ))
    end = datetime.fromtimestamp(w["end"], UTC).astimezone(__import__("zoneinfo").ZoneInfo(TZ))
    assert 7 <= start.hour <= 10 and 16 <= end.hour <= 19
    assert w["energy_wh"] > 20000
    assert surplus_window(fc, base, TZ, 20000, fc[0][0], fc[-1][0]) is None


def test_battery_full_at():
    d = date(2026, 6, 21)
    fc = day_curve(d)
    base = dict.fromkeys(range(24), 500.0)
    t = battery_full_at(fc, base, TZ, 20, 10000, fc[0][0])
    assert t is not None
    hour = datetime.fromtimestamp(t, UTC).hour + 2
    assert 8 <= hour <= 13
    assert battery_full_at(fc, base, TZ, 20, 0, fc[0][0]) is None


def test_underperformance_rule():
    days = [
        {"day": f"2026-06-0{i}", "pv_wh": 20000, "forecast_wh": 40000, "clear_sky": True}
        for i in range(1, 4)
    ]
    r = is_underperforming(days)
    assert r == {"ratio_pct": 50, "days": 3}
    days[1]["clear_sky"] = False
    assert is_underperforming(days) is None
    ok = [
        {"day": f"2026-06-0{i}", "pv_wh": 39000, "forecast_wh": 40000, "clear_sky": True}
        for i in range(1, 4)
    ]
    assert is_underperforming(ok) is None
    assert is_underperforming(ok[:2]) is None


def test_ev_plan_prefers_solar_and_cheap_hours():
    hours = [
        {
            "ts": i * 3600,
            "surplus_w": 6000 if 10 <= i < 15 else 0,
            "grid_ct": 35 if i != 3 else 25,
            "feed_ct": 8,
        }
        for i in range(24)
    ]
    plan = ev_charging_plan(hours, 22000, 11000)
    assert plan["hours"] == [10 * 3600, 11 * 3600]
    assert plan["solar_share_pct"] == 55
    # sehr günstiger Nachtstrom schlägt teilweise Solarladung
    hours[3]["grid_ct"] = 10
    assert 3 * 3600 in ev_charging_plan(hours, 22000, 11000)["hours"]
    assert ev_charging_plan([], 1, 1) is None


def test_build_insights_integration(db):
    site = Site(name="Haus", lat=53.08, lon=8.8, battery_kwh=10, arrays=[{"kwp": 10}])
    db.add(site)
    db.commit()
    db.refresh(site)
    today = datetime.now(UTC).date()
    for d in (today, today + timedelta(days=1)):
        for ts, p in day_curve(d, 9000):
            db.add(ForecastPoint(site_id=site.id, ts=ts, power_w=p))
    for i in range(1, 4):
        db.add(
            DailyStats(
                site_id=site.id,
                day=(today - timedelta(days=i)).isoformat(),
                pv_wh=10000,
                forecast_wh=40000,
                clear_sky=True,
            )
        )
    db.commit()
    noon = int(datetime(today.year, today.month, today.day, 6, tzinfo=UTC).timestamp())
    live = {
        "sites": {str(site.id): {"battery_soc_pct": 30}},
        "devices": [
            {
                "id": 9,
                "site_id": site.id,
                "name": "WR",
                "online": False,
                "last_seen": noon - 3600,
                "error": "Timeout",
            }
        ],
    }
    prices = {
        "points": [
            {"ts": noon + i * 3600, "duration_s": 3600, "ct_kwh": 10 + i} for i in range(10)
        ],
        "cheapest_3h": {"start": noon, "end": noon + 3 * 3600, "avg_ct_kwh": 11},
        "current": {"ts": noon, "duration_s": 3600, "ct_kwh": 10},
    }
    items = build_insights(db, [site], live, prices, now=noon)
    keys = [i["key"] for i in items]
    assert keys[0] == "insight.underperformance"
    assert "insight.offline" in keys and "insight.surplus" in keys and "insight.cheap_power" in keys
    assert "insight.battery_full" in keys


def test_monthly_report(db):
    site = Site(name="Haus", lat=53.08, lon=8.8)
    db.add(site)
    db.commit()
    db.refresh(site)
    for d in range(1, 31):
        db.add(
            DailyStats(
                site_id=site.id,
                day=f"2026-06-{d:02d}",
                pv_wh=40000 + d * 100,
                load_wh=12000,
                import_wh=2000,
                export_wh=30000,
                self_consumption_wh=10000,
            )
        )
        db.add(
            DailyStats(
                site_id=site.id,
                day=f"2025-06-{d:02d}",
                pv_wh=36000,
                load_wh=12000,
                import_wh=2500,
                export_wh=26000,
                self_consumption_wh=10000,
            )
        )
    db.commit()
    r = monthly_report(db, [site], 2026, 6)
    assert r["total"]["pv_wh"] == pytest.approx(sum(40000 + d * 100 for d in range(1, 31)))
    assert r["best_day"]["day"] == "2026-06-30"
    assert r["change_pct"] > 0
    assert report_pdf(r, "de").startswith(b"%PDF")
    assert report_pdf(r, "en").startswith(b"%PDF")
