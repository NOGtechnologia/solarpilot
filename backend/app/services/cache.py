"""TTL-Cache mit „letztem guten Stand“ in der DB (bei Ausfall nicht leer anzeigen)."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from app.db import new_session

from .settings_store import get_value, set_value

log = logging.getLogger(__name__)

_mem: dict[str, tuple[float, Any]] = {}
_locks: dict[str, asyncio.Lock] = {}


def clear() -> None:
    _mem.clear()


async def cached(
    key: str, ttl_s: float, fetch: Callable[[], Awaitable[Any]], persist: bool = True
) -> dict[str, Any]:
    """Gibt ``{"data", "fetched_at", "stale", "error"}`` zurück."""
    now = time.time()
    hit = _mem.get(key)
    if hit and now - hit[0] < ttl_s:
        return {"data": hit[1], "fetched_at": int(hit[0]), "stale": False, "error": None}
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        hit = _mem.get(key)
        if hit and time.time() - hit[0] < ttl_s:
            return {"data": hit[1], "fetched_at": int(hit[0]), "stale": False, "error": None}
        try:
            data = await fetch()
        except Exception as exc:  # noqa: BLE001
            log.warning("Quelle %s nicht verfügbar: %s", key, exc)
            fallback = hit
            if fallback is None and persist:
                with new_session() as s:
                    stored = get_value(s, f"cache:{key}")
                if stored:
                    fallback = (stored["fetched_at"], stored["data"])
                    _mem[key] = (0.0, stored["data"])  # erneut versuchen beim nächsten Aufruf
            if fallback is None:
                return {"data": None, "fetched_at": None, "stale": True, "error": str(exc)}
            return {
                "data": fallback[1],
                "fetched_at": int(fallback[0]) or None,
                "stale": True,
                "error": str(exc),
            }
        ts = time.time()
        _mem[key] = (ts, data)
        if persist:
            with new_session() as s:
                set_value(s, f"cache:{key}", {"fetched_at": int(ts), "data": data})
        return {"data": data, "fetched_at": int(ts), "stale": False, "error": None}
