"""OpenDTU (Hoymiles/TSUN) über die lokale REST-API ``/api/livedata/status``.

Ideal für Balkonkraftwerke. Lesen ist ohne Login möglich.
"""

from __future__ import annotations

from ._http import base_url, get_json, num
from ._httpadapter import HttpAdapter
from .base import Capabilities, LiveSnapshot, StringValue, host_field
from .registry import register


def _v(obj: dict | None, key: str) -> float | None:
    if not obj or key not in obj:
        return None
    item = obj[key]
    if isinstance(item, dict):
        val = num(item.get("v"))
        unit = str(item.get("u", ""))
        if val is not None and unit.lower() == "kwh":
            val *= 1000
        return val
    return num(item)


@register
class OpenDtuAdapter(HttpAdapter):
    type_name = "opendtu"
    display_name = "OpenDTU (Hoymiles / Balkonkraftwerk)"
    vendor = "Hoymiles"
    status = "beta"
    default_role = "inverter"
    capabilities = Capabilities(pv=True, strings=True)
    config_schema = [*host_field()]
    docs = "opendtu"

    async def read_live(self) -> LiveSnapshot:
        data = await get_json(
            self.client, base_url(str(self.value("host"))) + "/api/livedata/status"
        )
        total = data.get("total", {})
        strings: list[StringValue] = []
        for inv in data.get("inverters", []):
            for key, dc in (inv.get("DC") or {}).items():
                name = (dc.get("name") or {}).get("u") or f"{inv.get('name', 'WR')} DC{key}"
                strings.append(
                    StringValue(
                        name=str(name),
                        power_w=_v(dc, "Power"),
                        voltage_v=_v(dc, "Voltage"),
                        current_a=_v(dc, "Current"),
                    )
                )
        return LiveSnapshot(
            pv_power_w=max(_v(total, "Power") or 0.0, 0.0),
            energy_today_wh=_v(total, "YieldDay"),
            strings=strings,
            extra={"yield_total_wh": _v(total, "YieldTotal")},
        )
