"""Basisklasse für HTTP-basierte Adapter (eigener oder injizierter httpx-Client)."""

from __future__ import annotations

import httpx

from .base import InverterAdapter


class HttpAdapter(InverterAdapter):
    verify_tls: bool = True

    def __init__(self, *args, client: httpx.AsyncClient | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._client = client
        self._own = client is None

    def make_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=8.0, verify=self.verify_tls)

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = self.make_client()
        return self._client

    async def connect(self) -> None:
        _ = self.client
        self.connected = True

    async def close(self) -> None:
        if self._client is not None and self._own:
            await self._client.aclose()
            self._client = None
        self.connected = False
