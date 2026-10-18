"""Import/Export der Anlagen-Konfiguration als YAML (siehe config/sites.example.yaml)."""

from __future__ import annotations

import os
import re
from typing import Any

import yaml
from sqlmodel import Session, select

from app.adapters.registry import get_adapter_class
from app.crypto import encrypt_json
from app.models import Device, Site

ENV_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")
RESERVED = {"type", "name", "role", "enabled", "secrets"}


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        return ENV_RE.sub(lambda m: os.environ.get(m.group(1), ""), value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def import_sites(session: Session, text: str, source: str = "file") -> dict[str, int]:
    data = _expand_env(yaml.safe_load(text) or {})
    created = updated = devices = 0
    for s in data.get("sites", []):
        loc = s.get("location") or {}
        if "lat" not in loc or "lon" not in loc or not s.get("name"):
            raise ValueError(f"Site ohne name/location: {s}")
        site = session.exec(select(Site).where(Site.name == s["name"])).first()
        if site is None:
            site = Site(name=s["name"], lat=float(loc["lat"]), lon=float(loc["lon"]), source=source)
            created += 1
        else:
            updated += 1
        site.lat, site.lon = float(loc["lat"]), float(loc["lon"])
        site.timezone = s.get("timezone", site.timezone or "Europe/Berlin")
        site.arrays = [
            {
                "kwp": float(a["kwp"]),
                "tilt": float(a.get("tilt", 30)),
                "azimuth": float(a.get("azimuth", 180)),
                "losses_pct": float(a.get("losses_pct", 14)),
            }
            for a in s.get("arrays", [])
        ]
        tariff = s.get("tariff") or {}
        site.buy_eur_kwh = tariff.get("buy_eur_kwh")
        site.feed_in_eur_kwh = tariff.get("feed_in_eur_kwh")
        site.battery_kwh = s.get("battery_kwh")
        session.add(site)
        session.commit()
        session.refresh(site)
        existing = {
            d.name: d for d in session.exec(select(Device).where(Device.site_id == site.id))
        }
        grid_meters = 0
        for i, d in enumerate(s.get("devices", [])):
            cls = get_adapter_class(d["type"])
            name = d.get("name") or f"{cls.display_name} {i + 1}"
            role = d.get("role") or cls.default_role
            if role == "grid_meter":
                grid_meters += 1
                if grid_meters > 1:
                    raise ValueError(f"{site.name}: nur ein Gerät mit Rolle grid_meter erlaubt")
            secret_names = {f.name for f in cls.config_schema if f.secret}
            cfg = {k: v for k, v in d.items() if k not in RESERVED and k not in secret_names}
            secrets = dict(d.get("secrets") or {})
            secrets.update({k: v for k, v in d.items() if k in secret_names})
            dev = existing.get(name) or Device(site_id=site.id, name=name, type=d["type"])  # type: ignore[arg-type]
            dev.type, dev.role, dev.config = d["type"], role, cfg
            dev.enabled = bool(d.get("enabled", True))
            if secrets:
                dev.secrets_enc = encrypt_json(secrets)
            session.add(dev)
            devices += 1
        session.commit()
    return {"created": created, "updated": updated, "devices": devices}


def export_sites(session: Session) -> str:
    out = []
    for site in session.exec(select(Site).order_by(Site.id)).all():
        entry: dict[str, Any] = {
            "name": site.name,
            "location": {"lat": site.lat, "lon": site.lon},
            "timezone": site.timezone,
            "arrays": site.arrays,
        }
        if site.battery_kwh:
            entry["battery_kwh"] = site.battery_kwh
        if site.buy_eur_kwh is not None or site.feed_in_eur_kwh is not None:
            entry["tariff"] = {
                "buy_eur_kwh": site.buy_eur_kwh,
                "feed_in_eur_kwh": site.feed_in_eur_kwh,
            }
        entry["devices"] = [
            {"type": d.type, "name": d.name, "role": d.role, **d.config}
            for d in session.exec(select(Device).where(Device.site_id == site.id)).all()
        ]
        out.append(entry)
    header = "# SolarPilot-Konfiguration (Zugangsdaten werden nicht exportiert)\n"
    return header + yaml.safe_dump({"sites": out}, allow_unicode=True, sort_keys=False)
