# CLAUDE.md – SolarPilot

Projekt: **SolarPilot** – Open-Source-Dashboard für PV-Anlagen mehrerer Hersteller
(Live-Energiefluss, Wetter, PV-Prognose, Strompreise, News, smarte Tipps).

## Struktur

Monorepo:

- `backend/` – Python 3.12, FastAPI, SQLModel, APScheduler, pymodbus, httpx
  - `app/adapters/` – **alle** Hersteller-Anbindungen (eine Datei pro Adapter)
  - `app/services/` – Poller, Statistik, Wetter, Prognose, Preise, News, Insights, Reports, MQTT, Benachrichtigungen
  - `app/api/` – REST-Router und WebSocket (`/api/ws`)
  - `tests/` – pytest, aufgezeichnete Antworten in `tests/fixtures/`
- `frontend/` – Next.js (App Router, statischer Export), TypeScript, Tailwind v4, shadcn/ui-Stil, ECharts, Framer Motion
- `config/` – `news_feeds.yaml`, `sites.example.yaml`
- `docs/` – Design-System (`design.md`), Adapter-Anleitungen (`adapters/`), FAQ
- `docker-compose.yml`, `Dockerfile` (All-in-one-Image), `Makefile`

## Regeln

- Alle Hersteller-Anbindungen sind Adapter unter `backend/app/adapters/` und implementieren
  die Basisklasse `InverterAdapter` (`app/adapters/base.py`). Keine Herstellerlogik außerhalb.
  Registrierung über den Dekorator `@register` in `app/adapters/registry.py`.
- Einheitliches Format `LiveSnapshot`. Vorzeichen: `grid_power_w` + = Bezug, − = Einspeisung;
  `battery_power_w` + = Laden, − = Entladen. `load = pv + grid − battery`.
- Einheiten intern immer W, Wh, %, °C. Zeitstempel intern immer UTC (Unix-Sekunden in der DB),
  Anzeige in lokaler Zeit der Site.
- Keine Zugangsdaten im Code. Alles über `.env` oder Fernet-verschlüsselt in der DB
  (`app/crypto.py`). Secrets werden in API-Antworten nie im Klartext zurückgegeben.
- Pro Site genau ein Gerät mit Rolle `grid_meter`, damit nichts doppelt gezählt wird.
- Jede neue Funktion bekommt Tests (pytest / vitest). Externe APIs in Tests immer mit `respx` mocken.
- UI-Texte über i18n (`frontend/src/lib/i18n/`, de + en). Deutsch ist Standard.
- Farben haben Bedeutung (siehe `docs/design.md`): Solar Amber, Verbrauch Blau, Batterie Grün,
  Netzbezug Orange, Einspeisung Violett.
- Vor externen APIs immer aktuelle Doku per Websuche prüfen.
- News: nur Titel, Quelle, Datum, Link, kurzer Teaser – nie ganze Artikel.

## Befehle

```bash
make dev        # Backend :8000 + Frontend :3000
make test       # pytest + vitest
make lint       # ruff + tsc
make e2e        # Playwright gegen Backend mit statischem Frontend
docker compose up
```

Ohne `make` (Windows):

```bash
cd backend && pip install -e ".[dev]" && pytest
cd frontend && npm ci && npm run test && npm run build
```
