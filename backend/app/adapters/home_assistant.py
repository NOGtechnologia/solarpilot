"""Home Assistant REST-API – liest beliebige Sensoren als Messwerte (fängt „alles andere“ ab)."""

from __future__ import annotations

import re

from ._http import base_url, get_json, num
from ._httpadapter import HttpAdapter
from .base import AdapterError, Capabilities, ConfigField, LiveSnapshot
from .registry import register

ENTITY_FIELDS = {
    "pv_entity": "pv_power_w",
    "load_entity": "load_power_w",
    "grid_entity": "grid_power_w",
    "battery_entity": "battery_power_w",
    "soc_entity": "battery_soc_pct",
    "energy_today_entity": "energy_today_wh",
}

ENTITY_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")

UNIT_FACTORS = {"kw": 1000.0, "w": 1.0, "kwh": 1000.0, "wh": 1.0, "%": 1.0}


@register
class HomeAssistantAdapter(HttpAdapter):
    type_name = "home_assistant"
    display_name = "Home Assistant (Sensoren)"
    vendor = "Home Assistant"
    status = "beta"
    default_role = "hybrid"
    capabilities = Capabilities(pv=True, load=True, grid=True, battery=True)
    config_schema = [
        ConfigField(
            name="url",
            label_de="Home-Assistant-URL",
            label_en="Home Assistant URL",
            required=True,
            default="http://homeassistant.local:8123",
        ),
        ConfigField(
            name="token",
            label_de="Langlebiges Zugriffstoken",
            label_en="Long-lived access token",
            type="password",
            required=True,
            secret=True,
        ),
        ConfigField(name="pv_entity", label_de="PV-Leistung (Entity)", label_en="PV power entity"),
        ConfigField(name="load_entity", label_de="Verbrauch (Entity)", label_en="Load entity"),
        ConfigField(
            name="grid_entity",
            label_de="Netz (+Bezug/−Einspeisung)",
            label_en="Grid (+import/−export)",
        ),
        ConfigField(
            name="battery_entity",
            label_de="Batterie (+Laden/−Entladen)",
            label_en="Battery (+charge/−discharge)",
        ),
        ConfigField(name="soc_entity", label_de="Batterie-SoC (Entity)", label_en="Battery SoC"),
        ConfigField(
            name="energy_today_entity",
            label_de="Ertrag heute (Entity)",
            label_en="Energy today entity",
        ),
    ]
    docs = "home_assistant"

    async def read_live(self) -> LiveSnapshot:
        base = base_url(str(self.value("url")))
        headers = {"Authorization": f"Bearer {self.value('token', '')}"}
        values: dict[str, float | None] = {}
        configured = [(k, f) for k, f in ENTITY_FIELDS.items() if self.value(k)]
        if not configured:
            raise AdapterError("Mindestens eine Entity angeben")
        for key, field in configured:
            if not ENTITY_RE.match(str(self.value(key))):
                raise AdapterError(f"Ungültige Entity-ID: {self.value(key)}")
            data = await get_json(
                self.client, f"{base}/api/states/{self.value(key)}", headers=headers
            )
            val = num(data.get("state"))
            unit = str((data.get("attributes") or {}).get("unit_of_measurement", "")).lower()
            if val is not None:
                val *= UNIT_FACTORS.get(unit, 1.0)
            values[field] = val
        return LiveSnapshot(**values)
