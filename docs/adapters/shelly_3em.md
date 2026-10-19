# Shelly 3EM / Pro 3EM (Netzzähler)

Dreiphasiger Zähler am Hausanschluss – liefert Netzbezug/Einspeisung. Rolle: **Netzzähler**.

## Einrichtung

1. Shelly ins WLAN bringen und IP fest vergeben.
   <!-- Screenshot Schritt 1: hier eigenes Bild aus docs/images/adapters/ einfügen -->
2. Im Assistenten zur bestehenden Anlage hinzufügen, Rolle „Netzzähler“.
   <!-- Screenshot Schritt 2: hier eigenes Bild aus docs/images/adapters/ einfügen -->
3. Generation „auto“ erkennt Gen1 (`/status`) und Gen2+ (`/rpc/EM.GetStatus`).
   <!-- Screenshot Schritt 3: hier eigenes Bild aus docs/images/adapters/ einfügen -->

## Hinweise

Pro Anlage darf es nur **einen** Netzzähler geben, damit nichts doppelt gezählt wird.

## Fehlerbehebung

- **Zeitüberschreitung:** IP prüfen, Gerät im selben Netz? Firewall/VLAN?
- **Zugriff verweigert:** Zugangsdaten bzw. Token prüfen.
- **Werte falsch herum:** Vorzeichen-Optionen nutzen (siehe oben).
- Weiter: [FAQ](../faq.md) · [Fehlerbehebung](../troubleshooting.md)
