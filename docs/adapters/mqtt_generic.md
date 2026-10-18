# MQTT (generisch)

Für alles, was Werte per MQTT veröffentlicht: Tasmota-SML-Leseköpfe, evcc, Victron, AhoyDTU, eigene Skripte.

## Einrichtung

1. Broker-Host/Port und ggf. Benutzer/Passwort eintragen.
   ![Screenshot Schritt 1](../images/adapters/mqtt_generic-1.png)
2. Pro Messwert das Topic angeben (z. B. `tele/sml/SENSOR`).
   ![Screenshot Schritt 2](../images/adapters/mqtt_generic-2.png)
3. Bei JSON-Nachrichten den Schlüssel als Pfad angeben, z. B. `SML.Power`.
   ![Screenshot Schritt 3](../images/adapters/mqtt_generic-3.png)

## Hinweise

Vorzeichen: Netz + = Bezug, − = Einspeisung; Batterie + = Laden.

## Fehlerbehebung

- **Zeitüberschreitung:** IP prüfen, Gerät im selben Netz? Firewall/VLAN?
- **Zugriff verweigert:** Zugangsdaten bzw. Token prüfen.
- **Werte falsch herum:** Vorzeichen-Optionen nutzen (siehe oben).
- Weiter: [FAQ](../faq.md) · [Fehlerbehebung](../troubleshooting.md)
