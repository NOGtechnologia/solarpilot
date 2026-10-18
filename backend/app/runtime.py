"""Laufzeit-Objekte der App (Poller, WebSocket-Hub, MQTT) – über ``request.app.state.rt``."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from fastapi import Request, WebSocket

from .services.mqtt_out import MqttPublisher
from .services.poller import Poller

log = logging.getLogger(__name__)


@dataclass
class WsHub:
    clients: set[WebSocket] = field(default_factory=set)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        if not self.clients:
            return
        text = json.dumps(payload)
        dead = []
        for ws in list(self.clients):
            try:
                await asyncio.wait_for(ws.send_text(text), 5)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)


@dataclass
class Runtime:
    poller: Poller
    hub: WsHub = field(default_factory=WsHub)
    mqtt: MqttPublisher = field(default_factory=MqttPublisher)
    insights_sent: set[str] = field(default_factory=set)


def get_rt(request: Request) -> Runtime:
    return request.app.state.rt
