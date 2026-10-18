"""Fronius Solar API v1 (lokal, HTTP/JSON, ohne Login).

Doku: Fronius „Solar API V1“ – ``GetPowerFlowRealtimeData.fcgi``.
``P_Grid`` + = Bezug, ``P_Load`` negativ = Verbrauch, ``P_Akku`` + = Entladen.
"""

from __future__ import annotations

from ._http import base_url, get_json, num
from ._httpadapter import HttpAdapter
from .base import Capabilities, ConfigField, LiveSnapshot, host_field
from .registry import register


@register
class FroniusLocalAdapter(HttpAdapter):
    type_name = "fronius_local"
    display_name = "Fronius Solar API (lokal)"
    vendor = "Fronius"
    status = "beta"
    default_role = "hybrid"
    capabilities = Capabilities(pv=True, load=True, grid=True, battery=True)
    config_schema = [
        *host_field(),
        ConfigField(
            name="invert_battery_sign",
            label_de="Vorzeichen Batterie umkehren",
            label_en="Invert battery sign",
            type="bool",
            default=False,
        ),
    ]
    docs = "fronius_local"

    async def read_live(self) -> LiveSnapshot:
        url = base_url(str(self.value("host"))) + "/solar_api/v1/GetPowerFlowRealtimeData.fcgi"
        data = await get_json(self.client, url)
        body = data.get("Body", {}).get("Data", {})
        site = body.get("Site", {})
        akku = num(site.get("P_Akku"))
        battery = None
        if akku is not None:
            battery = akku if self.value("invert_battery_sign") else -akku
        load = num(site.get("P_Load"))
        soc = None
        for inv in (body.get("Inverters") or {}).values():
            if inv.get("SOC") is not None:
                soc = num(inv.get("SOC"))
                break
        return LiveSnapshot(
            pv_power_w=max(num(site.get("P_PV")) or 0.0, 0.0),
            load_power_w=abs(load) if load is not None else None,
            grid_power_w=num(site.get("P_Grid")),
            battery_power_w=battery,
            battery_soc_pct=soc,
            energy_today_wh=num(site.get("E_Day")),
            extra={"mode": site.get("Mode")},
        )
