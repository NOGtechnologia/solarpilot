"""Shelly 3EM (Gen1, ``/status``) und Shelly Pro 3EM (Gen2+, RPC ``EM.GetStatus``).

Typischer Einsatz als Netzzähler (Rolle ``grid_meter``). Shelly misst Bezug positiv.
"""

from __future__ import annotations

from ._http import base_url, get_json, num
from ._httpadapter import HttpAdapter
from .base import AdapterError, Capabilities, ConfigField, LiveSnapshot, host_field
from .registry import register


@register
class ShellyEmAdapter(HttpAdapter):
    type_name = "shelly_3em"
    display_name = "Shelly 3EM / Pro 3EM (Zähler)"
    vendor = "Shelly"
    status = "beta"
    default_role = "grid_meter"
    capabilities = Capabilities(pv=False, grid=True)
    config_schema = [
        *host_field(),
        ConfigField(
            name="generation",
            label_de="Generation",
            label_en="Generation",
            type="select",
            options=["auto", "gen1", "gen2"],
            default="auto",
        ),
        ConfigField(
            name="invert_sign",
            label_de="Vorzeichen umkehren",
            label_en="Invert sign",
            type="bool",
            default=False,
        ),
    ]
    docs = "shelly_3em"

    async def _read_power(self) -> float | None:
        base = base_url(str(self.value("host")))
        gen = self.value("generation", "auto")
        if gen in ("auto", "gen2"):
            try:
                data = await get_json(self.client, base + "/rpc/EM.GetStatus", params={"id": 0})
                return num(data.get("total_act_power"))
            except AdapterError:
                if gen == "gen2":
                    raise
        data = await get_json(self.client, base + "/status")
        if "total_power" in data:
            return num(data["total_power"])
        return sum(num(e.get("power")) or 0.0 for e in data.get("emeters", []))

    async def read_live(self) -> LiveSnapshot:
        p = await self._read_power()
        if p is not None and self.value("invert_sign"):
            p = -p
        return LiveSnapshot(grid_power_w=p)
