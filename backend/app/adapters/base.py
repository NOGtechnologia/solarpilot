"""Einheitliche Adapter-Schnittstelle für alle Hersteller.

Vorzeichen-Konvention im ``LiveSnapshot``:

* ``grid_power_w``    + = Netzbezug, − = Einspeisung
* ``battery_power_w`` + = Batterie lädt, − = Batterie entlädt
* ``load_power_w``    Hausverbrauch (immer ≥ 0)

Energiebilanz: ``load = pv + grid − battery``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, Field


class StringValue(BaseModel):
    name: str
    power_w: float | None = None
    voltage_v: float | None = None
    current_a: float | None = None


class LiveSnapshot(BaseModel):
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))
    pv_power_w: float | None = None
    load_power_w: float | None = None
    grid_power_w: float | None = None
    battery_power_w: float | None = None
    battery_soc_pct: float | None = None
    energy_today_wh: float | None = None
    temperature_c: float | None = None
    strings: list[StringValue] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class Capabilities(BaseModel):
    pv: bool = True
    load: bool = False
    grid: bool = False
    battery: bool = False
    strings: bool = False
    history: bool = False


FieldType = Literal["text", "number", "password", "bool", "select", "textarea"]


class ConfigField(BaseModel):
    name: str
    label_de: str
    label_en: str
    type: FieldType = "text"
    required: bool = False
    default: Any = None
    secret: bool = False
    options: list[str] | None = None
    help_de: str | None = None
    help_en: str | None = None


@dataclass
class SiteContext:
    """Informationen über die Site, die manche Adapter brauchen (z. B. der Simulator)."""

    lat: float = 52.52
    lon: float = 13.40
    timezone: str = "Europe/Berlin"
    kwp: float = 10.0
    battery_kwh: float | None = None


class AdapterError(Exception):
    """Lesbarer Fehler für die Oberfläche (z. B. „Verbindung abgelehnt“)."""


def host_field(default_port: int | None = None) -> list[ConfigField]:
    fields = [
        ConfigField(
            name="host",
            label_de="Host / IP-Adresse",
            label_en="Host / IP address",
            required=True,
            help_de="z. B. 192.168.1.50",
            help_en="e.g. 192.168.1.50",
        )
    ]
    if default_port is not None:
        fields.append(
            ConfigField(
                name="port", label_de="Port", label_en="Port", type="number", default=default_port
            )
        )
    return fields


class InverterAdapter(ABC):
    type_name: ClassVar[str]
    display_name: ClassVar[str]
    vendor: ClassVar[str]
    connection: ClassVar[Literal["local", "cloud", "simulated"]] = "local"
    status: ClassVar[Literal["stable", "beta"]] = "beta"
    default_role: ClassVar[str] = "inverter"
    #: Minimales Abfrageintervall (Cloud-APIs schützen, damit kein Konto gesperrt wird)
    min_poll_interval_s: ClassVar[float] = 0
    capabilities: ClassVar[Capabilities] = Capabilities()
    config_schema: ClassVar[list[ConfigField]] = []
    docs: ClassVar[str | None] = None

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        secrets: dict[str, Any] | None = None,
        site: SiteContext | None = None,
    ) -> None:
        self.config = {**self.defaults(), **(config or {})}
        self.secrets = secrets or {}
        self.site = site or SiteContext()
        self.connected = False

    @classmethod
    def defaults(cls) -> dict[str, Any]:
        return {
            f.name: f.default for f in cls.config_schema if f.default is not None and not f.secret
        }

    @classmethod
    def describe(cls) -> dict[str, Any]:
        return {
            "type": cls.type_name,
            "name": cls.display_name,
            "vendor": cls.vendor,
            "connection": cls.connection,
            "status": cls.status,
            "default_role": cls.default_role,
            "min_poll_interval_s": cls.min_poll_interval_s,
            "capabilities": cls.capabilities.model_dump(),
            "config_schema": [f.model_dump() for f in cls.config_schema],
            "docs": cls.docs,
        }

    def value(self, name: str, default: Any = None) -> Any:
        """Wert aus Konfiguration oder Secrets."""
        if name in self.secrets and self.secrets[name] not in (None, ""):
            return self.secrets[name]
        val = self.config.get(name, default)
        return default if val in (None, "") else val

    async def connect(self) -> None:
        self.connected = True

    @abstractmethod
    async def read_live(self) -> LiveSnapshot: ...

    async def read_history(self, start: datetime, end: datetime) -> list[LiveSnapshot]:
        return []

    async def close(self) -> None:
        self.connected = False

    async def test_connection(self) -> LiveSnapshot:
        try:
            await self.connect()
            return await self.read_live()
        finally:
            await self.close()
