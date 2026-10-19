# Fronius Solar API (lokal)

Einfachster Einstieg: Die Solar API v1 ist im Wechselrichter (Symo, Primo, Gen24, Tauro) eingebaut und braucht keinen Login.

## Einrichtung

1. Prüfen: Im Browser `http://<IP>/solar_api/v1/GetPowerFlowRealtimeData.fcgi` öffnen – es muss JSON erscheinen.
   <!-- Screenshot Schritt 1: hier eigenes Bild aus docs/images/adapters/ einfügen -->
2. Bei Gen24: *Kommunikation → Solar API* ggf. aktivieren.
   <!-- Screenshot Schritt 2: hier eigenes Bild aus docs/images/adapters/ einfügen -->
3. Im Assistenten nur die IP eintragen.
   <!-- Screenshot Schritt 3: hier eigenes Bild aus docs/images/adapters/ einfügen -->

## Hinweise

Die Werte für Verbrauch, Netz und Batterie stammen vom Fronius Smart Meter. Falls Laden/Entladen vertauscht ist: „Vorzeichen Batterie umkehren“.

## Fehlerbehebung

- **Zeitüberschreitung:** IP prüfen, Gerät im selben Netz? Firewall/VLAN?
- **Zugriff verweigert:** Zugangsdaten bzw. Token prüfen.
- **Werte falsch herum:** Vorzeichen-Optionen nutzen (siehe oben).
- Weiter: [FAQ](../faq.md) · [Fehlerbehebung](../troubleshooting.md)
