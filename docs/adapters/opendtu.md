# OpenDTU (Hoymiles / Balkonkraftwerk)

Für Hoymiles-/TSUN-Mikrowechselrichter mit OpenDTU (ESP32). Ideal für Balkonkraftwerke.

## Einrichtung

1. OpenDTU im Heimnetz einrichten (https://www.opendtu.solar).
   <!-- Screenshot Schritt 1: hier eigenes Bild aus docs/images/adapters/ einfügen -->
2. Im Assistenten die IP der OpenDTU eintragen – Lesen geht ohne Passwort.
   <!-- Screenshot Schritt 2: hier eigenes Bild aus docs/images/adapters/ einfügen -->

## Hinweise

AhoyDTU wird über den MQTT-Adapter unterstützt.

## Fehlerbehebung

- **Zeitüberschreitung:** IP prüfen, Gerät im selben Netz? Firewall/VLAN?
- **Zugriff verweigert:** Zugangsdaten bzw. Token prüfen.
- **Werte falsch herum:** Vorzeichen-Optionen nutzen (siehe oben).
- Weiter: [FAQ](../faq.md) · [Fehlerbehebung](../troubleshooting.md)
