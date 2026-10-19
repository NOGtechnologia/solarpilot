# Victron GX (Modbus TCP)

Cerbo GX, Venus GX und andere GX-Geräte. Liest die Systemwerte (PV, Verbrauch, Netz, Batterie).

## Einrichtung

1. Auf dem GX: *Einstellungen → Dienste → Modbus TCP* → **Aktiviert**.
   <!-- Screenshot Schritt 1: hier eigenes Bild aus docs/images/adapters/ einfügen -->
2. Unit-ID **100** (com.victronenergy.system).
   <!-- Screenshot Schritt 2: hier eigenes Bild aus docs/images/adapters/ einfügen -->

## Hinweise

Alternativ funktioniert auch der MQTT-Adapter mit dem eingebauten MQTT-Broker des GX.

## Fehlerbehebung

- **Zeitüberschreitung:** IP prüfen, Gerät im selben Netz? Firewall/VLAN?
- **Zugriff verweigert:** Zugangsdaten bzw. Token prüfen.
- **Werte falsch herum:** Vorzeichen-Optionen nutzen (siehe oben).
- Weiter: [FAQ](../faq.md) · [Fehlerbehebung](../troubleshooting.md)
