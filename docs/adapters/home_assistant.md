# Home Assistant (Sensoren)

Liest beliebige Sensoren aus Home Assistant – fängt alle Geräte ab, für die es dort schon eine Integration gibt.

## Einrichtung

1. In Home Assistant: *Profil → Sicherheit → Langlebige Zugriffstokens* → Token erstellen.
   ![Screenshot Schritt 1](../images/adapters/home_assistant-1.png)
2. URL (z. B. `http://homeassistant.local:8123`) und Token eintragen.
   ![Screenshot Schritt 2](../images/adapters/home_assistant-2.png)
3. Entity-IDs der Sensoren angeben, z. B. `sensor.pv_power`. Einheiten W/kW/Wh/kWh werden umgerechnet.
   ![Screenshot Schritt 3](../images/adapters/home_assistant-3.png)

## Hinweise

Netz + = Bezug, − = Einspeisung; Batterie + = Laden – ggf. per Template-Sensor in HA anpassen.

## Fehlerbehebung

- **Zeitüberschreitung:** IP prüfen, Gerät im selben Netz? Firewall/VLAN?
- **Zugriff verweigert:** Zugangsdaten bzw. Token prüfen.
- **Werte falsch herum:** Vorzeichen-Optionen nutzen (siehe oben).
- Weiter: [FAQ](../faq.md) · [Fehlerbehebung](../troubleshooting.md)
