# Shelly 3EM / Pro 3EM (Netzzähler)

Dreiphasiger Zähler am Hausanschluss – liefert Netzbezug/Einspeisung. Rolle: **Netzzähler**.

## Einrichtung

1. Shelly ins WLAN bringen und IP fest vergeben.
   ![Screenshot Schritt 1](../images/adapters/shelly_3em-1.png)
2. Im Assistenten zur bestehenden Anlage hinzufügen, Rolle „Netzzähler“.
   ![Screenshot Schritt 2](../images/adapters/shelly_3em-2.png)
3. Generation „auto“ erkennt Gen1 (`/status`) und Gen2+ (`/rpc/EM.GetStatus`).
   ![Screenshot Schritt 3](../images/adapters/shelly_3em-3.png)

## Hinweise

Pro Anlage darf es nur **einen** Netzzähler geben, damit nichts doppelt gezählt wird.

## Fehlerbehebung

- **Zeitüberschreitung:** IP prüfen, Gerät im selben Netz? Firewall/VLAN?
- **Zugriff verweigert:** Zugangsdaten bzw. Token prüfen.
- **Werte falsch herum:** Vorzeichen-Optionen nutzen (siehe oben).
- Weiter: [FAQ](../faq.md) · [Fehlerbehebung](../troubleshooting.md)
