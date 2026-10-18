"""Sites, Geräte, Adapter-Katalog, Verbindungstest, Demo und YAML-Konfiguration."""

from __future__ import annotations

import asyncio
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.adapters.base import AdapterError
from app.adapters.registry import all_adapters, get_adapter_class
from app.auth import require_admin, require_viewer
from app.crypto import decrypt_json, encrypt_json
from app.db import get_session
from app.models import DEVICE_ROLES, DailyStats, Device, ForecastPoint, Measurement, Site, User
from app.runtime import Runtime, get_rt
from app.services.config_file import export_sites, import_sites
from app.services.demo_seed import create_demo_site
from app.services.settings_store import MASK

router = APIRouter(prefix="/api", tags=["sites"])


class ArrayIn(BaseModel):
    kwp: float = Field(gt=0, le=10000)
    tilt: float = Field(default=30, ge=0, le=90)
    azimuth: float = Field(default=180, ge=0, lt=360)
    losses_pct: float = Field(default=14, ge=0, le=60)
    name: str | None = None


class SiteIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    timezone: str = "Europe/Berlin"
    arrays: list[ArrayIn] = []
    battery_kwh: float | None = Field(default=None, ge=0)
    buy_eur_kwh: float | None = Field(default=None, ge=0)
    feed_in_eur_kwh: float | None = Field(default=None, ge=0)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class DeviceIn(BaseModel):
    site_id: int
    name: str = Field(min_length=1, max_length=80)
    type: str
    role: str | None = None
    config: dict[str, Any] = {}
    secrets: dict[str, Any] = {}
    enabled: bool = True


class TestIn(BaseModel):
    config: dict[str, Any] = {}
    secrets: dict[str, Any] = {}
    device_id: int | None = None
    lat: float = 52.5
    lon: float = 13.4
    timezone: str = "Europe/Berlin"


def site_out(site: Site, devices: list[Device]) -> dict[str, Any]:
    return {
        **site.model_dump(),
        "kwp": round(sum(float(a.get("kwp") or 0) for a in site.arrays or []), 2),
        "devices": [device_out(d) for d in devices],
    }


def device_out(d: Device) -> dict[str, Any]:
    try:
        cls = get_adapter_class(d.type)
        secret_fields = [f.name for f in cls.config_schema if f.secret]
    except KeyError:
        secret_fields = []
    stored = decrypt_json(d.secrets_enc) if d.secrets_enc else {}
    return {
        "id": d.id,
        "site_id": d.site_id,
        "name": d.name,
        "type": d.type,
        "role": d.role,
        "config": d.config,
        "enabled": d.enabled,
        "last_seen": d.last_seen,
        "last_error": d.last_error,
        "secrets": {k: (MASK if stored.get(k) else "") for k in secret_fields},
    }


def _split_config(type_name: str, config: dict, secrets: dict) -> tuple[dict, dict]:
    cls = get_adapter_class(type_name)
    secret_names = {f.name for f in cls.config_schema if f.secret}
    allowed = {f.name for f in cls.config_schema}
    cfg = {k: v for k, v in config.items() if k in allowed and k not in secret_names}
    sec = {k: v for k, v in {**config, **secrets}.items() if k in secret_names}
    missing = [
        f.name
        for f in cls.config_schema
        if f.required and not f.secret and cfg.get(f.name) in (None, "")
    ]
    if missing:
        raise HTTPException(422, f"Pflichtfelder fehlen: {', '.join(missing)}")
    return cfg, sec


def _check_tz(name: str) -> None:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise HTTPException(422, f"Unbekannte Zeitzone: {name}") from exc


def _check_grid_meter(session: Session, site_id: int, role: str, device_id: int | None) -> None:
    if role != "grid_meter":
        return
    q = select(Device).where(Device.site_id == site_id, Device.role == "grid_meter")
    for d in session.exec(q).all():
        if d.id != device_id:
            raise HTTPException(409, f"Site hat bereits einen Netzzähler ({d.name})")


# --- Sites --------------------------------------------------------------------


@router.get("/sites")
def list_sites(_: User | None = Depends(require_viewer), session: Session = Depends(get_session)):
    sites = session.exec(select(Site).order_by(Site.id)).all()
    devices = session.exec(select(Device)).all()
    return [site_out(s, [d for d in devices if d.site_id == s.id]) for s in sites]


@router.post("/sites")
def create_site(
    body: SiteIn,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
    rt: Runtime = Depends(get_rt),
):
    _check_tz(body.timezone)
    site = Site(**body.model_dump(exclude={"arrays"}), arrays=[a.model_dump() for a in body.arrays])
    session.add(site)
    session.commit()
    session.refresh(site)
    rt.poller.request_reload()
    return site_out(site, [])


@router.put("/sites/{site_id}")
def update_site(
    site_id: int,
    body: SiteIn,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
    rt: Runtime = Depends(get_rt),
):
    site = session.get(Site, site_id)
    if not site:
        raise HTTPException(404, "Unbekannte Site")
    _check_tz(body.timezone)
    for k, v in body.model_dump(exclude={"arrays"}).items():
        setattr(site, k, v)
    site.arrays = [a.model_dump() for a in body.arrays]
    session.add(site)
    session.commit()
    session.refresh(site)
    rt.poller.request_reload()
    devices = session.exec(select(Device).where(Device.site_id == site_id)).all()
    return site_out(site, list(devices))


@router.delete("/sites/{site_id}")
def delete_site(
    site_id: int,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
    rt: Runtime = Depends(get_rt),
):
    site = session.get(Site, site_id)
    if not site:
        raise HTTPException(404, "Unbekannte Site")
    for model in (Measurement, DailyStats, ForecastPoint):
        for row in session.exec(select(model).where(model.site_id == site_id)).all():
            session.delete(row)
    for d in session.exec(select(Device).where(Device.site_id == site_id)).all():
        session.delete(d)
    session.commit()
    session.delete(site)
    session.commit()
    rt.poller.request_reload()
    return {"ok": True}


