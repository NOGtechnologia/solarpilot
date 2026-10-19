# SolarEdge (Modbus TCP / SunSpec)

Lokal über Modbus TCP. Die Cloud-API ist stark limitiert (ca. 300 Abfragen/Tag) und daher nicht der Standard.

## Einrichtung

1. Modbus TCP aktivieren: über SetApp (*Kommunikation → Modbus TCP*) oder das Display.
   <!-- Screenshot Schritt 1: hier eigenes Bild aus docs/images/adapters/ einfügen -->
2. Port ist meist **1502** (neuere Geräte) oder 502.
   <!-- Screenshot Schritt 2: hier eigenes Bild aus docs/images/adapters/ einfügen -->
3. Unit-ID 1. Ein angeschlossener SolarEdge-Zähler wird automatisch erkannt (Modell 203).
   <!-- Screenshot Schritt 3: hier eigenes Bild aus docs/images/adapters/ einfügen -->

## Hinweise

Bei SolarEdge zeigt der Zähler je nach Einbauort Einspeisung positiv – dann „Vorzeichen Netz umkehren“ aktivieren.

## Fehlerbehebung

- **Zeitüberschreitung:** IP prüfen, Gerät im selben Netz? Firewall/VLAN?
- **Zugriff verweigert:** Zugangsdaten bzw. Token prüfen.
- **Werte falsch herum:** Vorzeichen-Optionen nutzen (siehe oben).
- Weiter: [FAQ](../faq.md) · [Fehlerbehebung](../troubleshooting.md)
