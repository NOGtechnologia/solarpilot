"""Fragt alle Geräte unabhängig voneinander ab, fasst zusammen und speichert Mittelwerte.

* Abfrage alle ``poll_interval_s`` (Standard 10 s), Speichern alle ``store_interval_s`` (60 s)
* Fällt ein Gerät aus, laufen die anderen weiter (Backoff bis 5 min, „offline seit …“)
* Cloud-Adapter werden nie öfter als ``min_poll_interval_s`` abgefragt
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session, select

from app.adapters.base import AdapterError, InverterAdapter, LiveSnapshot, SiteContext
from app.adapters.registry import get_adapter_class
from app.crypto import decrypt_json
from app.db import new_session
from app.models import Device, Measurement, Site

from .aggregate import aggregate_all, aggregate_site, average_snapshots
from .stats import compute_day
from .timeutil import local_today

log = logging.getLogger(__name__)

Listener = Callable[[dict[str, Any]], Awaitable[None] | None]


def site_context(site: Site) -> SiteContext:
    kwp = sum(float(a.get("kwp") or 0) for a in site.arrays or []) or 10.0
    return SiteContext(
        lat=site.lat, lon=site.lon, timezone=site.timezone, kwp=kwp, battery_kwh=site.battery_kwh
    )


def build_adapter(device: Device, site: Site) -> InverterAdapter:
    cls = get_adapter_class(device.type)
    return cls(
        config=device.config, secrets=decrypt_json(device.secrets_enc), site=site_context(site)
    )


def _fingerprint(device: Device, site: Site) -> str:
    raw = json.dumps(
        [
            device.type,
            device.config,
            device.secrets_enc,
            device.role,
            site.lat,
            site.lon,
            site.timezone,
            site.arrays,
        ],
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class DeviceRuntime:
    device_id: int
    site_id: int
    name: str
    type: str
    role: str
    adapter: InverterAdapter
    fingerprint: str
    snapshot: LiveSnapshot | None = None
    last_seen: float | None = None
    error: str | None = None
    fails: int = 0
    next_poll: float = 0.0
    online: bool = False

    def status(self) -> dict[str, Any]:
        return {
            "id": self.device_id,
            "site_id": self.site_id,
            "name": self.name,
            "type": self.type,
            "role": self.role,
            "online": self.online,
            "last_seen": int(self.last_seen) if self.last_seen else None,
            "error": self.error,
            "snapshot": self.snapshot.model_dump(mode="json") if self.snapshot else None,
        }


@dataclass
class Poller:
    poll_interval_s: float = 10.0
    store_interval_s: int = 60
    timeout_s: float = 8.0
    runtimes: dict[int, DeviceRuntime] = field(default_factory=dict)
    sites: dict[int, Site] = field(default_factory=dict)
    site_snapshots: dict[int, LiveSnapshot] = field(default_factory=dict)
    samples: dict[tuple[int, int | None], list[LiveSnapshot]] = field(
        default_factory=lambda: defaultdict(list)
    )
    listeners: list[Listener] = field(default_factory=list)
    last_store: float = field(default_factory=time.time)
    _task: asyncio.Task | None = None
    _reload_event: asyncio.Event = field(default_factory=asyncio.Event)

    # --- Verwaltung -------------------------------------------------------------
    async def reload(self) -> None:
        with new_session() as session:
            sites = {s.id: s for s in session.exec(select(Site)).all()}
            devices = session.exec(select(Device).where(Device.enabled == True)).all()  # noqa: E712
        self.sites = sites  # type: ignore[assignment]
        seen: set[int] = set()
        for dev in devices:
            site = sites.get(dev.site_id)
            if site is None or dev.id is None:
                continue
            seen.add(dev.id)
            fp = _fingerprint(dev, site)
            rt = self.runtimes.get(dev.id)
            if rt and rt.fingerprint == fp:
                rt.name = dev.name
                continue
            if rt:
                await self._close(rt)
            try:
                adapter = build_adapter(dev, site)
            except (KeyError, ValueError) as exc:
                log.warning("Gerät %s: %s", dev.name, exc)
                continue
            self.runtimes[dev.id] = DeviceRuntime(
                device_id=dev.id,
                site_id=dev.site_id,
                name=dev.name,
                type=dev.type,
                role=dev.role,
                adapter=adapter,
                fingerprint=fp,
            )
        for dev_id in list(self.runtimes):
            if dev_id not in seen:
                await self._close(self.runtimes.pop(dev_id))
        for sid in list(self.site_snapshots):
            if sid not in self.sites:
                self.site_snapshots.pop(sid, None)

    def request_reload(self) -> None:
        self._reload_event.set()

    async def _close(self, rt: DeviceRuntime) -> None:
        try:
            await rt.adapter.close()
        except Exception:  # noqa: BLE001
            log.debug("Schließen fehlgeschlagen", exc_info=True)

    # --- Abfrage ----------------------------------------------------------------
    async def _poll_device(self, rt: DeviceRuntime, now: float) -> None:
        try:
            if not rt.adapter.connected:
                await asyncio.wait_for(rt.adapter.connect(), self.timeout_s)
            snap = await asyncio.wait_for(rt.adapter.read_live(), self.timeout_s)
            rt.snapshot = snap
            rt.last_seen = now
            rt.error = None
            rt.fails = 0
            rt.online = True
            interval = max(self.poll_interval_s, rt.adapter.min_poll_interval_s)
            rt.next_poll = now + interval
        except Exception as exc:  # noqa: BLE001 - jedes Gerät isoliert
            rt.fails += 1
            rt.online = False
            if isinstance(exc, AdapterError):
                rt.error = str(exc)
            elif isinstance(exc, TimeoutError):
                rt.error = "Zeitüberschreitung"
            else:
                rt.error = f"{type(exc).__name__}: {exc}"
            backoff = min(self.poll_interval_s * (2 ** min(rt.fails, 6)), 300)
            rt.next_poll = now + max(backoff, rt.adapter.min_poll_interval_s)
            await self._close(rt)
            if rt.fails in (1, 5):
                log.warning("Gerät %s nicht erreichbar: %s", rt.name, rt.error)

    async def poll_once(self) -> dict[str, Any]:
        now = time.time()
        due = [rt for rt in self.runtimes.values() if rt.next_poll <= now]
        await asyncio.gather(*(self._poll_device(rt, now) for rt in due))
        stale = now - max(3 * self.poll_interval_s, 60)
        by_site: dict[int, list[tuple[str, LiveSnapshot]]] = defaultdict(list)
        for rt in self.runtimes.values():
            if rt.snapshot and rt.last_seen and rt.last_seen >= stale and rt.online:
                by_site[rt.site_id].append((rt.role, rt.snapshot))
                if rt in due:
                    self.samples[(rt.site_id, rt.device_id)].append(rt.snapshot)
            elif rt.last_seen and rt.last_seen < stale:
                rt.online = False
        for site_id in self.sites:
            if by_site.get(site_id):
                snap = aggregate_site(by_site[site_id])
                self.site_snapshots[site_id] = snap
                if due:
                    self.samples[(site_id, None)].append(snap)
            else:
                self.site_snapshots.pop(site_id, None)
        payload = self.live_payload()
        await self._notify(payload)
        return payload

    def live_payload(self) -> dict[str, Any]:
        sites = {str(k): v.model_dump(mode="json") for k, v in self.site_snapshots.items()}
        total = aggregate_all(list(self.site_snapshots.values())) if self.site_snapshots else None
        return {
            "type": "live",
            "ts": int(time.time()),
            "all": total.model_dump(mode="json") if total else None,
            "sites": sites,
            "devices": [rt.status() for rt in self.runtimes.values()],
        }

    async def _notify(self, payload: dict[str, Any]) -> None:
        for fn in list(self.listeners):
            try:
                res = fn(payload)
                if asyncio.iscoroutine(res):
                    await res
            except Exception:  # noqa: BLE001
                log.debug("Listener-Fehler", exc_info=True)

    # --- Speichern --------------------------------------------------------------
    def store(self, now: float | None = None) -> int:
        now = now or time.time()
        dt = int(min(max(now - self.last_store, 1), 600))
        self.last_store = now
        samples, self.samples = self.samples, defaultdict(list)
        if not samples:
            return 0
        ts = int(now)
        rows = []
        touched: set[int] = set()
        last_seen: dict[int, int] = {}
        for (site_id, device_id), snaps in samples.items():
            if not snaps or site_id not in self.sites:
                continue
            avg = average_snapshots(snaps)
            rows.append(
                Measurement(
                    site_id=site_id,
                    device_id=device_id,
                    ts=ts,
                    dt_s=dt,
                    pv_w=avg.pv_power_w,
                    load_w=avg.load_power_w,
                    grid_w=avg.grid_power_w,
                    battery_w=avg.battery_power_w,
                    soc_pct=avg.battery_soc_pct,
                    energy_today_wh=avg.energy_today_wh,
                )
            )
            if device_id is None:
                touched.add(site_id)
            else:
                last_seen[device_id] = int(snaps[-1].timestamp_utc.timestamp())
        with new_session() as session:
            session.add_all(rows)
            for dev_id, seen in last_seen.items():
                dev = session.get(Device, dev_id)
                if dev:
                    dev.last_seen = seen
                    rt = self.runtimes.get(dev_id)
                    dev.last_error = rt.error if rt else None
                    session.add(dev)
            session.commit()
            for site_id in touched:
                site = session.get(Site, site_id)
                if site:
                    compute_day(session, site, local_today(site.timezone))
        return len(rows)

    # --- Hintergrundschleife ----------------------------------------------------
    async def run(self) -> None:
        await self.reload()
        while True:
            started = time.time()
            if self._reload_event.is_set():
                self._reload_event.clear()
                await self.reload()
            try:
                await self.poll_once()
                if time.time() - self.last_store >= self.store_interval_s:
                    await asyncio.to_thread(self.store)
            except Exception:  # noqa: BLE001
                log.exception("Poller-Fehler")
            delay = max(self.poll_interval_s - (time.time() - started), 0.5)
            try:
                await asyncio.wait_for(self._reload_event.wait(), delay)
            except TimeoutError:
                pass

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self.run(), name="poller")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._task = None
        if self.samples:
            await asyncio.to_thread(self.store)
        for rt in self.runtimes.values():
            await self._close(rt)


def snapshot_age(snapshot: dict | None) -> float | None:
    if not snapshot:
        return None
    ts = datetime.fromisoformat(snapshot["timestamp_utc"])
    return (datetime.now(UTC) - ts).total_seconds()


def session_sites(session: Session, site: str | int | None) -> list[Site]:
    """``site`` = "all"/None → alle Sites, sonst eine ID."""
    if site in (None, "", "all"):
        return list(session.exec(select(Site).order_by(Site.id)).all())
    s = session.get(Site, int(site))
    return [s] if s else []