# --- Geräte -------------------------------------------------------------------


@router.post("/devices")
def create_device(
    body: DeviceIn,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
    rt: Runtime = Depends(get_rt),
):
    if not session.get(Site, body.site_id):
        raise HTTPException(404, "Unbekannte Site")
    try:
        cls = get_adapter_class(body.type)
    except KeyError as exc:
        raise HTTPException(422, str(exc)) from exc
    role = body.role or cls.default_role
    if role not in DEVICE_ROLES:
        raise HTTPException(422, f"Unbekannte Rolle {role}")
    _check_grid_meter(session, body.site_id, role, None)
    cfg, sec = _split_config(body.type, body.config, body.secrets)
    sec = {k: v for k, v in sec.items() if v and v != MASK}
    dev = Device(
        site_id=body.site_id,
        name=body.name,
        type=body.type,
        role=role,
        config=cfg,
        secrets_enc=encrypt_json(sec),
        enabled=body.enabled,
    )
    session.add(dev)
    session.commit()
    session.refresh(dev)
    rt.poller.request_reload()
    return device_out(dev)


@router.put("/devices/{device_id}")
def update_device(
    device_id: int,
    body: DeviceIn,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
    rt: Runtime = Depends(get_rt),
):
    dev = session.get(Device, device_id)
    if not dev:
        raise HTTPException(404, "Unbekanntes Gerät")
    role = body.role or dev.role
    if role not in DEVICE_ROLES:
        raise HTTPException(422, f"Unbekannte Rolle {role}")
    _check_grid_meter(session, body.site_id, role, device_id)
    cfg, sec = _split_config(body.type, body.config, body.secrets)
    old = decrypt_json(dev.secrets_enc)
    merged = {k: (old.get(k) if v == MASK else v) for k, v in sec.items()}
    merged = {k: v for k, v in {**old, **merged}.items() if v}
    dev.site_id, dev.name, dev.type, dev.role = body.site_id, body.name, body.type, role
    dev.config, dev.enabled = cfg, body.enabled
    dev.secrets_enc = encrypt_json(merged)
    session.add(dev)
    session.commit()
    session.refresh(dev)
    rt.poller.request_reload()
    return device_out(dev)


@router.delete("/devices/{device_id}")
def delete_device(
    device_id: int,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
    rt: Runtime = Depends(get_rt),
):
    dev = session.get(Device, device_id)
    if not dev:
        raise HTTPException(404, "Unbekanntes Gerät")
    for row in session.exec(select(Measurement).where(Measurement.device_id == device_id)).all():
        session.delete(row)
    session.delete(dev)
    session.commit()
    rt.poller.request_reload()
    return {"ok": True}


# --- Adapter ------------------------------------------------------------------


@router.get("/adapters")
def list_adapters(_: User | None = Depends(require_viewer)):
    return [cls.describe() for cls in all_adapters()]


@router.post("/adapters/{type_name}/test")
async def test_adapter(
    type_name: str,
    body: TestIn,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    try:
        cls = get_adapter_class(type_name)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    secrets = dict(body.secrets)
    if body.device_id:
        dev = session.get(Device, body.device_id)
        if dev:
            stored = decrypt_json(dev.secrets_enc)
            secrets = {k: (stored.get(k) if v == MASK else v) for k, v in secrets.items()}
    secrets = {k: v for k, v in secrets.items() if v and v != MASK}
    from app.adapters.base import SiteContext

    adapter = cls(
        config=body.config,
        secrets=secrets,
        site=SiteContext(lat=body.lat, lon=body.lon, timezone=body.timezone),
    )
    try:
        snap = await asyncio.wait_for(adapter.test_connection(), 15)
    except AdapterError as exc:
        return {"ok": False, "error": str(exc)}
    except TimeoutError:
        return {"ok": False, "error": "Zeitüberschreitung (15 s)"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"ok": True, "snapshot": snap.model_dump(mode="json")}


# --- Demo und YAML ------------------------------------------------------------


class DemoIn(BaseModel):
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = None


@router.post("/demo")
async def start_demo(
    body: DemoIn | None = None,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
    rt: Runtime = Depends(get_rt),
):
    existing = session.exec(select(Site).where(Site.source == "demo")).first()
    if existing:
        return {"site_id": existing.id, "created": False}
    kwargs = {}
    if body and body.lat is not None and body.lon is not None:
        kwargs = {"lat": body.lat, "lon": body.lon}
        if body.timezone:
            _check_tz(body.timezone)
            kwargs["timezone"] = body.timezone
    site = await asyncio.to_thread(_create_demo, kwargs)
    rt.poller.request_reload()
    return {"site_id": site, "created": True}


def _create_demo(kwargs: dict) -> int:
    from app.db import new_session

    with new_session() as s:
        return create_demo_site(s, **kwargs).id  # type: ignore[return-value]


@router.get("/config/export")
def config_export(_: User = Depends(require_admin), session: Session = Depends(get_session)):
    return Response(
        export_sites(session),
        media_type="application/x-yaml",
        headers={"Content-Disposition": 'attachment; filename="solarpilot-sites.yaml"'},
    )


class ImportIn(BaseModel):
    yaml: str = Field(max_length=200_000)


@router.post("/config/import")
def config_import(
    body: ImportIn,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
    rt: Runtime = Depends(get_rt),
):
    try:
        result = import_sites(session, body.yaml, source="ui")
    except (ValueError, KeyError) as exc:
        raise HTTPException(422, str(exc)) from exc
    rt.poller.request_reload()
    return result
