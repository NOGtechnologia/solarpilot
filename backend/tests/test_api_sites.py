import asyncio

from app.crypto import decrypt_json
from app.models import Device

SITE = {
    "name": "Wohnhaus",
    "lat": 53.08,
    "lon": 8.8,
    "arrays": [{"kwp": 9.8, "tilt": 35, "azimuth": 180}],
    "battery_kwh": 10,
}


def test_site_crud(admin):
    r = admin.post("/api/sites", json=SITE)
    assert r.status_code == 200
    sid = r.json()["id"]
    assert r.json()["kwp"] == 9.8
    r = admin.put(f"/api/sites/{sid}", json={**SITE, "name": "Haus"})
    assert r.json()["name"] == "Haus"
    assert len(admin.get("/api/sites").json()) == 1
    assert admin.delete(f"/api/sites/{sid}").status_code == 200
    assert admin.get("/api/sites").json() == []


def test_site_validation(admin):
    assert admin.post("/api/sites", json={**SITE, "lat": 100}).status_code == 422
    assert admin.post("/api/sites", json={**SITE, "arrays": [{"kwp": -1}]}).status_code == 422


def test_device_secrets_are_encrypted_and_masked(admin):
    sid = admin.post("/api/sites", json=SITE).json()["id"]
    r = admin.post(
        "/api/devices",
        json={
            "site_id": sid,
            "name": "Envoy",
            "type": "enphase_local",
            "config": {"host": "192.168.1.9"},
            "secrets": {"token": "supersecret"},
        },
    )
    assert r.status_code == 200, r.text
    dev = r.json()
    assert dev["secrets"]["token"] == "__unchanged__"
    assert "supersecret" not in r.text
    from app.db import new_session

    with new_session() as s:
        stored = s.get(Device, dev["id"])
        assert "supersecret" not in stored.secrets_enc
        assert decrypt_json(stored.secrets_enc)["token"] == "supersecret"
    # Update mit Maske behält das Secret
    r = admin.put(
        f"/api/devices/{dev['id']}",
        json={
            "site_id": sid,
            "name": "Envoy 2",
            "type": "enphase_local",
            "config": {"host": "192.168.1.10"},
            "secrets": {"token": "__unchanged__"},
        },
    )
    assert r.status_code == 200
    with new_session() as s:
        assert decrypt_json(s.get(Device, dev["id"]).secrets_enc)["token"] == "supersecret"


def test_required_fields_and_unknown_type(admin):
    sid = admin.post("/api/sites", json=SITE).json()["id"]
    r = admin.post("/api/devices", json={"site_id": sid, "name": "x", "type": "fronius_local"})
    assert r.status_code == 422
    r = admin.post("/api/devices", json={"site_id": sid, "name": "x", "type": "nope"})
    assert r.status_code == 422


def test_only_one_grid_meter(admin):
    sid = admin.post("/api/sites", json=SITE).json()["id"]
    body = {"site_id": sid, "name": "Shelly", "type": "shelly_3em", "config": {"host": "1.2.3.4"}}
    assert admin.post("/api/devices", json=body).json()["role"] == "grid_meter"
    assert admin.post("/api/devices", json={**body, "name": "Shelly 2"}).status_code == 409


def test_adapter_catalog(admin):
    adapters = admin.get("/api/adapters").json()
    types = {a["type"] for a in adapters}
    assert {
        "demo",
        "sunspec_modbus",
        "fronius_local",
        "sma_modbus",
        "opendtu",
        "shelly_3em",
        "huawei_modbus",
        "victron_modbus",
        "home_assistant",
        "mqtt_generic",
    } <= types
    demo = next(a for a in adapters if a["type"] == "demo")
    assert demo["config_schema"][0]["name"] == "kwp"


def test_adapter_connection_test(admin):
    r = admin.post("/api/adapters/demo/test", json={"config": {"kwp": 5}})
    assert r.json()["ok"] is True
    assert "pv_power_w" in r.json()["snapshot"]
    r = admin.post("/api/adapters/fronius_local/test", json={"config": {"host": "127.0.0.1:9"}})
    assert r.json()["ok"] is False and r.json()["error"]


def test_demo_and_data_endpoints(admin):
    r = admin.post("/api/demo", json={})
    assert r.status_code == 200 and r.json()["created"]
    assert admin.post("/api/demo", json={}).json()["created"] is False
    rt = admin.app.state.rt
    asyncio.run(rt.poller.reload())
    payload = asyncio.run(rt.poller.poll_once())
    assert payload["all"]["pv_power_w"] is not None
    assert admin.get("/api/live").json()["devices"][0]["online"] is True
    k = admin.get("/api/kpis").json()["today"]
    assert k["pv_wh"] >= 0 and "autarky_pct" in k
    # Vortag bzw. Vormonat verwenden, damit der Test auch kurz nach Mitternacht stabil ist
    from datetime import date, timedelta

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    last_month = (date.today().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    day = admin.get(f"/api/history?range=day&date={yesterday}").json()
    assert len(day["series"]["ts"]) > 100
    assert len(day["forecast"]["ts"]) > 10
    for rng in ("week", "month", "year"):
        h = admin.get(f"/api/history?range={rng}&date={yesterday}").json()
        assert h["energy"]["total"]["pv_wh"] > 0
    assert admin.get("/api/history?range=decade").status_code == 422
    assert admin.get("/api/history?date=kaputt").status_code == 422
    rep = admin.get(f"/api/reports/monthly?month={last_month}").json()
    assert rep["total"]["pv_wh"] > 0
    pdf = admin.get("/api/reports/monthly.pdf?lang=en")
    assert pdf.content.startswith(b"%PDF")
    ins = admin.get("/api/insights").json()
    assert isinstance(ins["items"], list)
    assert admin.get("/api/history?site=999").status_code == 404


def test_yaml_roundtrip(admin):
    yaml_text = """
sites:
  - name: Haus
    location: { lat: 53.0, lon: 8.8 }
    arrays: [{ kwp: 5, tilt: 30, azimuth: 180 }]
    devices:
      - { type: opendtu, name: DTU, host: 192.168.1.70 }
      - { type: enphase_local, name: Envoy, host: 192.168.1.9, token: geheim }
"""
    r = admin.post("/api/config/import", json={"yaml": yaml_text})
    assert r.json() == {"created": 1, "updated": 0, "devices": 2}
    out = admin.get("/api/config/export").text
    assert "Haus" in out and "opendtu" in out and "geheim" not in out
    bad = "sites:\n  - name: X\n"
    assert admin.post("/api/config/import", json={"yaml": bad}).status_code == 422


def test_websocket(admin):
    admin.post("/api/demo", json={})
    with admin.websocket_connect("/api/ws") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "live"
        ws.send_text("ping")
        assert ws.receive_json()["type"] == "pong"


def test_websocket_requires_auth(client):
    client.post("/api/auth/setup", json={"username": "admin", "password": "secret123"})
    client.post("/api/auth/logout")
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/api/ws") as ws:
        ws.receive_json()
