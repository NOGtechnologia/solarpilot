"""Generischer MQTT-Adapter: abonniert frei wählbare Topics (z. B. Victron, Tasmota-SML, evcc).

Jedes Topic liefert eine Zahl oder JSON; mit ``json_key`` (z. B. ``SML.Power``) wird ein Wert
aus dem JSON gelesen.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from typing import Any

from ._http import num
from .base import AdapterError, Capabilities, ConfigField, InverterAdapter, LiveSnapshot
from .registry import register

TOPIC_FIELDS = {
    "pv_topic": "pv_power_w",
    "load_topic": "load_power_w",
    "grid_topic": "grid_power_w",
    "battery_topic": "battery_power_w",
    "soc_topic": "battery_soc_pct",
    "energy_today_topic": "energy_today_wh",
}


def extract(payload: bytes | str, key: str | None) -> float | None:
    text = payload.decode() if isinstance(payload, bytes) else payload
    if not key:
        v = num(text.strip())
        if v is not None:
            return v
    try:
        obj: Any = json.loads(text)
    except ValueError:
        return None
    if key:
        for part in key.split("."):
            if not isinstance(obj, dict) or part not in obj:
                return None
            obj = obj[part]
    if isinstance(obj, dict) and "value" in obj:
        obj = obj["value"]
    return num(obj)


@register
class MqttGenericAdapter(InverterAdapter):
    type_name = "mqtt_generic"
    display_name = "MQTT (generisch)"
    vendor = "MQTT"
    status = "beta"
    default_role = "hybrid"
    capabilities = Capabilities(pv=True, load=True, grid=True, battery=True)
    config_schema = [
        ConfigField(name="host", label_de="Broker-Host", label_en="Broker host", required=True),
        ConfigField(name="port", label_de="Port", label_en="Port", type="number", default=1883),
        ConfigField(name="username", label_de="Benutzer", label_en="Username"),
        ConfigField(
            name="password", label_de="Passwort", label_en="Password", type="password", secret=True
        ),
        ConfigField(name="json_key", label_de="JSON-Schlüssel (optional)", label_en="JSON key"),
        *[
            ConfigField(name=k, label_de=f"Topic {v}", label_en=f"Topic {v}")
            for k, v in TOPIC_FIELDS.items()
        ],
    ]
    docs = "mqtt_generic"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._values: dict[str, float | None] = {}
        self._lock = threading.Lock()
        self._client = None
        self._last_msg = 0.0

    def on_message(self, topic: str, payload: bytes) -> None:
        for key, field in TOPIC_FIELDS.items():
            if self.value(key) == topic:
                with self._lock:
                    self._values[field] = extract(payload, self.value("json_key"))
                    self._last_msg = time.time()

    async def connect(self) -> None:
        import paho.mqtt.client as mqtt

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if self.value("username"):
            client.username_pw_set(str(self.value("username")), self.value("password"))
        client.on_message = lambda _c, _u, msg: self.on_message(msg.topic, msg.payload)
        try:
            await asyncio.to_thread(
                client.connect, str(self.value("host")), int(self.value("port", 1883)), 60
            )
        except OSError as exc:
            raise AdapterError(f"MQTT-Broker nicht erreichbar: {exc}") from exc
        for key in TOPIC_FIELDS:
            if self.value(key):
                client.subscribe(str(self.value(key)))
        client.loop_start()
        self._client = client
        self.connected = True

    async def read_live(self) -> LiveSnapshot:
        if self._client is None:
            await self.connect()
        with self._lock:
            if not self._values:
                raise AdapterError("Noch keine MQTT-Nachrichten empfangen")
            if time.time() - self._last_msg > 300:
                raise AdapterError("Seit 5 Minuten keine MQTT-Nachrichten")
            return LiveSnapshot(**self._values)

    async def close(self) -> None:
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
        self.connected = False
