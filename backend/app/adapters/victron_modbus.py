"""Victron GX (Cerbo, Venus OS) per Modbus TCP – Systemwerte unter Unit-ID 100.

Register (com.victronenergy.system): 808–810 PV AC-Ausgang, 811–813 PV AC-Eingang,
817–819 Verbrauch L1–L3, 820–822 Netz L1–L3 (I16, + = Bezug), 842 Batterieleistung
(I16, + = Laden), 843 SoC (U16, %), 850 PV DC-gekoppelt (U16, W).
"""

from __future__ import annotations

from ._modbus import ModbusTcpReader, s16
from .base import AdapterError, Capabilities, ConfigField, InverterAdapter, LiveSnapshot, host_field
from .registry import register


@register
class VictronModbusAdapter(InverterAdapter):
    type_name = "victron_modbus"
    display_name = "Victron GX (Modbus TCP)"
    vendor = "Victron"
    status = "beta"
    default_role = "hybrid"
    capabilities = Capabilities(pv=True, load=True, grid=True, battery=True)
    config_schema = [
        *host_field(502),
        ConfigField(
            name="unit_id", label_de="Unit-ID", label_en="Unit ID", type="number", default=100
        ),
    ]
    docs = "victron_modbus"

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
                int(self.value("unit_id", 100)),
            )
        await self.reader.connect()
        self.connected = True

    async def read_live(self) -> LiveSnapshot:
        if self.reader is None:
            await self.connect()
        # Einzelne Blöcke lesen: nicht belegte Register liefern beim GX einen Fehler
        d = await self.reader.read(808, 15)  # 808..822
        b = await self.reader.read(842, 2)
        pv_dc = (await self.reader.read(850, 1))[0]
        pv_ac = sum(v for v in d[0:6] if v != 0xFFFF)
        load = sum(v for v in d[9:12] if v != 0xFFFF)
        grid = sum(s16(v) for v in d[12:15] if v != 0x7FFF)
        batt = s16(b[0])
        soc = b[1]
        if pv_dc == 0xFFFF:
            pv_dc = 0
        return LiveSnapshot(
            pv_power_w=float(pv_ac + pv_dc),
            load_power_w=float(load),
            grid_power_w=float(grid),
            battery_power_w=float(batt),
            battery_soc_pct=float(soc),
        )

    async def close(self) -> None:
        if self.reader is not None:
            await self.reader.close()
        self.connected = False
