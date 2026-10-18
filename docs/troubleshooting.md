# Fehlerbehebung

| Problem | Lösung |
| --- | --- |
| Dashboard zeigt „Verbinde …“ dauerhaft | WebSocket blockiert (Reverse-Proxy). `Upgrade`/`Connection`-Header für `/api/ws` weiterleiten – siehe `frontend/nginx.conf`. Die Werte kommen dann per Polling alle 10 s. |
| Gerät „offline seit …“ | IP geändert? Am Router feste IP vergeben. Modbus nur einmal gleichzeitig erlaubt (Huawei!). In den Einstellungen steht die letzte Fehlermeldung. |
| Einspeisung erscheint als Bezug | Im Gerät „Vorzeichen umkehren“ aktivieren. |
| Doppelter Verbrauch in der Summenansicht | Pro Anlage nur ein Netzzähler; der Hausverbrauch wird aus PV + Netz − Batterie berechnet. |
| Keine Prognose | Modulfelder (kWp, Neigung, Ausrichtung) in der Anlage hinterlegen. Internetzugang des Containers prüfen. |
| Keine Strompreise | Preise für morgen gibt es ab ca. 13–14 Uhr. Es wird stündlich erneut versucht. |
| Zugangsdaten „konnten nicht entschlüsselt werden“ | `secret.key` bzw. `SOLARPILOT_SECRET_KEY` hat sich geändert. Altes Secret wiederherstellen oder Zugangsdaten neu eingeben. |
| Passwort vergessen | `docker compose exec -it backend python -m app.cli reset-password admin` (bzw. dein Benutzername) – fragt das neue Passwort ab. |

Logs ansehen:

```bash
docker compose logs -f backend
```

API-Dokumentation (OpenAPI) im laufenden System: `http://<host>:8080/api/docs`.
