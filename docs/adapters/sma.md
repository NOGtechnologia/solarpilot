# SMA (Modbus TCP / SunSpec)

Für SMA Sunny Tripower/Boy und Sunny Island mit aktivierter Modbus-Schnittstelle. Nutzt das SunSpec-Profil (Unit-ID 126).

## Einrichtung

1. Im SMA-Webinterface als Installateur anmelden → *Geräteparameter* → *Externe Kommunikation* → *Modbus* → **TCP-Server aktivieren**.
   <!-- Screenshot Schritt 1: hier eigenes Bild aus docs/images/adapters/ einfügen -->
2. Port 502 belassen.
   <!-- Screenshot Schritt 2: hier eigenes Bild aus docs/images/adapters/ einfügen -->
3. Im Assistenten „SMA (Modbus TCP / SunSpec)“ wählen, IP eintragen, Unit-ID **126**.
   <!-- Screenshot Schritt 3: hier eigenes Bild aus docs/images/adapters/ einfügen -->
4. Für den Netzbezug den SMA Energy Meter/Home Manager über einen separaten Zähler (z. B. Shelly) oder die SunSpec-Zählermodelle einbinden.
   <!-- Screenshot Schritt 4: hier eigenes Bild aus docs/images/adapters/ einfügen -->

## Hinweise

SMA liefert nachts teils `NaN`-Werte; diese werden als 0 W PV angezeigt.

## Fehlerbehebung

- **Zeitüberschreitung:** IP prüfen, Gerät im selben Netz? Firewall/VLAN?
- **Zugriff verweigert:** Zugangsdaten bzw. Token prüfen.
- **Werte falsch herum:** Vorzeichen-Optionen nutzen (siehe oben).
- Weiter: [FAQ](../faq.md) · [Fehlerbehebung](../troubleshooting.md)
