"""Einstellungen in der DB (Abschnitte als JSON). Geheime Felder werden verschlüsselt."""

from __future__ import annotations

import copy
from typing import Any

from sqlmodel import Session

from app.crypto import decrypt_str, encrypt_str
from app.models import Setting, now_ts

MASK = "__unchanged__"
ENC_PREFIX = "enc:"

DEFAULTS: dict[str, dict[str, Any]] = {
    "tariff": {
        "buy_eur_kwh": 0.32,
        "feed_in_eur_kwh": 0.08,
        "currency": "EUR",
        "dynamic": False,
        "price_zone": "DE-LU",
        "price_provider": "energy_charts",
        "markup_eur_kwh": 0.18,
    },
    "general": {
        "language": "de",
        "co2_kg_per_kwh": 0.38,
        "public_dashboard": False,
        "base_load_w": 400,
        "big_consumer_w": 2000,
        "ev_charge_kwh": 20,
        "ev_charge_power_w": 11000,
    },
    "weather": {
        "brightsky_alerts": True,
        "forecast_solar": False,
        "forecast_solar_key": "",
    },
    "news": {"enabled": True, "feeds": [], "max_items": 30},
    "notifications": {
        "ntfy": {"enabled": False, "url": "https://ntfy.sh", "topic": "", "token": ""},
        "telegram": {"enabled": False, "bot_token": "", "chat_id": ""},
        "email": {
            "enabled": False,
            "host": "",
            "port": 587,
            "username": "",
            "password": "",
            "from_addr": "",
            "to_addr": "",
            "starttls": True,
        },
        "events": {
            "offline": True,
            "underperformance": True,
            "surplus": False,
            "daily_summary": False,
        },
    },
    "mqtt": {
        "enabled": False,
        "host": "",
        "port": 1883,
        "username": "",
        "password": "",
        "prefix": "solarpilot",
        "discovery": True,
        "discovery_prefix": "homeassistant",
    },
    "ai": {"enabled": False, "api_key": "", "model": "claude-opus-5-5"},
}

SECRET_FIELDS: dict[str, set[tuple[str, ...]]] = {
    "weather": {("forecast_solar_key",)},
    "notifications": {
        ("ntfy", "token"),
        ("telegram", "bot_token"),
        ("email", "password"),
    },
    "mqtt": {("password",)},
    "ai": {("api_key",)},
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _get_path(d: dict, path: tuple[str, ...]) -> Any:
    for p in path:
        if not isinstance(d, dict):
            return None
        d = d.get(p)  # type: ignore[assignment]
    return d


def _set_path(d: dict, path: tuple[str, ...], value: Any) -> None:
    for p in path[:-1]:
        d = d.setdefault(p, {})
    d[path[-1]] = value


def get_section(session: Session, name: str) -> dict[str, Any]:
    """Abschnitt inkl. entschlüsselter Secrets (nur intern verwenden)."""
    if name not in DEFAULTS:
        raise KeyError(name)
    row = session.get(Setting, name)
    data = _deep_merge(DEFAULTS[name], row.value if row and isinstance(row.value, dict) else {})
    for path in SECRET_FIELDS.get(name, set()):
        v = _get_path(data, path)
        if isinstance(v, str) and v.startswith(ENC_PREFIX):
            try:
                _set_path(data, path, decrypt_str(v[len(ENC_PREFIX) :]))
            except ValueError:
                _set_path(data, path, "")
    return data


def public_section(session: Session, name: str) -> dict[str, Any]:
    """Abschnitt für die API: Secrets werden maskiert."""
    data = get_section(session, name)
    for path in SECRET_FIELDS.get(name, set()):
        v = _get_path(data, path)
        _set_path(data, path, MASK if v else "")
    return data


def update_section(session: Session, name: str, values: dict[str, Any]) -> dict[str, Any]:
    current = get_section(session, name)
    merged = _deep_merge(current, values)
    for path in SECRET_FIELDS.get(name, set()):
        if _get_path(values, path) == MASK:
            _set_path(merged, path, _get_path(current, path))
    stored = copy.deepcopy(merged)
    for path in SECRET_FIELDS.get(name, set()):
        v = _get_path(stored, path)
        if v:
            _set_path(stored, path, ENC_PREFIX + encrypt_str(str(v)))
    row = session.get(Setting, name) or Setting(key=name)
    row.value = stored
    row.updated_at = now_ts()
    session.add(row)
    session.commit()
    return public_section(session, name)


def get_value(session: Session, key: str, default: Any = None) -> Any:
    row = session.get(Setting, key)
    return row.value if row else default


def set_value(session: Session, key: str, value: Any) -> None:
    row = session.get(Setting, key) or Setting(key=key)
    row.value = value
    row.updated_at = now_ts()
    session.add(row)
    session.commit()
