# Kostal Plenticore (Modbus TCP / SunSpec)

Kostal Plenticore plus / PIKO IQ über Modbus TCP mit SunSpec-Profil.

## Einrichtung

1. Im Webserver als Installateur: *Einstellungen → Modbus/SunSpec (TCP)* aktivieren.
   ![Screenshot Schritt 1](../images/adapters/kostal-1.png)
2. Port **1502**, Unit-ID **71**.
   ![Screenshot Schritt 2](../images/adapters/kostal-2.png)

## Fehlerbehebung

- **Zeitüberschreitung:** IP prüfen, Gerät im selben Netz? Firewall/VLAN?
- **Zugriff verweigert:** Zugangsdaten bzw. Token prüfen.
- **Werte falsch herum:** Vorzeichen-Optionen nutzen (siehe oben).
- Weiter: [FAQ](../faq.md) · [Fehlerbehebung](../troubleshooting.md)
