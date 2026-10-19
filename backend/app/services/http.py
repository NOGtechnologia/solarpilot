"""Gemeinsamer HTTP-Client für externe Dienste (Wetter, Preise, News, Benachrichtigungen)."""

from __future__ import annotations

import httpx

from app import __version__

USER_AGENT = f"SolarPilot/{__version__} (+https://github.com/NOGtechnologia/solarpilot)"


def client(timeout: float = 15.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=timeout, headers={"User-Agent": USER_AGENT}, follow_redirects=True
    )
