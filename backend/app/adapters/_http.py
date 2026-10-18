"""HTTP-Hilfen für Adapter: gemeinsame Fehlerbehandlung und Timeouts."""

from __future__ import annotations

from typing import Any

import httpx

from .base import AdapterError

DEFAULT_TIMEOUT = 8.0


def base_url(host: str, scheme: str = "http") -> str:
    host = host.strip().rstrip("/")
    if host.startswith(("http://", "https://")):
        return host
    return f"{scheme}://{host}"


async def get_json(client: httpx.AsyncClient, url: str, **kwargs: Any) -> Any:
    try:
        r = await client.get(url, **kwargs)
    except httpx.TimeoutException as exc:
        raise AdapterError(f"Zeitüberschreitung bei {url}") from exc
    except httpx.HTTPError as exc:
        raise AdapterError(f"Keine Verbindung zu {url}: {exc}") from exc
    if r.status_code in (401, 403):
        raise AdapterError("Zugriff verweigert – Zugangsdaten prüfen")
    if r.status_code >= 400:
        raise AdapterError(f"HTTP {r.status_code} von {url}")
    try:
        return r.json()
    except ValueError as exc:
        raise AdapterError(f"Ungültige Antwort von {url}") from exc


def num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
