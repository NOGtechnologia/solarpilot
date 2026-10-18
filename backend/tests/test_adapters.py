import json
from pathlib import Path

import httpx
import pytest
import respx

from app.adapters._modbus import FakeRegisterReader, s32
from app.adapters.base import AdapterError
from app.adapters.enphase_local import EnphaseLocalAdapter
from app.adapters.fronius_local import FroniusLocalAdapter
from app.adapters.goodwe_local import map_runtime
from app.adapters.home_assistant import HomeAssistantAdapter
from app.adapters.huawei_modbus import HuaweiModbusAdapter
from app.adapters.mqtt_generic import MqttGenericAdapter, extract
from app.adapters.opendtu import OpenDtuAdapter
from app.adapters.registry import get_adapter_class
from app.adapters.shelly_em import ShellyEmAdapter
from app.adapters.sunspec_modbus import SmaModbusAdapter, SunSpecModbusAdapter
from app.adapters.victron_modbus import VictronModbusAdapter

FIX = Path(__file__).parent / "fixtures"


def fixture(name: str):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def u16(v: int) -> int:
    return v & 0xFFFF


def text_regs(s: str, n: int) -> list[int]:
    raw = s.encode().ljust(n * 2, b"\x00")
    return [int.from_bytes(raw[i : i + 2], "big") for i in range(0, n * 2, 2)]


def sunspec_map() -> dict[int, int]:
    """Aufgezeichnetes Registerabbild eines SunSpec-Wechselrichters mit Zähler und Speicher."""
    regs: list[int] = [0x5375, 0x6E53]
    # Modell 1 Common (66 Register)
    common = (
        text_regs("SMA", 16)
        + text_regs("STP 10.0", 16)
        + [0] * 16
        + text_regs("SN123", 16)
        + [1, 0x8000]
    )
    regs += [1, 66] + common
    # Modell 103 (50 Register): W=5432 SF=0, WH=1234567 SF=0, DCW=5600, Tmp=41.5 (SF -1), St=4
    m103 = [0] * 50
    m103[12], m103[13] = 5432, 0
    m103[22], m103[23], m103[24] = 1234567 >> 16, 1234567 & 0xFFFF, 0
    m103[29], m103[30] = 5600, 0
    m103[31], m103[35], m103[36] = 415, u16(-1), 4
    regs += [103, 50] + m103
    # Modell 160 mit 2 Modulen (8 + 2·20 = 48)
    m160 = [u16(-2), u16(-1), 0, 0, 0, 0, 2, 0]
    for i, (a, v, w) in enumerate(((812, 4100, 3300), (650, 3950, 2560))):
        blk = [i + 1] + text_regs(f"PV{i + 1}", 8) + [a, v, w, 0, 0, 0, 0, 0, 0, 0, 0]
        m160 += blk
    regs += [160, 48] + m160
    # Modell 124 (24 Register): SoC 734 · 10^-1 = 73.4 %
    m124 = [0] * 24
    m124[6], m124[20] = 734, u16(-1)
    regs += [124, 24] + m124
    # Modell 203 (105 Register): W = -1500 (Einspeisung)
    m203 = [0] * 105
    m203[16], m203[20] = u16(-1500), 0
    regs += [203, 105] + m203
    regs += [0xFFFF, 0]
    return {40000 + i: v for i, v in enumerate(regs)}


async def test_sunspec_full_map():
    fake = FakeRegisterReader(sunspec_map())
    a = SunSpecModbusAdapter(config={"host": "x"}, reader_factory=lambda unit: fake)
    snap = await a.read_live()
    assert snap.pv_power_w == 5432
    assert snap.temperature_c == pytest.approx(41.5)
    assert snap.battery_soc_pct == pytest.approx(73.4)
    assert snap.grid_power_w == -1500
    assert snap.extra["energy_total_wh"] == 1234567
    assert snap.extra["device"]["manufacturer"] == "SMA"
    assert [s.name for s in snap.strings] == ["PV1", "PV2"]
    assert snap.strings[0].current_a == pytest.approx(8.12)
    assert snap.strings[0].voltage_v == pytest.approx(410.0)
    assert snap.strings[1].power_w == 2560
    await a.close()


