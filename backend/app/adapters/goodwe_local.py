"""GoodWe lokal per UDP über die Bibliothek ``goodwe`` (ET/EH/BT/BH/ES/DT-Serien).

Die Schlüssel der Laufzeitdaten unterscheiden sich je Serie; es werden die gängigen Namen
ausgewertet. ``active_power``/``meter_active_power`` + = Einspeisung, ``pbattery1`` + = Entladen.
"""

from __future__ import annotations

from typing import Any

from ._http import num
from .base import AdapterError, Capabilities, InverterAdapter, LiveSnapshot, host_field
from .registry import register


def map_runtime(data: dict[str, Any]) -> LiveSnapshot:
    pv = num(data.get("ppv"))
    grid_raw = num(data.get("meter_active_power", data.get("active_power")))
    batt_raw = num(data.get("pbattery1"))
    load = num(data.get("house_consumption", data.get("load_ptotal")))
    return LiveSnapshot(
        pv_power_w=max(pv or 0.0, 0.0),
        grid_power_w=-grid_raw if grid_raw is not None else None,
        battery_power_w=-batt_raw if batt_raw is not None else None,
        battery_soc_pct=num(data.get("battery_soc")),
        load_power_w=load,
        energy_today_wh=(num(data.get("e_day")) or 0) * 1000
        if data.get("e_day") is not None
        else None,
        temperature_c=num(data.get("temperature")),
    )


@register
class GoodWeLocalAdapter(InverterAdapter):
    type_name = "goodwe_local"
    display_name = "GoodWe (lokal, UDP)"
    vendor = "GoodWe"
    status = "beta"
    default_role = "hybrid"
    capabilities = Capabilities(pv=True, load=True, grid=True, battery=True)
    config_schema = [*host_field()]
    docs = "goodwe_local"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._inv = None

    async def connect(self) -> None:
        try:
            import goodwe
        except ImportError as exc:  # pragma: no cover
            raise AdapterError("Python-Paket 'goodwe' fehlt") from exc
        try:
            self._inv = await goodwe.connect(str(self.value("host")))
        except Exception as exc:  # noqa: BLE001 - Bibliothek wirft diverse Fehler
            raise AdapterError(f"GoodWe nicht erreichbar: {exc}") from exc
        self.connected = True

    async def read_live(self) -> LiveSnapshot:
        if self._inv is None:
            await self.connect()
        try:
            data = await self._inv.read_runtime_data()
        except Exception as exc:  # noqa: BLE001
            raise AdapterError(f"GoodWe-Lesefehler: {exc}") from exc
        return map_runtime(data)
