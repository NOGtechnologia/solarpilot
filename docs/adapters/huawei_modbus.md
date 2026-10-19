# Huawei SUN2000 (Modbus TCP)

Über den SDongle (empfohlen) oder den internen WLAN-AP des Wechselrichters.

## Einrichtung

1. In der FusionSolar-App: *Geräteinbetriebnahme → Einstellungen → Kommunikationskonfiguration → Dongle-Parametereinstellungen → Modbus TCP* → **Aktivieren (uneingeschränkt)**.
   <!-- Screenshot Schritt 1: hier eigenes Bild aus docs/images/adapters/ einfügen -->
2. Port 502, Unit-ID meist 1 (bei manchen Firmwares 0 oder 16).
   <!-- Screenshot Schritt 2: hier eigenes Bild aus docs/images/adapters/ einfügen -->
3. „Smart Meter vorhanden“ und ggf. „Batterie vorhanden“ setzen.
   <!-- Screenshot Schritt 3: hier eigenes Bild aus docs/images/adapters/ einfügen -->

## Hinweise

Huawei erlaubt nur **eine** Modbus-Verbindung gleichzeitig – andere Tools (z. B. Home-Assistant-Integration) parallel führen zu Abbrüchen.

## Fehlerbehebung

- **Zeitüberschreitung:** IP prüfen, Gerät im selben Netz? Firewall/VLAN?
- **Zugriff verweigert:** Zugangsdaten bzw. Token prüfen.
- **Werte falsch herum:** Vorzeichen-Optionen nutzen (siehe oben).
- Weiter: [FAQ](../faq.md) · [Fehlerbehebung](../troubleshooting.md)
