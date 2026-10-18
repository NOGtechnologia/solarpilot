# Changelog

Alle relevanten Änderungen. Versionierung nach [SemVer](https://semver.org/lang/de/).

## [1.0.0] – 2026-10-18

Erste öffentliche Version.

### Neu

- **Dashboard:** animierter Energiefluss (PV, Haus, Batterie, Netz), Batterie als Flüssigkeit,
  Sonnenbogen, Farbverlauf nach Tageszeit/Wetter, KPI-Kacheln mit Count-up, Verlauf Tag/Woche/Monat/Jahr
  mit Prognoselinie, Live-Updates per WebSocket (Fallback Polling)
- **Mehrere Anlagen** mit Summenansicht, Einrichtungs-Assistent (Karte, Hersteller, Verbindungstest,
  Modulfelder), YAML-Import/-Export
- **Adapter:** Demo-Simulator, SunSpec Modbus (generisch, SMA, SolarEdge, Kostal), Fronius Solar API,
  Huawei SUN2000, Victron GX, Enphase IQ Gateway, GoodWe, OpenDTU, Shelly 3EM, MQTT, Home Assistant
- **Wetter & Prognose:** Open-Meteo (GTI je Modulfeld), optional Forecast.Solar, DWD-Warnungen über
  Bright Sky, Prognose-Genauigkeit und lernender Korrekturfaktor
- **Strompreise:** Energy-Charts mit Fallback aWATTar (DE-LU, AT), 15-Minuten-Auflösung
- **News:** konfigurierbare RSS-Feeds, dedupliziert, nur Titel/Quelle/Datum/Link/Teaser
- **Insights:** Überschuss-Zeitfenster, „Batterie voll um …“, E-Auto-Ladeplan, Minderertrag-Erkennung,
  Geräte offline, günstige/teure Strompreise; optionale KI-Tageszusammenfassung
- **Monatsreport** als Seite und PDF
- **Benachrichtigungen:** ntfy, Telegram, E-Mail · **MQTT** mit Home-Assistant-Auto-Discovery
- **PWA**, Hell-/Dunkelmodus, Deutsch/Englisch, Login, verschlüsselte Zugangsdaten
- Docker Compose, Multi-Arch-Image (amd64/arm64), CI mit Tests, E2E und gitleaks
