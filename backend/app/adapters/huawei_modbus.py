"""Huawei SUN2000 per Modbus TCP (SDongle oder WLAN-AP des Wechselrichters).

Register laut Huawei „SUN2000 MODBUS Interface Definitions“:
32064 Eingangsleistung (I32, W), 32080 Wirkleistung (I32, W), 32114 Tagesertrag (U32, 0,01 kWh),
37113 Zähler-Wirkleistung (I32, W, + = Einspeisung), 37760 Batterie-SoC (U16, 0,1 %),
37765 Batterieleistung (I32, W, + = Laden).
"""

from __future__ import annotations

from ._modbus import ModbusTcpReader, s32, u32
from .base import AdapterError, Capabilities, ConfigField, InverterAdapter, LiveSnapshot, host_field
from .registry import register


@register
class HuaweiModbusAdapter(InverterAdapter):
    type_name = "huawei_modbus"
    display_name = "Huawei SUN2000 (Modbus TCP)"
    vendor = "Huawei"
    status = "beta"
    default_role = "hybrid"
    capabilities = Capabilities(pv=True, grid=True, battery=True, load=True)
    config_schema = [
        *host_field(502),
        ConfigField(
            name="unit_id", label_de="Unit-ID", label_en="Unit ID", type="number", default=1
        ),
        ConfigField(
            name="has_meter",
            label_de="Smart Meter vorhanden",
            label_en="Smart meter installed",
            type="bool",
            default=True,
        ),
        ConfigField(
            name="has_battery",
            label_de="Batterie vorhanden",
            label_en="Battery installed",
            type="bool",
            default=False,
        ),
    ]
    docs = "huawei_modbus"

    def __init__(self, *args, reader=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.reader = reader

    async def connect(self) -> None:
        if self.reader is None:
            if not self.value("host"):
                raise AdapterError("Host fehlt")
            self.reader = ModbusTcpReader(
                str(self.value("host")),
                int(self.value("port", 502)),
                int(self.value("unit_id", 1)),
                timeout=5.0,
            )
        await self.reader.connect()
        self.connected = True

    async def read_live(self) -> LiveSnapshot:
        if self.reader is None:
            await self.connect()
        r = self.reader
        dc = await r.read(32064, 2)
        ac = await r.read(32080, 2)
        day = await r.read(32114, 2)
        snap = LiveSnapshot(
            pv_power_w=max(float(s32(*dc)), 0.0),
            energy_today_wh=u32(*day) * 10.0,
            extra={"ac_power_w": float(s32(*ac))},
        )
        if self.value("has_meter"):
            m = await r.read(37113, 2)
            snap.grid_power_w = -float(s32(*m))  # Huawei: + = Einspeisung
        if self.value("has_battery"):
            soc = await r.read(37760, 1)
            bp = await r.read(37765, 2)
            snap.battery_soc_pct = soc[0] / 10
            snap.battery_power_w = float(s32(*bp))
        if snap.grid_power_w is not None:
            snap.load_power_w = max(
                (snap.pv_power_w or 0) + snap.grid_power_w - (snap.battery_power_w or 0), 0.0
            )
        return snap

    async def close(self) -> None:
        if self.reader is not None:
            await self.reader.close()
        self.connected = False
