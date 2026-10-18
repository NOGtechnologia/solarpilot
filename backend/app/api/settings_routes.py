"""Einstellungen (Tarif, Allgemein, Wetter, News, Benachrichtigungen, MQTT, KI)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.auth import require_admin, require_viewer
from app.db import get_session
from app.models import User
from app.runtime import Runtime, get_rt
from app.services import notify
from app.services.settings_store import DEFAULTS, public_section, update_section

router = APIRouter(prefix="/api", tags=["settings"])

PUBLIC_SECTIONS = {"general", "tariff"}


@router.get("/settings")
def all_settings(
    user: User | None = Depends(require_viewer), session: Session = Depends(get_session)
) -> dict[str, Any]:
    names = DEFAULTS if (user and user.is_admin) else PUBLIC_SECTIONS
    return {n: public_section(session, n) for n in names}


@router.get("/settings/{section}")
def get_settings_section(
    section: str, _: User = Depends(require_admin), session: Session = Depends(get_session)
) -> dict[str, Any]:
    if section not in DEFAULTS:
        raise HTTPException(404, "Unbekannter Abschnitt")
    return public_section(session, section)


@router.put("/settings/{section}")
def put_settings_section(
    section: str,
    body: dict[str, Any],
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
    rt: Runtime = Depends(get_rt),
) -> dict[str, Any]:
    if section not in DEFAULTS:
        raise HTTPException(404, "Unbekannter Abschnitt")
    unknown = set(body) - set(DEFAULTS[section])
    if unknown:
        raise HTTPException(422, f"Unbekannte Felder: {', '.join(sorted(unknown))}")
    if section == "tariff" and body.get("price_zone") not in (None, "DE-LU", "AT"):
        raise HTTPException(422, "price_zone muss DE-LU oder AT sein")
    out = update_section(session, section, body)
    if section == "mqtt":
        from app.jobs import configure_mqtt

        configure_mqtt(rt)
    return out


class TestNotification(BaseModel):
    channel: str


@router.post("/notifications/test")
async def test_notification(
    body: TestNotification,
    _: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    if body.channel not in notify.CHANNELS:
        raise HTTPException(422, "Unbekannter Kanal")
    from app.services.settings_store import get_section

    cfg = get_section(session, "notifications")
    return await notify.send(
        cfg, "SolarPilot", "Test-Benachrichtigung – alles funktioniert. ☀️", only=body.channel
    )
