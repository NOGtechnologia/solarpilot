"""Gemeinsame Modbus-TCP-Hilfen für Adapter (pymodbus 3.x)."""

from __future__ import annotations

import inspect
from typing import Protocol

from .base import AdapterError


class RegisterReader(Protocol):
    async def read(self, address: int, count: int) -> list[int]: ...

    async def close(self) -> None: ...


class ModbusTcpReader:
    """Dünner Wrapper um ``AsyncModbusTcpClient`` – kompatibel zu ``slave=`` und ``device_id=``."""

    def __init__(self, host: str, port: int = 502, unit_id: int = 1, timeout: float = 3.0) -> None:
        from pymodbus.client import AsyncModbusTcpClient

        self.unit_id = unit_id
        self.client = AsyncModbusTcpClient(host, port=port, timeout=timeout, retries=1)
        params = inspect.signature(self.client.read_holding_registers).parameters
        self._unit_kw = "device_id" if "device_id" in params else "slave"
        self.host, self.port = host, port

    async def connect(self) -> None:
        ok = await self.client.connect()
        if not ok:
            raise AdapterError(f"Keine Modbus-Verbindung zu {self.host}:{self.port}")

    async def read(self, address: int, count: int) -> list[int]:
        out: list[int] = []
        # Modbus erlaubt max. 125 Register pro Anfrage
        while count > 0:
            n = min(count, 120)
            rr = await self.client.read_holding_registers(
                address, count=n, **{self._unit_kw: self.unit_id}
            )
            if rr.isError():
                raise AdapterError(f"Modbus-Fehler bei Register {address}: {rr}")
            out.extend(rr.registers)
            address += n
            count -= n
        return out

    async def close(self) -> None:
        self.client.close()


class FakeRegisterReader:
    """Für Tests: liest aus einem Dict ``{adresse: wert}``."""

    def __init__(self, registers: dict[int, int]) -> None:
        self.registers = registers

    async def connect(self) -> None:
        return None

    async def read(self, address: int, count: int) -> list[int]:
        try:
            return [self.registers[a] for a in range(address, address + count)]
        except KeyError as exc:
            raise AdapterError(f"Register {exc} nicht vorhanden") from exc

    async def close(self) -> None:
        return None


def s16(v: int) -> int:
    return v - 0x10000 if v & 0x8000 else v


def u32(hi: int, lo: int) -> int:
    return (hi << 16) | lo


def s32(hi: int, lo: int) -> int:
    v = u32(hi, lo)
    return v - 0x1_0000_0000 if v & 0x8000_0000 else v


def regs_to_str(regs: list[int]) -> str:
    raw = b"".join(r.to_bytes(2, "big") for r in regs)
    return raw.split(b"\x00", 1)[0].decode("ascii", errors="ignore").strip()
