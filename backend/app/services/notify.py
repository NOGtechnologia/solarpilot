"""Benachrichtigungen per ntfy, Telegram und E-Mail (bei Störung, Minderertrag, Überschuss)."""

from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

from .http import client

log = logging.getLogger(__name__)


async def send_ntfy(cfg: dict[str, Any], title: str, body: str, tags: str = "sunny") -> None:
    # JSON-Publishing an die Basis-URL: Titel mit Umlauten ohne Header-Kodierungsprobleme
    url = cfg.get("url", "https://ntfy.sh").rstrip("/") + "/"
    payload = {
        "topic": str(cfg["topic"]).strip("/"),
        "title": title,
        "message": body,
        "tags": [tags],
    }
    headers = {"Authorization": f"Bearer {cfg['token']}"} if cfg.get("token") else {}
    async with client() as c:
        r = await c.post(url, json=payload, headers=headers)
        r.raise_for_status()


async def send_telegram(cfg: dict[str, Any], title: str, body: str) -> None:
    url = f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage"
    async with client() as c:
        r = await c.post(url, json={"chat_id": cfg["chat_id"], "text": f"{title}\n\n{body}"})
        r.raise_for_status()


def _send_mail_sync(cfg: dict[str, Any], title: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = title
    msg["From"] = cfg.get("from_addr") or cfg.get("username")
    msg["To"] = cfg["to_addr"]
    msg.set_content(body)
    port = int(cfg.get("port") or 587)
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(cfg["host"], port, context=ctx, timeout=20) as s:
            if cfg.get("username"):
                s.login(cfg["username"], cfg.get("password", ""))
            s.send_message(msg)
    else:
        with smtplib.SMTP(cfg["host"], port, timeout=20) as s:
            if cfg.get("starttls", True):
                s.starttls(context=ctx)
            if cfg.get("username"):
                s.login(cfg["username"], cfg.get("password", ""))
            s.send_message(msg)


async def send_email(cfg: dict[str, Any], title: str, body: str) -> None:
    await asyncio.to_thread(_send_mail_sync, cfg, title, body)


CHANNELS = {
    "ntfy": (send_ntfy, ("topic",)),
    "telegram": (send_telegram, ("bot_token", "chat_id")),
    "email": (send_email, ("host", "to_addr")),
}


def enabled_channels(cfg: dict[str, Any]) -> list[str]:
    out = []
    for name, (_, required) in CHANNELS.items():
        ch = cfg.get(name) or {}
        if ch.get("enabled") and all(ch.get(k) for k in required):
            out.append(name)
    return out


async def send(
    cfg: dict[str, Any], title: str, body: str, only: str | None = None
) -> dict[str, str]:
    """Sendet an alle aktiven Kanäle (oder nur ``only``). Rückgabe: Kanal → "ok"/Fehler."""
    results: dict[str, str] = {}
    names = [only] if only else enabled_channels(cfg)
    for name in names:
        fn, _ = CHANNELS[name]
        try:
            await fn(cfg[name], title, body)
            results[name] = "ok"
        except Exception as exc:  # noqa: BLE001
            msg = redact(str(exc), cfg.get(name) or {})
            log.warning("Benachrichtigung über %s fehlgeschlagen: %s", name, msg)
            results[name] = msg
    return results


SECRET_KEYS = ("bot_token", "token", "password")


def redact(text: str, channel_cfg: dict[str, Any]) -> str:
    """Entfernt Zugangsdaten aus Fehlermeldungen (z. B. Telegram-Token in der URL)."""
    for key in SECRET_KEYS:
        value = channel_cfg.get(key)
        if value and isinstance(value, str) and len(value) >= 4:
            text = text.replace(value, "***")
    return text


TEXTS = {
    "de": {
        "insight.offline": ("Gerät offline", "{device} antwortet nicht. {error}"),
        "insight.underperformance": (
            "Minderertrag erkannt",
            "{site}: Ertrag nur {ratio_pct} % der Prognose an {days} sonnigen Tagen. "
            "Module verschmutzt oder String defekt?",
        ),
        "insight.surplus": (
            "Solarüberschuss",
            "{site}: ca. {kw} kW Überschuss erwartet – jetzt große Verbraucher einschalten.",
        ),
        "daily_summary": ("Tageszusammenfassung", "{text}"),
    },
    "en": {
        "insight.offline": ("Device offline", "{device} is not responding. {error}"),
        "insight.underperformance": (
            "Low yield detected",
            "{site}: yield only {ratio_pct} % of forecast on {days} sunny days. "
            "Dirty panels or faulty string?",
        ),
        "insight.surplus": (
            "Solar surplus",
            "{site}: about {kw} kW surplus expected – a good time for big appliances.",
        ),
        "daily_summary": ("Daily summary", "{text}"),
    },
}


def render(key: str, params: dict[str, Any], lang: str = "de") -> tuple[str, str]:
    title, body = TEXTS.get(lang, TEXTS["de"]).get(key, (key, ""))

    class _Safe(dict):
        def __missing__(self, k: str) -> str:
            return ""

    return title, body.format_map(_Safe({k: ("" if v is None else v) for k, v in params.items()}))
