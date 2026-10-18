"""Hintergrund-Jobs mit gemockten externen Diensten."""

import time
from datetime import UTC, datetime

import httpx
import respx
from sqlmodel import select

from app import jobs
from app.db import new_session
from app.models import DailyStats, ForecastPoint, Measurement, NewsItem, PricePoint, Site
from app.runtime import Runtime
from app.services.poller import Poller
from app.services.settings_store import get_value, update_section

RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>
<item><title>Neue Rekorde im Solarausbau</title><link>https://example.org/1</link></item>
</channel></rss>"""


def _site(db, **kw) -> Site:
    s = Site(name="Haus", lat=53.08, lon=8.8, arrays=[{"kwp": 5, "tilt": 30, "azimuth": 180}], **kw)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@respx.mock
async def test_job_forecast_prices_news(db, tmp_path, monkeypatch):
    _site(db)
    now_h = int(time.time()) // 3600 * 3600
    times = [now_h - 24 * 3600 + i * 3600 for i in range(8 * 24)]
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(
            200,
            json={
                "hourly": {
                    "time": times,
                    "global_tilted_irradiance": [500] * len(times),
                    "temperature_2m": [15] * len(times),
                    "cloud_cover": [20] * len(times),
                }
            },
        )
    )
    start = int(datetime.now(UTC).timestamp()) // 3600 * 3600
    respx.get("https://api.energy-charts.info/price").mock(
        return_value=httpx.Response(
            200, json={"unix_seconds": [start, start + 3600], "price": [80.0, 60.0]}
        )
    )
    respx.get("https://feeds.example/rss").mock(return_value=httpx.Response(200, text=RSS))
    feeds = tmp_path / "news_feeds.yaml"
    feeds.write_text("feeds:\n  - name: X\n    url: https://feeds.example/rss\n", encoding="utf-8")
    monkeypatch.setattr(jobs.get_settings(), "config_dir", tmp_path)

    await jobs.job_forecast()
    await jobs.job_prices(force=True)
    await jobs.job_news()
    with new_session() as s:
        assert s.exec(select(ForecastPoint)).first() is not None
        assert len(s.exec(select(PricePoint)).all()) == 2
        assert s.exec(select(NewsItem)).first().title == "Neue Rekorde im Solarausbau"
        assert get_value(s, "prices:last_fetch") is not None


async def test_daily_close_and_retention(db):
    site = _site(db)
    old = int(time.time()) - 900 * 86400
    db.add(Measurement(site_id=site.id, ts=old, pv_w=1))
    db.add(Measurement(site_id=site.id, ts=int(time.time()) - 60, dt_s=60, pv_w=1000, load_w=300))
    db.commit()
    await jobs.job_daily_close()
    jobs.job_retention()
    with new_session() as s:
        assert len(s.exec(select(Measurement)).all()) == 1
        assert s.exec(select(DailyStats)).first() is not None


@respx.mock
async def test_job_insights_sends_once(db):
    _site(db)
    update_section(
        db, "notifications", {"ntfy": {"enabled": True, "topic": "t"}, "events": {"offline": True}}
    )
    route = respx.post("https://ntfy.sh/").mock(return_value=httpx.Response(200))
    rt = Runtime(poller=Poller())
    rt.poller.live_payload = lambda: {  # type: ignore[method-assign]
        "sites": {},
        "devices": [
            {"id": 1, "site_id": 1, "name": "WR", "online": False, "last_seen": None, "error": "x"}
        ],
    }
    await jobs.job_insights(rt)
    await jobs.job_insights(rt)
    assert route.call_count == 1


async def test_ai_summary_disabled_is_noop(db):
    _site(db)
    await jobs.job_daily_summary()
    assert get_value(db, "ai:summary") is None


async def test_ai_summary_enabled(db, monkeypatch):
    _site(db)
    update_section(db, "ai", {"enabled": True, "api_key": "sk-test"})
    captured = {}

    async def fake(api_key, model, facts, lang):
        captured.update(api_key=api_key, model=model, facts=facts)
        return "Heute lief es gut."

    import app.services.ai_summary as ai

    monkeypatch.setattr(ai, "daily_summary", fake)
    await jobs.job_daily_summary()
    assert captured["api_key"] == "sk-test" and captured["model"] == "claude-opus-5-5"
    assert "today" in captured["facts"]
    with new_session() as s:
        assert get_value(s, "ai:summary")["text"] == "Heute lief es gut."


def test_scheduler_builds():
    sched = jobs.build_scheduler(Runtime(poller=Poller()))
    ids = {j.id for j in sched.get_jobs()}
    assert {"forecast", "prices", "news", "insights", "daily_close", "retention"} <= ids
