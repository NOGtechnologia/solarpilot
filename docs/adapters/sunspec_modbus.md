# SunSpec Modbus TCP (generisch)

Liest die SunSpec-Modelle 1 (Gerät), 101–103 (Wechselrichter), 160 (MPPT/Strings), 124 (Speicher-SoC) und 201–204 (Zähler). Funktioniert mit vielen Herstellern (SMA, SolarEdge, Kostal, Fronius, Sungrow u. a.).

## Einrichtung

1. Modbus TCP im Wechselrichter aktivieren (Webinterface oder Installateursmenü).
   <!-- Screenshot Schritt 1: hier eigenes Bild aus docs/images/adapters/ einfügen -->
2. IP-Adresse des Wechselrichters notieren und am Router fest vergeben.
   <!-- Screenshot Schritt 2: hier eigenes Bild aus docs/images/adapters/ einfügen -->
3. Im Assistenten Host, Port (meist 502) und Unit-ID eintragen.
   <!-- Screenshot Schritt 3: hier eigenes Bild aus docs/images/adapters/ einfügen -->
4. „Verbindung testen“ – es werden Leistung, SoC und Zählerwert angezeigt.
   <!-- Screenshot Schritt 4: hier eigenes Bild aus docs/images/adapters/ einfügen -->
5. Falls Einspeisung als Bezug erscheint: „Vorzeichen Netz umkehren“ aktivieren.
   <!-- Screenshot Schritt 5: hier eigenes Bild aus docs/images/adapters/ einfügen -->

## Konfiguration

| Feld | Beispiel |
| --- | --- |
| host | 192.168.1.50 |
| port | 502 |
| unit_id | 1 |

## Hinweise

Basisadresse wird automatisch gesucht (40000, 0, 50000). Hat der Zähler eine eigene Unit-ID, diese unter „Unit-ID Zähler“ eintragen.

## Fehlerbehebung

- **Zeitüberschreitung:** IP prüfen, Gerät im selben Netz? Firewall/VLAN?
- **Zugriff verweigert:** Zugangsdaten bzw. Token prüfen.
- **Werte falsch herum:** Vorzeichen-Optionen nutzen (siehe oben).
- Weiter: [FAQ](../faq.md) · [Fehlerbehebung](../troubleshooting.md)
