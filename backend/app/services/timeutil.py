"""Zeit-Hilfen: lokale Tagesgrenzen einer Site in UTC-Sekunden."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo


def tz(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "Europe/Berlin")
    except Exception:  # noqa: BLE001
        return ZoneInfo("Europe/Berlin")


def local_today(tzname: str | None) -> date:
    return datetime.now(tz(tzname)).date()


def day_bounds(day: date, tzname: str | None) -> tuple[int, int]:
    z = tz(tzname)
    start = datetime(day.year, day.month, day.day, tzinfo=z)
    end = start + timedelta(days=1)
    # DST-sicher: lokale Mitternacht des Folgetags
    end = datetime(end.year, end.month, end.day, tzinfo=z)
    return int(start.timestamp()), int(end.timestamp())


def local_day_of(ts: int, tzname: str | None) -> date:
    return datetime.fromtimestamp(ts, UTC).astimezone(tz(tzname)).date()


def parse_day(value: str | None, tzname: str | None) -> date:
    if not value:
        return local_today(tzname)
    return date.fromisoformat(value)
