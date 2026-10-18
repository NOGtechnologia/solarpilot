"""Optionale KI-Zusammenfassung des Tages über die Claude API (abschaltbar, eigener API-Key).

Es werden nur aggregierte Kennzahlen und Schlagzeilen übertragen – keine Zugangsdaten,
keine Geräte-Adressen.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

log = logging.getLogger(__name__)

SYSTEM = (
    "Du bist der Assistent im PV-Dashboard SolarPilot. Fasse den Tag für die Besitzer der "
    "Anlage in 3–5 kurzen Sätzen zusammen: Ertrag und Eigenverbrauch, was die Prognose für "
    "morgen bedeutet, ein konkreter Tipp. Wenn Schlagzeilen übergeben werden, nenne höchstens "
    "eine relevante mit Quelle. Erfinde keine Zahlen, nutze nur die übergebenen Daten. "
    "Antworte in der Sprache, die im Feld 'language' steht."
)


async def daily_summary(
    api_key: str, model: str, facts: dict[str, Any], language: str = "de"
) -> str | None:
    client = anthropic.AsyncAnthropic(api_key=api_key, timeout=60.0)
    payload = json.dumps({"language": language, **facts}, ensure_ascii=False, default=str)
    try:
        response = await client.beta.messages.create(
            model=model,
            max_tokens=2000,
            system=SYSTEM,
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": payload}],
        )
    except anthropic.AuthenticationError:
        log.warning("KI-Zusammenfassung: API-Key ungültig")
        return None
    except anthropic.RateLimitError:
        log.warning("KI-Zusammenfassung: Rate-Limit erreicht")
        return None
    except anthropic.APIStatusError as exc:
        log.warning("KI-Zusammenfassung: API-Fehler %s", exc.status_code)
        return None
    except anthropic.APIConnectionError:
        log.warning("KI-Zusammenfassung: keine Verbindung")
        return None
    finally:
        await client.close()
    if response.stop_reason == "refusal":
        return None
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return text or None
