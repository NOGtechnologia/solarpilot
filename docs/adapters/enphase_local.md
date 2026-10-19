# Enphase IQ Gateway (lokal)

Envoy/IQ Gateway ab Firmware 7 mit Token.

## Einrichtung

1. Token holen: https://entrez.enphaseenergy.com → mit Enlighten-Konto anmelden → Gateway auswählen → Token erzeugen (gilt 1 Jahr für Besitzer).
   <!-- Screenshot Schritt 1: hier eigenes Bild aus docs/images/adapters/ einfügen -->
2. IP des Gateways und Token im Assistenten eintragen. Der Token wird verschlüsselt gespeichert.
   <!-- Screenshot Schritt 2: hier eigenes Bild aus docs/images/adapters/ einfügen -->
3. Das Gateway nutzt ein selbstsigniertes Zertifikat – „Zertifikat prüfen“ daher standardmäßig aus.
   <!-- Screenshot Schritt 3: hier eigenes Bild aus docs/images/adapters/ einfügen -->

## Hinweise

Verbrauchs- und Netzwerte gibt es nur mit installierten Verbrauchs-CTs.

## Fehlerbehebung

- **Zeitüberschreitung:** IP prüfen, Gerät im selben Netz? Firewall/VLAN?
- **Zugriff verweigert:** Zugangsdaten bzw. Token prüfen.
- **Werte falsch herum:** Vorzeichen-Optionen nutzen (siehe oben).
- Weiter: [FAQ](../faq.md) · [Fehlerbehebung](../troubleshooting.md)