async def test_sunspec_invert_and_missing_marker():
    fake = FakeRegisterReader(sunspec_map())
    a = SunSpecModbusAdapter(
        config={"host": "x", "invert_grid_sign": True}, reader_factory=lambda u: fake
    )
    assert (await a.read_live()).grid_power_w == 1500
    empty = FakeRegisterReader({})
    b = SunSpecModbusAdapter(config={"host": "x"}, reader_factory=lambda u: empty)
    with pytest.raises(AdapterError):
        await b.connect()


def test_sunspec_aliases_defaults():
    assert SmaModbusAdapter.defaults()["unit_id"] == 126
    assert get_adapter_class("kostal_modbus").defaults()["port"] == 1502
    assert get_adapter_class("solaredge_modbus").defaults()["port"] == 1502


@respx.mock
async def test_fronius_power_flow():
    respx.get("http://10.0.0.5/solar_api/v1/GetPowerFlowRealtimeData.fcgi").mock(
        return_value=httpx.Response(200, json=fixture("fronius_powerflow.json"))
    )
    a = FroniusLocalAdapter(config={"host": "10.0.0.5"})
    snap = await a.read_live()
    assert snap.pv_power_w == 6120
    assert snap.load_power_w == 1250
    assert snap.grid_power_w == -2870
    assert snap.battery_power_w == 2000  # P_Akku −2000 = lädt
    assert snap.battery_soc_pct == 54.3
    assert snap.energy_today_wh == 18300
    await a.close()


@respx.mock
async def test_fronius_night_nulls():
    data = fixture("fronius_powerflow.json")
    data["Body"]["Data"]["Site"].update({"P_PV": None, "P_Akku": None})
    respx.get(url__regex=r".*GetPowerFlow.*").mock(return_value=httpx.Response(200, json=data))
    snap = await FroniusLocalAdapter(config={"host": "10.0.0.5"}).read_live()
    assert snap.pv_power_w == 0 and snap.battery_power_w is None


@respx.mock
async def test_http_errors_are_readable():
    respx.get(url__regex=r".*GetPowerFlow.*").mock(return_value=httpx.Response(500))
    with pytest.raises(AdapterError, match="HTTP 500"):
        await FroniusLocalAdapter(config={"host": "10.0.0.5"}).read_live()
    respx.get(url__regex=r".*livedata.*").mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(AdapterError, match="Keine Verbindung"):
        await OpenDtuAdapter(config={"host": "10.0.0.6"}).read_live()


@respx.mock
async def test_opendtu():
    respx.get("http://10.0.0.6/api/livedata/status").mock(
        return_value=httpx.Response(200, json=fixture("opendtu_status.json"))
    )
    snap = await OpenDtuAdapter(config={"host": "10.0.0.6"}).read_live()
    assert snap.pv_power_w == pytest.approx(612.4)
    assert snap.energy_today_wh == 2140
    assert snap.extra["yield_total_wh"] == pytest.approx(1523400)
    assert len(snap.strings) == 2 and snap.strings[0].name == "Süd"


@respx.mock
async def test_shelly_gen2_and_gen1_fallback():
    respx.get("http://10.0.0.7/rpc/EM.GetStatus").mock(
        return_value=httpx.Response(200, json={"id": 0, "total_act_power": 734.5})
    )
    assert (await ShellyEmAdapter(config={"host": "10.0.0.7"}).read_live()).grid_power_w == 734.5
    respx.get("http://10.0.0.8/rpc/EM.GetStatus").mock(return_value=httpx.Response(404))
    respx.get("http://10.0.0.8/status").mock(
        return_value=httpx.Response(
            200, json={"emeters": [{"power": 100}, {"power": -50}, {"power": 20}]}
        )
    )
    snap = await ShellyEmAdapter(config={"host": "10.0.0.8", "invert_sign": True}).read_live()
    assert snap.grid_power_w == -70


@respx.mock
async def test_enphase():
    route = respx.get("https://10.0.0.9/production.json").mock(
        return_value=httpx.Response(200, json=fixture("enphase_production.json"))
    )
    a = EnphaseLocalAdapter(config={"host": "10.0.0.9"}, secrets={"token": "abc"})
    snap = await a.read_live()
    assert route.calls[0].request.headers["authorization"] == "Bearer abc"
    assert snap.pv_power_w == 3210.4 and snap.load_power_w == 980.2 and snap.grid_power_w == -2230.2
    assert snap.energy_today_wh == 12500


