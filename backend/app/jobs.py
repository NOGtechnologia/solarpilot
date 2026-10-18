"""Hintergrund-Jobs (APScheduler): Wetter/Prognose, Preise, News, Insights, Tagesabschluss."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlmodel import delete, select

from .config import get_settings
from .db import new_session
from .models import DailyStats, Measurement, Site
from .runtime import Runtime
from .services import notify
from .services.forecast import site_forecast
from .services.insights import build_insights, mark_clear_sky
from .services.news import load_feeds, refresh_news
from .services.prices import get_prices, has_tomorrow, refresh_prices
from .services.settings_store import get_section, get_value, set_value
from .services.stats import compute_day
from .services.timeutil import local_today

log = logging.getLogger(__name__)


async def job_forecast() -> None:
    with new_session() as s:
        for site in s.exec(select(Site)).all():
            try:
                await site_forecast(s, site)
            except Exception:  # noqa: BLE001
                log.exception("Prognose für %s fehlgeschlagen", site.name)


async def job_prices(force: bool = False) -> None:
    with new_session() as s:
        t = get_section(s, "tariff")
        zone = t["price_zone"]
        last = get_value(s, "prices:last_fetch", 0) or 0
        due = force or time.time() - last > 6 * 3600 or not has_tomorrow(s, zone)
        if not due:
            return
        try:
            n = await refresh_prices(s, zone, t.get("price_provider", "energy_charts"))
            set_value(s, "prices:last_fetch", int(time.time()))
            log.info("Strompreise aktualisiert (%s Werte)", n)
        except Exception as exc:  # noqa: BLE001
            log.warning("Strompreise nicht verfügbar: %s", exc)


async def job_news() -> None:
    with new_session() as s:
        cfg = get_section(s, "news")
        if not cfg.get("enabled", True):
            return
        feeds = cfg.get("feeds") or load_feeds(get_settings().config_dir / "news_feeds.yaml")
        n = await refresh_news(s, feeds)
        log.info("News aktualisiert (%s neu)", n)


async def job_insights(rt: Runtime) -> None:
    """Prüft Insights und verschickt Benachrichtigungen (jede Meldung nur einmal)."""
    with new_session() as s:
        cfg = get_section(s, "notifications")
        events = cfg.get("events", {})
        if not notify.enabled_channels(cfg):
            return
        sites = list(s.exec(select(Site)).all())
        t = get_section(s, "tariff")
        p = get_prices(s, t["price_zone"])
        items = build_insights(s, sites, rt.poller.live_payload(), p if p["points"] else None)
        lang = get_section(s, "general").get("language", "de")
        sent = set(get_value(s, "notify:sent", []) or [])
        wanted = {
            "insight.offline": events.get("offline"),
            "insight.underperformance": events.get("underperformance"),
            "insight.surplus": events.get("surplus"),
        }
        now = time.time()
        for it in items:
            if not wanted.get(it["key"]) or it["id"] in sent:
                continue
            if it["key"] == "insight.surplus" and not (it["start"] - 1800 <= now <= it["end"]):
                continue
            title, body = notify.render(it["key"], it["params"], lang)
            await notify.send(cfg, title, body)
            sent.add(it["id"])
        set_value(s, "notify:sent", sorted(sent)[-500:])


async def job_daily_close() -> None:
    """Abends: Tagesstatistik finalisieren, Prognose speichern, klaren Himmel markieren."""
    with new_session() as s:
        for site in s.exec(select(Site)).all():
            for offset in (1, 0):
                day = local_today(site.timezone) - timedelta(days=offset)
                stats = compute_day(s, site, day)
                clear = mark_clear_sky(s, site, day.isoformat())
                if clear is not None and stats.id is not None:
                    stats.clear_sky = clear
                    s.add(stats)
                    s.commit()


async def job_daily_summary() -> None:
    with new_session() as s:
        ai = get_section(s, "ai")
        if not ai.get("enabled") or not ai.get("api_key"):
            return
        from .services.ai_summary import daily_summary
        from .services.news import latest_news
        from .services.stats import today_kpis

        sites = list(s.exec(select(Site)).all())
        if not sites:
            return
        lang = get_section(s, "general").get("language", "de")
        facts = {
            "date": datetime.now(UTC).date().isoformat(),
            "today": today_kpis(s, sites),
            "headlines": [
                {"title": n["title"], "source": n["source"]} for n in latest_news(s, 8, lang)
            ],
        }
        text = await daily_summary(ai["api_key"], ai.get("model", "claude-opus-5-5"), facts, lang)
        if text:
            set_value(s, "ai:summary", {"text": text, "created_at": int(time.time())})
            cfg = get_section(s, "notifications")
            if cfg.get("events", {}).get("daily_summary"):
                title, body = notify.render("daily_summary", {"text": text}, lang)
                await notify.send(cfg, title, body)


def job_retention() -> None:
    days = get_settings().retention_days
    cutoff = int(time.time()) - days * 86400
    with new_session() as s:
        s.exec(delete(Measurement).where(Measurement.ts < cutoff))  # type: ignore[call-overload]
        # Gerätewerte nur 30 Tage, Site-Summen bis zur Aufbewahrungsgrenze
        s.exec(  # type: ignore[call-overload]
            delete(Measurement).where(
                Measurement.device_id.is_not(None),  # type: ignore[union-attr]
                Measurement.ts < int(time.time()) - 30 * 86400,
            )
        )
        s.exec(  # type: ignore[call-overload]
            delete(DailyStats).where(
                DailyStats.day < (datetime.now(UTC).date() - timedelta(days=days * 3)).isoformat()
            )
        )
        s.commit()


def configure_mqtt(rt: Runtime) -> None:
    with new_session() as s:
        cfg = get_section(s, "mqtt")
        sites = {site.id: site.name for site in s.exec(select(Site)).all()}
    rt.mqtt.configure(cfg, sites)  # type: ignore[arg-type]


def build_scheduler(rt: Runtime) -> AsyncIOScheduler:
    sched = AsyncIOScheduler(timezone="UTC")
    soon = datetime.now(UTC) + timedelta(seconds=5)
    sched.add_job(job_forecast, "interval", minutes=30, next_run_time=soon, id="forecast")
    sched.add_job(job_prices, "interval", minutes=60, next_run_time=soon, id="prices")
    sched.add_job(
        job_news, "interval", minutes=60, next_run_time=soon + timedelta(seconds=10), id="news"
    )
    sched.add_job(job_insights, "interval", minutes=5, args=[rt], id="insights")
    sched.add_job(job_daily_close, "cron", hour="*/3", minute=50, id="daily_close")
    sched.add_job(job_daily_summary, "cron", hour=19, minute=30, id="ai_summary")
    sched.add_job(job_retention, "cron", hour=3, minute=17, id="retention")
    sched.add_job(lambda: configure_mqtt(rt), "interval", minutes=10, id="mqtt_refresh")
    return sched
