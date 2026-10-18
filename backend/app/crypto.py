"""Verschlüsselung von Zugangsdaten (Fernet) – Schlüssel wird aus dem App-Secret abgeleitet."""

from __future__ import annotations

import base64
import hashlib
import json
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from .config import get_settings


@lru_cache
def _fernet() -> Fernet:
    secret = get_settings().resolved_secret()
    key = base64.urlsafe_b64encode(hashlib.sha256(f"fernet:{secret}".encode()).digest())
    return Fernet(key)


def reset_cache() -> None:
    _fernet.cache_clear()


def encrypt_str(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_str(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Zugangsdaten konnten nicht entschlüsselt werden") from exc


def encrypt_json(data: dict[str, Any]) -> str:
    if not data:
        return ""
    return encrypt_str(json.dumps(data))


def decrypt_json(token: str | None) -> dict[str, Any]:
    if not token:
        return {}
    return json.loads(decrypt_str(token))
