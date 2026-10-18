"""Generischer SunSpec-Modbus-TCP-Adapter.

Unterstützt die Modelle 1 (Common), 101/102/103 (Wechselrichter), 160 (MPPT-Strings),
124 (Speicher) und 201–204 (Zähler). Damit werden u. a. SMA, SolarEdge, Kostal und Fronius
abgedeckt (siehe Aliase unten).
"""

from __future__ import annotations

from typing import Any

from ._modbus import FakeRegisterReader, ModbusTcpReader, regs_to_str, s16, u32
from .base import (
    AdapterError,
    Capabilities,
    ConfigField,
    InverterAdapter,
    LiveSnapshot,
    StringValue,
    host_field,
)
from .registry import register

SUNS_MARKER = [0x5375, 0x6E53]  # "SunS"
BASE_ADDRESSES = (40000, 0, 50000)
NOT_IMPL_S16 = 0x8000
NOT_IMPL_U16 = 0xFFFF


def _sf(raw: int) -> int:
    v = s16(raw)
    return 0 if raw == NOT_IMPL_S16 else v


def scaled(raw: int, sf_raw: int, signed: bool = True) -> float | None:
    if signed and raw == NOT_IMPL_S16:
        return None
    if not signed and raw == NOT_IMPL_U16:
        return None
    value = s16(raw) if signed else raw
    return value * (10 ** _sf(sf_raw))


def parse_inverter(d: list[int]) -> dict[str, Any]:
    """Modell 101/102/103 (Datenblock ohne ID und L)."""
    wh_raw = u32(d[22], d[23])
    return {
        "ac_power_w": scaled(d[12], d[13]),
        "energy_total_wh": None if wh_raw == 0 else wh_raw * (10 ** _sf(d[24])),
        "dc_power_w": scaled(d[29], d[30]),
        "temperature_c": scaled(d[31], d[35]),
        "state": d[36] if len(d) > 36 else None,
    }


def parse_mppt(d: list[int]) -> list[StringValue]:
    """Modell 160 – Strings/MPPT-Tracker."""
    dca_sf, dcv_sf, dcw_sf = d[0], d[1], d[2]
    n = d[6]
    out: list[StringValue] = []
    for i in range(n):
        base = 8 + i * 20
        if base + 20 > len(d):
            break
        blk = d[base : base + 20]
        name = regs_to_str(blk[1:9]) or f"String {i + 1}"
        out.append(
            StringValue(
                name=name,
                current_a=scaled(blk[9], dca_sf, signed=False),
                voltage_v=scaled(blk[10], dcv_sf, signed=False),
                power_w=scaled(blk[11], dcw_sf, signed=False),
            )
        )
    return out


def parse_storage(d: list[int]) -> dict[str, Any]:
    """Modell 124 – Ladezustand."""
    return {"soc_pct": scaled(d[6], d[20], signed=False)}


def parse_meter(d: list[int]) -> dict[str, Any]:
    """Modell 201–204 – Gesamtwirkleistung."""
    return {"power_w": scaled(d[16], d[20])}


class SunSpecClient:
    def __init__(self, reader: Any) -> None:
        self.reader = reader
        self.models: dict[int, tuple[int, int]] = {}  # id -> (adresse Datenblock, länge)
        self.common: dict[str, str] = {}

    async def discover(self, base: int | None = None) -> None:
        bases = (base,) if base is not None else BASE_ADDRESSES
        for b in bases:
            try:
                marker = await self.reader.read(b, 2)
            except AdapterError:
                continue
            if marker == SUNS_MARKER:
                await self._walk(b + 2)
                return
        raise AdapterError("Kein SunSpec-Gerät gefunden (Marker 'SunS' fehlt)")

    async def _walk(self, addr: int) -> None:
        for _ in range(64):
            hdr = await self.reader.read(addr, 2)
            model_id, length = hdr
            if model_id == 0xFFFF or length == 0:
                break
            self.models.setdefault(model_id, (addr + 2, length))
            addr += 2 + length
        if 1 in self.models:
            a, n = self.models[1]
            d = await self.reader.read(a, min(n, 65))
            self.common = {
                "manufacturer": regs_to_str(d[0:16]),
                "model": regs_to_str(d[16:32]),
                "serial": regs_to_str(d[48:64]) if len(d) >= 64 else "",
            }

    async def block(self, model_id: int) -> list[int] | None:
        if model_id not in self.models:
            return None
        a, n = self.models[model_id]
        return await self.reader.read(a, n)


