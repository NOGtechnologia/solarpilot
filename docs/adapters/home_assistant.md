# Home Assistant (Sensoren)

Liest beliebige Sensoren aus Home Assistant – fängt alle Geräte ab, für die es dort schon eine Integration gibt.

## Einrichtung

1. In Home Assistant: *Profil → Sicherheit → Langlebige Zugriffstokens* → Token erstellen.
   <!-- Screenshot Schritt 1: hier eigenes Bild aus docs/images/adapters/ einfügen -->
2. URL (z. B. `http://homeassistant.local:8123`) und Token eintragen.
   <!-- Screenshot Schritt 2: hier eigenes Bild aus docs/images/adapters/ einfügen -->
3. Entity-IDs der Sensoren angeben, z. B. `sensor.pv_power`. Einheiten W/kW/Wh/kWh werden umgerechnet.
   <!-- Screenshot Schritt 3: hier eigenes Bild aus docs/images/adapters/ einfügen -->

## Hinweise

Netz + = Bezug, − = Einspeisung; Batterie + = Laden – ggf. per Template-Sensor in HA anpassen.

## Fehlerbehebung

- **Zeitüberschreitung:** IP prüfen, Gerät im selben Netz? Firewall/VLAN?
- **Zugriff verweigert:** Zugangsdaten bzw. Token prüfen.
- **Werte falsch herum:** Vorzeichen-Optionen nutzen (siehe oben).
- Weiter: [FAQ](../faq.md) · [Fehlerbehebung](../troubleshooting.md)
