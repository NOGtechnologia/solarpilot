"""Adapter-Registry: findet Adapter-Klassen über ihren Typnamen."""

from __future__ import annotations

import importlib
import logging
import pkgutil

from .base import InverterAdapter

log = logging.getLogger(__name__)

_REGISTRY: dict[str, type[InverterAdapter]] = {}
_loaded = False


def register[T: type[InverterAdapter]](cls: T) -> T:
    if cls.type_name in _REGISTRY and _REGISTRY[cls.type_name] is not cls:
        raise ValueError(f"Adapter-Typ doppelt registriert: {cls.type_name}")
    _REGISTRY[cls.type_name] = cls
    return cls


def load_all() -> None:
    """Importiert alle Module in ``app.adapters`` (registriert sich per Dekorator)."""
    global _loaded
    if _loaded:
        return
    from app import adapters

    for mod in pkgutil.iter_modules(adapters.__path__):
        if mod.name.startswith("_") or mod.name in ("base", "registry"):
            continue
        try:
            importlib.import_module(f"app.adapters.{mod.name}")
        except Exception:  # pragma: no cover - fehlende optionale Abhängigkeit
            log.exception("Adapter %s konnte nicht geladen werden", mod.name)
    _loaded = True


def get_adapter_class(type_name: str) -> type[InverterAdapter]:
    load_all()
    try:
        return _REGISTRY[type_name]
    except KeyError as exc:
        raise KeyError(f"Unbekannter Adapter-Typ: {type_name}") from exc


def all_adapters() -> list[type[InverterAdapter]]:
    load_all()
    return sorted(
        _REGISTRY.values(), key=lambda c: (c.connection == "simulated", c.vendor, c.type_name)
    )
