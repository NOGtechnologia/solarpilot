# Mitmachen bei SolarPilot

Danke, dass du helfen willst! Der größte Hebel sind **neue Hersteller-Adapter** und Rückmeldungen
von echten Anlagen.

## Entwicklungsumgebung

```bash
make install     # Python-venv + npm ci
make dev         # Backend :8000 + Frontend :3000 mit Hot-Reload
make test        # pytest + vitest
make lint        # ruff + tsc
make e2e         # Playwright gegen das gebaute Frontend
```

Regeln stehen in [`CLAUDE.md`](CLAUDE.md) – kurz: Herstellerlogik nur in `backend/app/adapters/`,
Einheiten W/Wh/%/°C, Zeitstempel UTC, keine Zugangsdaten im Code, UI-Texte in `de.ts` **und** `en.ts`,
jede Funktion mit Tests.

## So baust du einen neuen Adapter

1. **Doku recherchieren** – offizielle Registerliste bzw. API-Doku des Herstellers.
2. **Datei anlegen:** `backend/app/adapters/<name>.py`

   ```python
   from .base import Capabilities, ConfigField, InverterAdapter, LiveSnapshot, host_field
   from .registry import register

   @register
   class MeinAdapter(InverterAdapter):
       type_name = "hersteller_modbus"          # eindeutig, snake_case
       display_name = "Hersteller XY (Modbus TCP)"
       vendor = "Hersteller"
       connection = "local"                      # local | cloud
       status = "beta"
       default_role = "hybrid"                   # inverter | hybrid | battery | grid_meter | ...
       min_poll_interval_s = 0                   # Cloud-APIs: z. B. 300
       capabilities = Capabilities(pv=True, grid=True, battery=True, load=True)
       config_schema = [*host_field(502), ConfigField(name="token", label_de="Token",
                        label_en="Token", type="password", secret=True)]
       docs = "hersteller_modbus"

       async def read_live(self) -> LiveSnapshot:
           ...
           return LiveSnapshot(pv_power_w=..., grid_power_w=..., battery_power_w=...,
                               battery_soc_pct=..., energy_today_wh=...)
   ```

   **Vorzeichen:** `grid_power_w` + = Bezug, − = Einspeisung · `battery_power_w` + = Laden, − = Entladen.
   Fehler als `AdapterError("lesbare Meldung")` werfen. Für HTTP `HttpAdapter` aus `_httpadapter.py`
   nutzen, für Modbus `ModbusTcpReader` aus `_modbus.py`.
3. **Formular:** ergibt sich automatisch aus `config_schema` (Felder mit `secret=True` werden verschlüsselt).
4. **Tests:** `backend/tests/test_adapters.py` – mit aufgezeichneten, **anonymisierten** Antworten in
   `tests/fixtures/` (HTTP mit `respx`, Modbus mit `FakeRegisterReader`).
5. **Anleitung:** `docs/adapters/<name>.md` mit Schritt-für-Schritt-Anleitung und Screenshot-Platzhaltern.
6. **README-Tabelle** ergänzen (Status zunächst „beta“).

> Prompt-Vorlage für Claude Code: *„Neuer Adapter: <Hersteller> <Modell>, Verbindung <lokal Modbus TCP /
> Cloud-API>. Recherchiere die aktuelle offizielle Doku bzw. Registerliste. Implementiere
> backend/app/adapters/<name>.py nach InverterAdapter, mappe alle Werte auf LiveSnapshot (Vorzeichen:
> Netzbezug +, Einspeisung −). Tests mit aufgezeichneten Antworten und docs/adapters/<name>.md.“*

## Pull Requests

- Klein und thematisch fokussiert, mit Beschreibung *was* und *warum*
- `make lint test` muss grün sein
- **Keine** echten IP-Adressen, Seriennummern, Tokens oder Passwörter – auch nicht in Fixtures
- Commit-Nachrichten gern im Stil `feat(adapter): sungrow modbus`

## Verhaltenskodex

Es gilt der [Code of Conduct](CODE_OF_CONDUCT.md).
