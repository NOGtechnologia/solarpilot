"""Lesende Endpunkte: Live, Verlauf, Kennzahlen, Wetter, Prognose, Preise, News, Insights."""

from __future__ import annotations

from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from sqlmodel import Session

from app import __version__
from app.auth import require_admin, require_viewer, ws_allowed
from app.db import get_session, new_session
from app.models import User
from app.runtime import Runtime, get_rt
from app.services import forecast as fc
from app.services.insights import build_insights
from app.services.news import latest_news
from app.services.poller import session_sites
from app.services.prices import get_prices
from app.services.report import monthly_report, report_pdf
from app.services.settings_store import get_section, get_value
from app.services.stats import history, today_kpis
from app.services.timeutil import parse_day
from app.services.weather import site_weather

router = APIRouter(prefix="/api", tags=["data"])


@router.get("/health")
def health(rt: Runtime = Depends(get_rt)) -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "devices": len(rt.poller.runtimes),
        "online": sum(1 for r in rt.poller.runtimes.values() if r.online),
    }


def _sites(session: Session, site: str | None):
    sites = session_sites(session, site)
    if site not in (None, "", "all") and not sites:
        raise HTTPException(404, "Unbekannte Site")
    return sites


@router.get("/live")
def live(_: User | None = Depends(require_viewer), rt: Runtime = Depends(get_rt)) -> dict:
    return rt.poller.live_payload()


@router.get("/kpis")
def kpis(
    site: str = "all",
    _: User | None = Depends(require_viewer),
    session: Session = Depends(get_session),
) -> dict:
    sites = _sites(session, site)
    return {"site": site, "today": today_kpis(session, sites) if sites else None}


@router.get("/history")
def get_history(
    site: str = "all",
    range: str = Query("day", pattern="^(day|week|month|year)$"),  # noqa: A002
    day: str | None = Query(None, alias="date"),
    _: User | None = Depends(require_viewer),
    session: Session = Depends(get_session),
) -> dict:
    sites = _sites(session, site)
    if not sites:
        return {"range": range, "series": None, "energy": None}
    try:
        d = parse_day(day, sites[0].timezone)
    except ValueError as exc:
        raise HTTPException(422, "Ungültiges Datum") from exc
    return history(session, sites, range, d)


@router.get("/weather")
async def weather(
    site: str, _: User | None = Depends(require_viewer), session: Session = Depends(get_session)
) -> dict:
    sites = _sites(session, site if site != "all" else None)
    if not sites:
        raise HTTPException(404, "Keine Site")
    alerts = bool(get_section(session, "weather").get("brightsky_alerts"))
    return await site_weather(sites[0], alerts)


@router.get("/forecast")
async def forecast(
    site: str = "all",
    _: User | None = Depends(require_viewer),
    session: Session = Depends(get_session),
) -> dict:
    sites = _sites(session, site)
    results = []
    for s in sites:
        r = await fc.site_forecast(session, s)
        r["site_id"] = s.id
        r["accuracy_history"] = fc.accuracy_history(session, s)
        results.append(r)
    return {"sites": results}


@router.get("/prices")
def prices(
    zone: str | None = None,
    _: User | None = Depends(require_viewer),
    session: Session = Depends(get_session),
) -> dict:
    t = get_section(session, "tariff")
    z = zone or t["price_zone"]
    if z not in ("DE-LU", "AT"):
        raise HTTPException(422, "Zone muss DE-LU oder AT sein")
    out = get_prices(session, z, float(t["markup_eur_kwh"]) if t.get("dynamic") else 0.0)
    out["dynamic"] = bool(t.get("dynamic"))
    return out


@router.get("/news")
def news(
    limit: int = Query(20, ge=1, le=100),
    lang: str | None = None,
    _: User | None = Depends(require_viewer),
    session: Session = Depends(get_session),
) -> dict:
    if not get_section(session, "news").get("enabled", True):
        return {"items": [], "enabled": False}
    return {"items": latest_news(session, limit, lang), "enabled": True}


@router.get("/insights")
def insights(
    site: str = "all",
    _: User | None = Depends(require_viewer),
    session: Session = Depends(get_session),
    rt: Runtime = Depends(get_rt),
) -> dict:
    sites = _sites(session, site)
    t = get_section(session, "tariff")
    p = get_prices(session, t["price_zone"])
    items = build_insights(session, sites, rt.poller.live_payload(), p if p["points"] else None)
    summary = get_value(session, "ai:summary")
    return {"items": items, "summary": summary}


@router.get("/reports/monthly")
def report(
    site: str = "all",
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    _: User | None = Depends(require_viewer),
    session: Session = Depends(get_session),
) -> dict:
    sites = _sites(session, site)
    y, m = _month(month)
    return monthly_report(session, sites, y, m)


@router.get("/reports/monthly.pdf")
def report_pdf_endpoint(
    site: str = "all",
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    lang: str = Query("de", pattern="^(de|en)$"),
    _: User | None = Depends(require_viewer),
    session: Session = Depends(get_session),
) -> Response:
    sites = _sites(session, site)
    y, m = _month(month)
    pdf = report_pdf(monthly_report(session, sites, y, m), lang)
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="solarpilot-{y}-{m:02d}.pdf"'},
    )


def _month(month: str | None) -> tuple[int, int]:
    if not month:
        t = date.today()
        return t.year, t.month
    y, m = (int(x) for x in month.split("-"))
    if not 1 <= m <= 12:
        raise HTTPException(422, "Ungültiger Monat")
    return y, m


@router.get("/geocode")
async def geocode(
    q: str = Query(min_length=2, max_length=100),
    lang: str = Query("de", pattern="^(de|en)$"),
    _: User = Depends(require_admin),
) -> dict:
    from app.services.cache import cached
    from app.services.http import client

    async def fetch():
        async with client() as c:
            r = await c.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": q, "count": 6, "language": lang, "format": "json"},
            )
            r.raise_for_status()
            return r.json().get("results") or []

    res = await cached(f"geo:{lang}:{q.lower()}", 86400, fetch, persist=False)
    return {
        "results": [
            {
                "name": r.get("name"),
                "admin1": r.get("admin1"),
                "country": r.get("country"),
                "lat": r.get("latitude"),
                "lon": r.get("longitude"),
                "timezone": r.get("timezone"),
            }
            for r in res["data"] or []
        ],
        "error": res["error"],
    }


@router.websocket("/ws")
async def websocket(ws: WebSocket) -> None:
    with new_session() as session:
        allowed = ws_allowed(ws, session)
    if not allowed:
        await ws.close(code=4401)
        return
    await ws.accept()
    rt: Runtime = ws.app.state.rt
    rt.hub.clients.add(ws)
    try:
        await ws.send_json(rt.poller.live_payload())
        while True:
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        pass
    finally:
        rt.hub.clients.discard(ws)
