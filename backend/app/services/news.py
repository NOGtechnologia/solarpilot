"""Solar-News per RSS: nur Titel, Quelle, Datum, Link und kurzer Teaser (Urheberrecht!)."""

from __future__ import annotations

import asyncio
import calendar
import hashlib
import html
import logging
import re
import time
from pathlib import Path
from typing import Any

import feedparser
import yaml
from sqlmodel import Session, col, delete, select

from app.models import NewsItem

from .http import client

log = logging.getLogger(__name__)

TEASER_LEN = 220
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def load_feeds(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [f for f in data.get("feeds", []) if f.get("url")]


def clean_teaser(raw: str | None, limit: int = TEASER_LEN) -> str:
    if not raw:
        return ""
    text = WS_RE.sub(" ", html.unescape(TAG_RE.sub(" ", raw))).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",;:.-–") + " …"


def parse_feed(content: bytes | str, source: str, lang: str = "de") -> list[dict[str, Any]]:
    parsed = feedparser.parse(content)
    items = []
    for e in parsed.entries:
        link = e.get("link")
        title = clean_teaser(e.get("title"), 300)
        if not link or not title or not str(link).startswith(("http://", "https://")):
            continue
        tm = e.get("published_parsed") or e.get("updated_parsed")
        published = int(calendar.timegm(tm)) if tm else int(time.time())
        guid = e.get("id") or link
        items.append(
            {
                "guid": hashlib.sha256(str(guid).encode()).hexdigest()[:40],
                "title": title,
                "source": source,
                "link": link,
                "published": published,
                "teaser": clean_teaser(e.get("summary")),
                "lang": lang,
            }
        )
    return items


def _norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9äöüß]+", "", t.lower())[:80]


async def fetch_feeds(feeds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    async def one(c, f: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            r = await c.get(f["url"])
            r.raise_for_status()
            return parse_feed(r.content, f.get("name") or f["url"], f.get("lang", "de"))
        except Exception as exc:  # noqa: BLE001
            log.warning("Feed %s nicht ladbar: %s", f.get("url"), exc)
            return []

    async with client(timeout=20) as c:
        results = await asyncio.gather(*(one(c, f) for f in feeds))
    return [it for items in results for it in items]


async def refresh_news(session: Session, feeds: list[dict[str, Any]], keep: int = 300) -> int:
    # Erst alle Feeds laden, dann kurz schreiben (keine DB-Sperre während Netzwerkzugriffen)
    items = await fetch_feeds(feeds)
    new = 0
    existing_titles = {_norm_title(t) for t in session.exec(select(NewsItem.title)).all()}
    existing_guids = set(session.exec(select(NewsItem.guid)).all())
    for it in items:
        nt = _norm_title(it["title"])
        if nt in existing_titles or it["guid"] in existing_guids:
            continue
        session.add(NewsItem(**it))
        existing_titles.add(nt)
        existing_guids.add(it["guid"])
        new += 1
    session.commit()
    ids = session.exec(
        select(NewsItem.id).order_by(col(NewsItem.published).desc()).offset(keep)
    ).all()
    if ids:
        session.exec(delete(NewsItem).where(col(NewsItem.id).in_(ids)))  # type: ignore[call-overload]
        session.commit()
    return new


def latest_news(session: Session, limit: int = 30, lang: str | None = None) -> list[dict[str, Any]]:
    q = select(NewsItem).order_by(col(NewsItem.published).desc()).limit(limit)
    if lang:
        q = q.where(NewsItem.lang == lang)
    return [
        {
            "title": n.title,
            "source": n.source,
            "link": n.link,
            "published": n.published,
            "teaser": n.teaser,
            "lang": n.lang,
        }
        for n in session.exec(q).all()
    ]
