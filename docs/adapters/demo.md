# Demo-Simulator

Simuliert eine 10-kWp-Anlage mit 10-kWh-Batterie anhand des echten Sonnenstands am Standort, mit zufälligen (aber reproduzierbaren) Wolken und typischen Haushaltsverbrauchern. Beim Start werden 7 Tage Minutenwerte und 400 Tage Tageswerte erzeugt.

## Einrichtung

1. Im Dashboard auf **„Demo starten“** klicken – fertig.
   ![Screenshot Schritt 1](../images/adapters/demo-1.png)
2. Alternativ `SOLARPILOT_DEMO=true` setzen; dann wird die Demo beim ersten Start angelegt.
   ![Screenshot Schritt 2](../images/adapters/demo-2.png)

## Hinweise

Keine Verbindung nötig.

## Fehlerbehebung

- **Zeitüberschreitung:** IP prüfen, Gerät im selben Netz? Firewall/VLAN?
- **Zugriff verweigert:** Zugangsdaten bzw. Token prüfen.
- **Werte falsch herum:** Vorzeichen-Optionen nutzen (siehe oben).
- Weiter: [FAQ](../faq.md) · [Fehlerbehebung](../troubleshooting.md)