@respx.mock
async def test_home_assistant_units_and_validation():
    respx.get("http://ha:8123/api/states/sensor.pv_power").mock(
        return_value=httpx.Response(
            200, json={"state": "2.5", "attributes": {"unit_of_measurement": "kW"}}
        )
    )
    respx.get("http://ha:8123/api/states/sensor.soc").mock(
        return_value=httpx.Response(
            200, json={"state": "81", "attributes": {"unit_of_measurement": "%"}}
        )
    )
    a = HomeAssistantAdapter(
        config={
            "url": "http://ha:8123",
            "pv_entity": "sensor.pv_power",
            "soc_entity": "sensor.soc",
        },
        secrets={"token": "t"},
    )
    snap = await a.read_live()
    assert snap.pv_power_w == 2500 and snap.battery_soc_pct == 81
    bad = HomeAssistantAdapter(
        config={"url": "http://ha:8123", "pv_entity": "../config"}, secrets={"token": "t"}
    )
    with pytest.raises(AdapterError, match="Ungültige Entity"):
        await bad.read_live()
    with pytest.raises(AdapterError):
        await HomeAssistantAdapter(config={"url": "http://ha:8123"}).read_live()


def _put32(regs: dict, addr: int, value: int) -> None:
    v = value & 0xFFFFFFFF
    regs[addr], regs[addr + 1] = v >> 16, v & 0xFFFF


async def test_huawei_registers():
    regs: dict[int, int] = {}
    _put32(regs, 32064, 5200)
    _put32(regs, 32080, 5000)
    _put32(regs, 32114, 1834)  # 18,34 kWh
    _put32(regs, 37113, 1200)  # Einspeisung 1,2 kW
    regs[37760] = 655
    _put32(regs, 37765, -800)  # entlädt
    a = HuaweiModbusAdapter(
        config={"host": "x", "has_battery": True}, reader=FakeRegisterReader(regs)
    )
    snap = await a.read_live()
    assert snap.pv_power_w == 5200 and snap.energy_today_wh == 18340
    assert snap.grid_power_w == -1200
    assert snap.battery_soc_pct == 65.5 and snap.battery_power_w == -800
    assert snap.load_power_w == 5200 - 1200 + 800
    assert s32(0xFFFF, 0xFCE0) == -800


async def test_victron_registers():
    regs = dict.fromkeys(range(808, 851), 0)
    regs[808] = 1200  # PV AC
    regs.update({817: 400, 818: 300, 819: 200})
    regs.update({820: 100, 821: 0xFFFF - 49, 822: 0})  # +100, −50
    regs[842] = 0xFFFF - 299  # −300 W
    regs[843] = 77
    regs[850] = 2500
    snap = await VictronModbusAdapter(
        config={"host": "x"}, reader=FakeRegisterReader(regs)
    ).read_live()
    assert snap.pv_power_w == 3700 and snap.load_power_w == 900
    assert snap.grid_power_w == 50 and snap.battery_power_w == -300 and snap.battery_soc_pct == 77


def test_goodwe_mapping():
    snap = map_runtime(
        {
            "ppv": 4100,
            "meter_active_power": 1500,
            "pbattery1": -900,
            "battery_soc": 61,
            "house_consumption": 1700,
            "e_day": 12.3,
            "temperature": 38,
        }
    )
    assert snap.pv_power_w == 4100 and snap.grid_power_w == -1500
    assert snap.battery_power_w == 900 and snap.energy_today_wh == pytest.approx(12300)


def test_mqtt_extract_and_messages():
    assert extract(b"123.4", None) == 123.4
    assert extract(b'{"SML": {"Power": -250}}', "SML.Power") == -250
    assert extract(b'{"value": 7}', None) == 7
    assert extract(b"kaputt", None) is None
    a = MqttGenericAdapter(config={"host": "x", "pv_topic": "pv/w", "grid_topic": "grid/w"})
    a.on_message("pv/w", b"900")
    a.on_message("grid/w", b"-100")
    a.on_message("other", b"1")
    assert a._values == {"pv_power_w": 900, "grid_power_w": -100}


async def test_demo_adapter_energy_balance():
    from app.adapters.base import SiteContext

    a = get_adapter_class("demo")(config={}, site=SiteContext(lat=53.08, lon=8.8))
    snap = await a.read_live()
    bal = snap.pv_power_w + snap.grid_power_w - snap.battery_power_w
    assert bal == pytest.approx(snap.load_power_w, abs=0.5)
    assert 0 <= snap.battery_soc_pct <= 100
    snap2 = await a.read_live()
    assert snap2.energy_today_wh >= snap.energy_today_wh
