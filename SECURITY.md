# Sicherheit

## Unterstützte Versionen

| Version | Sicherheitsupdates |
| --- | --- |
| 1.x | ✅ |

## Lücke melden

Bitte **keine öffentlichen Issues** für Sicherheitslücken. Nutze stattdessen
[GitHub Security Advisories](../../security/advisories/new) („Report a vulnerability“).
Wir antworten in der Regel innerhalb von 7 Tagen.

## Sicherheitskonzept

- Login mit scrypt-gehashten Passwörtern, JWT im `httpOnly`-/`SameSite=Lax`-Cookie, Login-Rate-Limit
- Zugangsdaten von Geräten und Diensten werden **Fernet-verschlüsselt** in der Datenbank gespeichert und
  von der API nie im Klartext zurückgegeben
- Schlüssel aus `SOLARPILOT_SECRET_KEY` oder automatisch erzeugt in `/data/secret.key` (Dateirechte 600)
- Schreibende Endpunkte nur für Administratoren; Verbindungstests nur für Administratoren
- Container laufen als unprivilegierter Benutzer; nur Port 8080 wird veröffentlicht
- Sicherheits-Header (`nosniff`, `X-Frame-Options`, `Referrer-Policy`), API-Antworten `no-store`
- CI prüft mit `gitleaks` auf versehentlich eingecheckte Secrets

## Empfehlungen für den Betrieb

- SolarPilot **nicht direkt ins Internet** stellen – für Fernzugriff VPN (WireGuard, Tailscale) oder einen
  Reverse-Proxy mit TLS nutzen und dann `SOLARPILOT_COOKIE_SECURE=true` setzen
- Starkes Admin-Passwort, regelmäßige Updates (`docker compose pull && docker compose up -d`)
- Backup des Volumes `solarpilot-data` (enthält Datenbank **und** `secret.key`)
