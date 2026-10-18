"""MQTT-Ausgabe der Live-Werte inkl. Home-Assistant-Auto-Discovery."""

from __future__ import annotations

import json
import logging
import re
import threading
from typing import Any

log = logging.getLogger(__name__)

SENSORS = [
    ("pv_power_w", "PV-Leistung", "power", "W", "measurement", "mdi:solar-power"),
    ("load_power_w", "Hausverbrauch", "power", "W", "measurement", "mdi:home-lightning-bolt"),
    ("grid_power_w", "Netz", "power", "W", "measurement", "mdi:transmission-tower"),
    ("battery_power_w", "Batterieleistung", "power", "W", "measurement", "mdi:battery-charging"),
    ("battery_soc_pct", "Batterie-Ladestand", "battery", "%", "measurement", None),
    ("energy_today_wh", "Ertrag heute", "energy", "Wh", "total_increasing", "mdi:solar-power"),
]


def slugify(name: str) -> str:
    s = re.sub(
        r"[^a-z0-9]+",
        "_",
        name.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss"),
    ).strip("_")
    return s or "site"


def discovery_messages(
    site_key: str, site_name: str, prefix: str, discovery_prefix: str
) -> list[tuple[str, dict[str, Any]]]:
    state_topic = f"{prefix}/{site_key}/state"
    device = {
        "identifiers": [f"solarpilot_{site_key}"],
        "name": f"SolarPilot {site_name}",
        "manufacturer": "SolarPilot",
        "model": "PV-Dashboard",
    }
    out = []
    for key, label, dev_class, unit, state_class, icon in SENSORS:
        uid = f"solarpilot_{site_key}_{key}"
        cfg: dict[str, Any] = {
            "name": label,
            "unique_id": uid,
            "object_id": uid,
            "state_topic": state_topic,
            "value_template": f"{{{{ value_json.{key} }}}}",
            "unit_of_measurement": unit,
            "device_class": dev_class,
            "state_class": state_class,
            "availability_topic": f"{prefix}/status",
            "device": device,
        }
        if icon:
            cfg["icon"] = icon
        out.append((f"{discovery_prefix}/sensor/{uid}/config", cfg))
    return out


def state_payload(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {k: snapshot.get(k) for k, *_ in SENSORS} | {"timestamp": snapshot.get("timestamp_utc")}


class MqttPublisher:
    def __init__(self) -> None:
        self.cfg: dict[str, Any] = {}
        self.client = None
        self.sites: dict[str, str] = {}
        self._announced: set[str] = set()
        self._lock = threading.Lock()
        self.connected = False

    def configure(self, cfg: dict[str, Any], sites: dict[int, str]) -> None:
        new_sites = {str(k): v for k, v in sites.items()}
        if cfg == self.cfg and self.client is not None:
            self.sites = new_sites
            return
        self.stop()
        self.cfg, self.sites = dict(cfg), new_sites
        if not cfg.get("enabled") or not cfg.get("host"):
            return
        import paho.mqtt.client as mqtt

        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="solarpilot")
        if cfg.get("username"):
            c.username_pw_set(cfg["username"], cfg.get("password") or None)
        prefix = cfg.get("prefix", "solarpilot")
        c.will_set(f"{prefix}/status", "offline", retain=True)

        def on_connect(client, _u, _f, rc, _p=None):
            self.connected = not rc.is_failure if hasattr(rc, "is_failure") else rc == 0
            if self.connected:
                client.publish(f"{prefix}/status", "online", retain=True)
                self._announced.clear()

        c.on_connect = on_connect
        try:
            c.connect_async(cfg["host"], int(cfg.get("port") or 1883), keepalive=60)
            c.loop_start()
        except OSError as exc:
            log.warning("MQTT-Verbindung fehlgeschlagen: %s", exc)
            return
        self.client = c

    def stop(self) -> None:
        if self.client is not None:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:  # noqa: BLE001
                pass
        self.client = None
        self.connected = False
        self._announced.clear()

    def publish_live(self, payload: dict[str, Any]) -> None:
        if self.client is None or not self.connected:
            return
        prefix = self.cfg.get("prefix", "solarpilot")
        items = dict(payload.get("sites") or {})
        if payload.get("all"):
            items["all"] = payload["all"]
        for sid, snap in items.items():
            name = "Alle Anlagen" if sid == "all" else self.sites.get(sid, f"Site {sid}")
            key = "all" if sid == "all" else f"{sid}_{slugify(name)}"
            if self.cfg.get("discovery", True) and key not in self._announced:
                for topic, cfg in discovery_messages(
                    key, name, prefix, self.cfg.get("discovery_prefix", "homeassistant")
                ):
                    self.client.publish(topic, json.dumps(cfg), retain=True)
                self._announced.add(key)
            self.client.publish(f"{prefix}/{key}/state", json.dumps(state_payload(snap)))
