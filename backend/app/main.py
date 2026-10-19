"""SolarPilot – FastAPI-App."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import select
from starlette.exceptions import HTTPException

from . import __version__
from .adapters.registry import load_all
from .api import auth_routes, data, settings_routes, sites
from .config import get_settings
from .db import create_db, init_engine, new_session
from .models import Site
from .runtime import Runtime
from .services.poller import Poller

log = logging.getLogger("solarpilot")


def bootstrap() -> None:
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    init_engine(settings.db_url)
    create_db()
    load_all()
    with new_session() as s:
        if settings.sites_file and settings.sites_file.exists():
            from .services.config_file import import_sites

            result = import_sites(s, settings.sites_file.read_text(encoding="utf-8"))
            log.info("Konfigurationsdatei geladen: %s", result)
        if settings.demo and s.exec(select(Site.id)).first() is None:
            from .services.demo_seed import create_demo_site

            create_demo_site(s)
            log.info("Demo-Anlage angelegt")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    bootstrap()
    rt = Runtime(poller=Poller(settings.poll_interval_s, settings.store_interval_s))
    rt.poller.listeners.append(rt.hub.broadcast)
    rt.poller.listeners.append(rt.mqtt.publish_live)
    app.state.rt = rt
    scheduler = None
    if settings.scheduler_enabled:
        from .jobs import build_scheduler, configure_mqtt

        configure_mqtt(rt)
        rt.poller.start()
        scheduler = build_scheduler(rt)
        scheduler.start()
    log.info("SolarPilot %s gestartet", __version__)
    yield
    if scheduler:
        scheduler.shutdown(wait=False)
    await rt.poller.stop()
    rt.mqtt.stop()


class SecurityHeadersMiddleware:
    """Reine ASGI-Middleware – robust bei abgebrochenen Verbindungen."""

    HEADERS = [
        (b"x-content-type-options", b"nosniff"),
        (b"referrer-policy", b"strict-origin-when-cross-origin"),
        (b"x-frame-options", b"SAMEORIGIN"),
    ]

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        is_api = scope["path"].startswith("/api/")

        async def wrapped(message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                present = {k.lower() for k, _ in headers}
                headers += [(k, v) for k, v in self.HEADERS if k not in present]
                if is_api and b"cache-control" not in present:
                    headers.append((b"cache-control", b"no-store"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, wrapped)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SolarPilot",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.add_middleware(SecurityHeadersMiddleware)

    for r in (auth_routes.router, sites.router, data.router, settings_routes.router):
        app.include_router(r)

    @app.exception_handler(404)
    async def not_found(request: Request, exc):
        if request.url.path.startswith("/api/") or not _static_dir():
            return JSONResponse({"detail": getattr(exc, "detail", "Not Found")}, status_code=404)
        page = _static_dir() / "404.html"  # type: ignore[operator]
        return FileResponse(page, status_code=404) if page.exists() else JSONResponse({}, 404)

    static = _static_dir()
    if static:
        app.mount("/", NextStaticFiles(directory=static, html=True), name="static")
    return app


def next_segment_path(path: str) -> str | None:
    """Next 16 fragt ``__next.seg.__PAGE__.txt`` an, exportiert ``__next.seg/__PAGE__.txt``."""
    head, _, name = path.replace("\\", "/").rpartition("/")
    if not (name.startswith("__next.") and name.endswith(".txt")):
        return None
    parts = name[: -len(".txt")].split(".")
    if len(parts) < 3:
        return None
    alt = f"__next.{parts[1]}/" + "/".join(parts[2:]) + ".txt"
    return f"{head}/{alt}" if head else alt


class NextStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        if path.replace("\\", "/").startswith("api/"):
            raise HTTPException(404, "Not Found")  # API-404 als JSON, nicht als HTML-Seite
        alt = next_segment_path(path)
        try:
            response = await super().get_response(path, scope)
        except HTTPException as exc:
            if alt is None or exc.status_code != 404:
                raise
            return await super().get_response(alt, scope)
        # mit html=True liefert StaticFiles bei 404 die 404.html statt einer Exception
        if alt is not None and response.status_code == 404:
            return await super().get_response(alt, scope)
        return response


def _static_dir() -> Path | None:
    d = get_settings().static_dir
    return d if d and d.exists() else None


app = create_app()
