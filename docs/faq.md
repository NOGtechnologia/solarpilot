# FAQ

**Brauche ich eine eigene Anlage zum Ausprobieren?**
Nein – „Demo starten“ legt eine simulierte 10-kWp-Anlage mit Batterie und einem Jahr Historie an.

**Kostet etwas?**
Nein. Alle Standardquellen (Open-Meteo, Bright Sky, Energy-Charts, aWATTar, RSS) sind frei und ohne
Schlüssel nutzbar. Optional: Forecast.Solar-Key, Claude-API-Key für die KI-Zusammenfassung.

**Läuft das auf dem Raspberry Pi?**
Ja, Raspberry Pi 4/5 mit 64-Bit-OS. SQLite ist Standard, die Datenbank wächst um ca. 30–50 MB pro Jahr
und Anlage.

**Warum lokal statt Cloud?**
Schneller (10-s-Updates), funktioniert ohne Internet, kein Rate-Limit und keine Konto-Sperren.

**Wie werden Eigenverbrauch und Ersparnis berechnet?**
Eigenverbrauch = PV-Ertrag − Einspeisung. Autarkie = (Verbrauch − Netzbezug) / Verbrauch.
Ersparnis = Eigenverbrauch × Strompreis + Einspeisung × Vergütung. Preise in den Einstellungen bzw. pro Anlage.

**Wie genau ist die Prognose?**
Die Prognose nutzt die Einstrahlung auf die geneigte Modulfläche von Open-Meteo. Nach einigen Tagen
lernt SolarPilot einen Korrekturfaktor (Verschattung, Wechselrichter, Verschmutzung) und zeigt die
Genauigkeit der letzten 30 Tage an.

**Zwei Zähler am selben Hausanschluss?**
Pro Anlage genau **ein** Gerät mit Rolle „Netzzähler“. Andere Geräte liefern nur PV/Batterie.

**Daten nach Home Assistant?**
Einstellungen → Smart Home → MQTT aktivieren. Die Sensoren erscheinen automatisch (Auto-Discovery).

**Backup?**
Das Docker-Volume `solarpilot-data` sichern (enthält Datenbank und `secret.key`). Ohne `secret.key` können
gespeicherte Zugangsdaten nicht mehr entschlüsselt werden.