@register
class SunSpecModbusAdapter(InverterAdapter):
    type_name = "sunspec_modbus"
    display_name = "SunSpec Modbus TCP (generisch)"
    vendor = "SunSpec"
    status = "beta"
    default_role = "inverter"
    capabilities = Capabilities(pv=True, battery=True, grid=True, strings=True)
    default_port = 502
    default_unit_id = 1
    config_schema = [
        *host_field(502),
        ConfigField(
            name="unit_id",
            label_de="Unit-ID / Slave-ID",
            label_en="Unit ID",
            type="number",
            default=1,
        ),
        ConfigField(
            name="base_address",
            label_de="Basisadresse (leer = automatisch)",
            label_en="Base address (empty = auto)",
            type="number",
        ),
        ConfigField(
            name="meter_unit_id",
            label_de="Unit-ID Zähler (optional)",
            label_en="Meter unit ID (optional)",
            type="number",
            help_de="Falls der Zähler unter einer eigenen Unit-ID erreichbar ist",
            help_en="If the meter is reachable under its own unit ID",
        ),
        ConfigField(
            name="invert_grid_sign",
            label_de="Vorzeichen Netz umkehren",
            label_en="Invert grid sign",
            type="bool",
            default=False,
            help_de="Aktivieren, wenn Einspeisung als Bezug angezeigt wird",
            help_en="Enable if feed-in is shown as import",
        ),
    ]
    docs = "sunspec_modbus"

    def __init__(self, *args, reader_factory=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._reader_factory = reader_factory
        self.inv: SunSpecClient | None = None
        self.meter: SunSpecClient | None = None

    def _make_reader(self, unit_id: int):
        if self._reader_factory:
            return self._reader_factory(unit_id)
        return ModbusTcpReader(
            str(self.value("host")),
            int(self.value("port", self.default_port)),
            unit_id,
        )

    async def connect(self) -> None:
        if not self._reader_factory and not self.value("host"):
            raise AdapterError("Host fehlt")
        unit = int(self.value("unit_id", self.default_unit_id))
        reader = self._make_reader(unit)
        await reader.connect()
        base = self.value("base_address")
        self.inv = SunSpecClient(reader)
        await self.inv.discover(int(base) if base not in (None, "") else None)
        meter_unit = self.value("meter_unit_id")
        if meter_unit not in (None, "") and int(meter_unit) != unit:
            mreader = self._make_reader(int(meter_unit))
            await mreader.connect()
            self.meter = SunSpecClient(mreader)
            await self.meter.discover(int(base) if base not in (None, "") else None)
        self.connected = True

    async def read_live(self) -> LiveSnapshot:
        if not self.inv:
            await self.connect()
        assert self.inv is not None
        snap = LiveSnapshot(extra={"device": self.inv.common})
        for mid in (103, 102, 101):
            d = await self.inv.block(mid)
            if d:
                inv = parse_inverter(d)
                ac = inv["ac_power_w"]
                snap.pv_power_w = max(ac, 0.0) if ac is not None else None
                snap.temperature_c = inv["temperature_c"]
                snap.extra["energy_total_wh"] = inv["energy_total_wh"]
                snap.extra["dc_power_w"] = inv["dc_power_w"]
                break
        d = await self.inv.block(160)
        if d:
            snap.strings = parse_mppt(d)
        d = await self.inv.block(124)
        if d:
            snap.battery_soc_pct = parse_storage(d)["soc_pct"]
        meter_client = self.meter or self.inv
        for mid in (203, 204, 202, 201):
            d = await meter_client.block(mid)
            if d:
                p = parse_meter(d)["power_w"]
                if p is not None:
                    snap.grid_power_w = -p if self.value("invert_grid_sign") else p
                break
        return snap

    async def close(self) -> None:
        for c in (self.inv, self.meter):
            if c:
                await c.reader.close()
        self.inv = self.meter = None
        self.connected = False


@register
class SmaModbusAdapter(SunSpecModbusAdapter):
    type_name = "sma_modbus"
    display_name = "SMA (Modbus TCP / SunSpec)"
    vendor = "SMA"
    default_unit_id = 126
    config_schema = [
        f.model_copy(update={"default": 126}) if f.name == "unit_id" else f
        for f in SunSpecModbusAdapter.config_schema
    ]
    docs = "sma"


@register
class SolarEdgeModbusAdapter(SunSpecModbusAdapter):
    type_name = "solaredge_modbus"
    display_name = "SolarEdge (Modbus TCP / SunSpec)"
    vendor = "SolarEdge"
    default_port = 1502
    config_schema = [
        f.model_copy(update={"default": 1502}) if f.name == "port" else f
        for f in SunSpecModbusAdapter.config_schema
    ]
    docs = "solaredge"


@register
class KostalModbusAdapter(SunSpecModbusAdapter):
    type_name = "kostal_modbus"
    display_name = "Kostal Plenticore (Modbus TCP / SunSpec)"
    vendor = "Kostal"
    default_port = 1502
    default_unit_id = 71
    config_schema = [
        f.model_copy(update={"default": {"port": 1502, "unit_id": 71}[f.name]})
        if f.name in ("port", "unit_id")
        else f
        for f in SunSpecModbusAdapter.config_schema
    ]
    docs = "kostal"


__all__ = ["FakeRegisterReader", "SunSpecClient", "SunSpecModbusAdapter"]
