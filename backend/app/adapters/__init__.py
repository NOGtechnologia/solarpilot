"""Hersteller-Adapter. Jede Datei registriert sich mit ``@register``."""

from .base import (
    AdapterError,
    Capabilities,
    ConfigField,
    InverterAdapter,
    LiveSnapshot,
    SiteContext,
)
from .registry import all_adapters, get_adapter_class, register

__all__ = [
    "AdapterError",
    "Capabilities",
    "ConfigField",
    "InverterAdapter",
    "LiveSnapshot",
    "SiteContext",
    "all_adapters",
    "get_adapter_class",
    "register",
]
