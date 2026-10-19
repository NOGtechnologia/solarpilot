# Kostal Plenticore (Modbus TCP / SunSpec)

Kostal Plenticore plus / PIKO IQ über Modbus TCP mit SunSpec-Profil.

## Einrichtung

1. Im Webserver als Installateur: *Einstellungen → Modbus/SunSpec (TCP)* aktivieren.
   <!-- Screenshot Schritt 1: hier eigenes Bild aus docs/images/adapters/ einfügen -->
2. Port **1502**, Unit-ID **71**.
   <!-- Screenshot Schritt 2: hier eigenes Bild aus docs/images/adapters/ einfügen -->

## Fehlerbehebung

- **Zeitüberschreitung:** IP prüfen, Gerät im selben Netz? Firewall/VLAN?
- **Zugriff verweigert:** Zugangsdaten bzw. Token prüfen.
- **Werte falsch herum:** Vorzeichen-Optionen nutzen (siehe oben).
- Weiter: [FAQ](../faq.md) · [Fehlerbehebung](../troubleshooting.md)
