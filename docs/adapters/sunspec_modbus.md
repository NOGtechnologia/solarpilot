# SunSpec Modbus TCP (generisch)

Liest die SunSpec-Modelle 1 (Gerät), 101–103 (Wechselrichter), 160 (MPPT/Strings), 124 (Speicher-SoC) und 201–204 (Zähler). Funktioniert mit vielen Herstellern (SMA, SolarEdge, Kostal, Fronius, Sungrow u. a.).

## Einrichtung

1. Modbus TCP im Wechselrichter aktivieren (Webinterface oder Installateursmenü).
   ![Screenshot Schritt 1](../images/adapters/sunspec_modbus-1.png)
2. IP-Adresse des Wechselrichters notieren und am Router fest vergeben.
   ![Screenshot Schritt 2](../images/adapters/sunspec_modbus-2.png)
3. Im Assistenten Host, Port (meist 502) und Unit-ID eintragen.
   ![Screenshot Schritt 3](../images/adapters/sunspec_modbus-3.png)
4. „Verbindung testen“ – es werden Leistung, SoC und Zählerwert angezeigt.
   ![Screenshot Schritt 4](../images/adapters/sunspec_modbus-4.png)
5. Falls Einspeisung als Bezug erscheint: „Vorzeichen Netz umkehren“ aktivieren.
   ![Screenshot Schritt 5](../images/adapters/sunspec_modbus-5.png)

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
