"""Enphase IQ Gateway (Envoy) lokal mit Token (Firmware ≥ 7).

Token über https://entrez.enphaseenergy.com holen. Das Gateway nutzt ein selbstsigniertes
Zertifikat, daher ist die TLS-Prüfung für diesen Adapter abschaltbar.
"""

from __future__ import annotations

import httpx

from ._http import base_url, get_json, num
from ._httpadapter import HttpAdapter
from .base import Capabilities, ConfigField, LiveSnapshot, host_field
from .registry import register


@register
class EnphaseLocalAdapter(HttpAdapter):
    type_name = "enphase_local"
    display_name = "Enphase IQ Gateway (lokal)"
    vendor = "Enphase"
    status = "beta"
    default_role = "hybrid"
    capabilities = Capabilities(pv=True, load=True, grid=True)
    config_schema = [
        *host_field(),
        ConfigField(
            name="token",
            label_de="Token",
            label_en="Token",
            type="password",
            required=True,
            secret=True,
        ),
        ConfigField(
            name="verify_tls",
            label_de="Zertifikat prüfen",
            label_en="Verify certificate",
            type="bool",
            default=False,
        ),
    ]
    docs = "enphase_local"

    def make_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=8.0, verify=bool(self.value("verify_tls", False)))

    async def read_live(self) -> LiveSnapshot:
        url = base_url(str(self.value("host")), "https") + "/production.json"
        headers = {"Authorization": f"Bearer {self.value('token', '')}"}
        data = await get_json(self.client, url, params={"details": 1}, headers=headers)
        prod = data.get("production", [])
        eim = next((p for p in prod if p.get("type") == "eim"), None)
        inv = next((p for p in prod if p.get("type") == "inverters"), None)
        pv = num((eim or {}).get("wNow"))
        if pv is None:
            pv = num((inv or {}).get("wNow"))
        cons = {c.get("measurementType"): c for c in data.get("consumption", [])}
        load = num(cons.get("total-consumption", {}).get("wNow"))
        grid = num(cons.get("net-consumption", {}).get("wNow"))
        return LiveSnapshot(
            pv_power_w=max(pv or 0.0, 0.0),
            load_power_w=load,
            grid_power_w=grid,
            energy_today_wh=num((eim or {}).get("whToday")),
        )
