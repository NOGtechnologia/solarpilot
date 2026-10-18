# GoodWe (lokal, UDP)

ET/EH/BT/BH/ES/DT-Serien über das lokale UDP-Protokoll (Bibliothek `goodwe`).

## Einrichtung

1. Wechselrichter muss per WLAN/LAN im Heimnetz sein (WiFi/LAN-Kit).
   ![Screenshot Schritt 1](../images/adapters/goodwe_local-1.png)
2. Nur die IP eintragen; die Serie wird automatisch erkannt.
   ![Screenshot Schritt 2](../images/adapters/goodwe_local-2.png)

## Hinweise

Läuft SolarPilot in Docker, muss UDP-Port 8899 zum Wechselrichter erreichbar sein (Standard-Bridge-Netz genügt).

## Fehlerbehebung

- **Zeitüberschreitung:** IP prüfen, Gerät im selben Netz? Firewall/VLAN?
- **Zugriff verweigert:** Zugangsdaten bzw. Token prüfen.
- **Werte falsch herum:** Vorzeichen-Optionen nutzen (siehe oben).
- Weiter: [FAQ](../faq.md) · [Fehlerbehebung](../troubleshooting.md)
