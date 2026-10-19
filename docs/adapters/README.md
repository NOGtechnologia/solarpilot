# Hersteller-Anleitungen

Wo möglich verbindet sich SolarPilot **lokal** (schnell, ohne Cloud, ohne Rate-Limit).
Alle Adapter werden im [Einrichtungs-Assistenten](../erste-schritte.md) mit „Verbindung testen“ geprüft.

| Hersteller / Gerät | Anleitung | Verbindung | Status |
| --- | --- | --- | --- |
| Demo-Simulator | [demo](demo.md) | – | stabil |
| SunSpec (generisch) | [sunspec_modbus](sunspec_modbus.md) | Modbus TCP | beta |
| SMA | [sma](sma.md) | Modbus TCP | beta |
| SolarEdge | [solaredge](solaredge.md) | Modbus TCP | beta |
| Kostal Plenticore | [kostal](kostal.md) | Modbus TCP | beta |
| Fronius | [fronius_local](fronius_local.md) | Solar API (HTTP) | beta |
| Huawei SUN2000 | [huawei_modbus](huawei_modbus.md) | Modbus TCP | beta |
| Victron GX | [victron_modbus](victron_modbus.md) | Modbus TCP | beta |
| Enphase IQ Gateway | [enphase_local](enphase_local.md) | HTTPS + Token | beta |
| GoodWe | [goodwe_local](goodwe_local.md) | UDP | beta |
| Hoymiles / OpenDTU | [opendtu](opendtu.md) | REST | beta |
| Shelly 3EM / Pro 3EM | [shelly_3em](shelly_3em.md) | HTTP | beta |
| MQTT (generisch) | [mqtt_generic](mqtt_generic.md) | MQTT | beta |
| Home Assistant | [home_assistant](home_assistant.md) | REST | beta |

**beta** = mit aufgezeichneten Antworten getestet; Rückmeldungen von echten Anlagen bitte als
[Issue](../../../../issues/new/choose) – das ist der schnellste Weg zu „stabil“.

Dein Gerät fehlt? Siehe [Neuen Adapter bauen](../../CONTRIBUTING.md#so-baust-du-einen-neuen-adapter).

## Vorzeichen

| Wert | positiv | negativ |
| --- | --- | --- |
| Netz | Bezug | Einspeisung |
| Batterie | Laden | Entladen |

Zeigt dein Gerät es andersherum, gibt es im Adapter eine Option „Vorzeichen umkehren“.
