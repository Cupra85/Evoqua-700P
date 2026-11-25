# Evoqua 700P für Home Assistant

Lokale, ausschließlich lesende Custom Integration für die Evoqua / Wallace & Tiernan
**DEPOLOX Pool E 700 P**. Einrichtung über die Home-Assistant-Oberfläche mit
IP-Adresse, Modbus-TCP-Port und Auswahl der vorhandenen Messkanäle.

**Stand 0.1.2:** Protokolltests mit simulierten Modbus-Datenströmen.
Die Integration wurde noch nicht an einer echten 700 P und noch nicht in einem
laufenden Home Assistant geprüft. Vor produktiver Nutzung die Werte mit der
Geräteanzeige vergleichen. Dieses Paket ist kein offizielles Evoqua-Produkt.

## Voraussetzungen

- Home Assistant **2025.12 oder neuer**; für diese Versionen entwickelt,
  ein vollständiger Home-Assistant-Kompatibilitätstest steht noch aus.
- 700 P mit Firmware **ab 1.31** und aktivierter Modbus-TCP-Schnittstelle.
- In den Ethernet-Einstellungen des Geräts **Modbus Port = 502** setzen und
  mit **Übernehmen** speichern. Laut Hersteller ist der Modbus-Port ab Werk aus.
- Home Assistant kann die IP-Adresse und Port 502 im lokalen Netz erreichen.

## Installation

1. ZIP entpacken.
2. Den gesamten Ordner `custom_components/evoqua_700p` in das Home-Assistant-
   Konfigurationsverzeichnis kopieren. Ergebnis:
   `/config/custom_components/evoqua_700p/manifest.json`.
   Bei anderen Installationsarten kann das Konfigurationsverzeichnis anders heißen.
3. Home Assistant neu starten.
4. **Einstellungen → Geräte & Dienste → Integration hinzufügen → Evoqua 700P**.
5. IP-Adresse der Pool-Messanlage eingeben und tatsächlich vorhandene Kanäle wählen.

Die IP-Adresse wird bei jeder neuen Einrichtung abgefragt und nur in der jeweiligen
Home-Assistant-Installation gespeichert. Es ist keine Geräte-IP im Code hinterlegt;
auch mehrere Anlagen mit unterschiedlichen IP-Adressen können eingerichtet werden.

Als Firmware des Zielgeräts wurde **V2.06** angegeben. Diese Versionskennung wird
akzeptiert und in den Geräteinformationen angezeigt; ein zusätzlicher Protokolltest
prüft die Schreibweisen `V2.06` und `V:2.06`. Eine speziell für V2.06 veröffentlichte
Registerliste wurde nicht gefunden. Die tatsächliche Registerkompatibilität mit
dieser Firmware muss deshalb noch am Gerät bestätigt werden.

Das Formular prüft die Gerätekennung und liest die ausgewählten Kanäle, bevor es
die Verbindung speichert. Nicht vorhandene Kanäle bitte abwählen; die Integration
behauptet keine automatische Erkennung der eingebauten Sensoren.

Für die Installation über HACS unter **Benutzerdefinierte Repositories** die URL
`https://github.com/Cupra85/Evoqua-700P` und die Kategorie **Integration** eintragen.
Anschließend **Evoqua 700P** herunterladen, Home Assistant neu starten und die
Integration wie oben beschrieben hinzufügen. `hacs.json` und die passende
Verzeichnisstruktur liegen bei. Eine HACS-Validierung ist noch nicht erfolgt.
Manuelle Installation funktioniert unabhängig von HACS.

## Einstellungen

| Einstellung | Standard | Bedeutung |
| --- | --- | --- |
| Host | eigene Geräte-IP | IP-Adresse oder DNS-Name, ohne `http://` |
| Port | 502 | Modbus TCP |
| Unit-ID | 1 | Im Handbuch nicht eindeutig spezifiziert; falls nötig anpassen |
| Zeitlimit | 5 Sekunden | Je Verbindungsaufbau bzw. Modbus-Anfrage |
| Registerbasis | 400001 | Handbuchregister 400100 wird als Adresse 99 übertragen |
| Byte-Reihenfolge | ABCD | 32-Bit-Werte, z. B. `3F A0 00 00` = 1,25 |
| Messkanäle | Chlor, pH, Redox, Temperatur | Nur vorhandene Messkanäle auswählen |
| Abfrageintervall | 30 Sekunden | Änderbar zwischen 5 und 3600 Sekunden |
| Statusregister | aus | Optional Fehlercodes und Messwasser-Stopp auslesen |

Messkanäle und Abfrageintervall lassen sich über **Konfigurieren** ändern.
Verbindungsdaten über das Menü der Integration → **Neu konfigurieren** ändern.
Die Entitätskennungen bleiben dabei erhalten. Bei geänderter Kanalauswahl werden
entfernte Kanäle nicht mehr aktualisiert; alte Einträge können anschließend im
Entitätsregister gelöscht werden.

## Messwerte und Register

| Sensor | Handbuchregister | Übertragene Adresse bei Basis 400001 |
| --- | ---: | ---: |
| Chlor | 400100 | 99 |
| pH | 400115 | 114 |
| Redox | 400130 | 129 |
| Gesamtchlor | 400145 | 144 |
| Leitfähigkeit | 400160 | 159 |
| Temperatur | 400175 | 174 |
| Umwälzung / mA-Eingang 1 | 400205 | 204 |
| mA-Eingang 2 | 400220 | 219 |

Jeder Messwert ist ein IEEE754-FLOAT über zwei Holding-Register; danach folgen
fünf Register mit der Einheit in CP437. Die Einheit kommt direkt vom Gerät,
insbesondere °C/°F und µS/cm/mS/cm werden nicht fest angenommen. `mg/l` wird
als `mg/L` normalisiert. pH erhält keine physikalische Einheit.

Optional werden die Register 400300–400317 abgefragt: Messwasser-Stopp
(400301, Bit 3), ein Störungssensor je ausgewähltem chemischen Kanal und dessen
roher UINT32-Fehlercode. Die Fehlercode-Sensoren sind zunächst deaktiviert und
können im Entitätsregister eingeschaltet werden. Einzelne Fehlerbits unterscheiden
sich zwischen Handbuchständen und werden deshalb nicht als Klartext interpretiert.

## Verhalten bei Fehlern

- Ausschließlich **FC03**. Es gibt keine Schreibfunktion und keine Steuerung
  von Dosierung oder Sollwerten.
- Eine TCP-Verbindung pro Abfragezyklus; alle Anfragen erfolgen nacheinander.
- Bei einer fehlgeschlagenen Anfrage wird der gesamte Zyklus verworfen. Die
  betroffenen Entitäten werden nicht verfügbar und erholen sich nach erfolgreicher Abfrage.
- NaN und unendliche FLOAT-Werte gelten als nicht verfügbar. Endliche Werte werden
  nicht auf vermeintlich plausible Bereiche begrenzt; sie müssen zur Geräteanzeige passen.
- Diagnosedownload enthält keine IP-Adresse. Hostname und Geräte-IP werden nicht
  in dieses Repository geschrieben.

## Verbindung ohne Home Assistant testen

Das beiliegende Diagnoseprogramm braucht nur Python ab 3.13, keine Zusatzpakete:

```sh
python tools/probe.py 192.168.1.50
python tools/probe.py 192.168.1.50 --channels ph temperature --unit-id 1 --status
```

`192.168.1.50` ist eine Beispieladresse. Deine Geräte-IP einsetzen.
Ein erfolgreicher Aufruf liefert JSON mit Gerätekennung, Softwareversion,
Messwerten und Einheiten. Mit der Anzeige der 700 P vergleichen.

Bei fehlender Verbindung zuerst aktivierten Modbus-Port, IP, VLAN/Firewall und
Unit-ID prüfen. Ein Registerfehler oder eine unpassende Gerätekennung kann an der
Adressierung liegen: `--register-base 400000` ist als Diagnoseoption vorhanden.
Falls Werte falsch dekodiert werden, stehen `--byte-order CDAB`, `BADC` oder `DCBA`
zur Verfügung. Einstellungen nur anhand der Geräteanzeige bzw. eines Telegrammmitschnitts
ändern. Die Byte-Reihenfolge gilt für 32-Bit-Zahlen; Text bleibt CP437 in Registerreihenfolge.
Eine Firmware mit anderem Systemnamen als einer Kennung mit `700 P` wird abgewiesen.

## GitHub

- Repository: [Cupra85/Evoqua-700P](https://github.com/Cupra85/Evoqua-700P)
- Fehlerberichte: [Issues](https://github.com/Cupra85/Evoqua-700P/issues)
- Lizenz: MIT

## Entwicklung und Prüfung

```sh
python -m unittest discover -s tests -p test_protocol.py -v
python -m compileall -q custom_components tools tests
python tools/validate_metadata.py
```

Standardmäßig verwenden die Tests lokale TCP-Verbindungen zum Simulator. In
Umgebungen ohne Netzwerkzugriff kann `EVOQUA_TEST_TRANSPORT=memory` gesetzt werden;
dann wird derselbe Testumfang mit In-Memory-Datenströmen und ohne OS-Sockets geprüft.
Geprüft werden alle Messkanäle,
CP437, vier Byte-Reihenfolgen, Registerbasis und Unit-ID, fragmentierte Antworten,
Statuscodes, Timeout, Abbruch, Wiederverbindung und fehlerhafte Telegramme.
Der GitHub-Workflow führt diese Prüfungen unter Python 3.13 und 3.14 aus.
Er ersetzt keine Home-Assistant- oder Hardwareprüfung.

## Quellen

- Evoqua, **Elektronik-Modul 700 P**, W3T321511 Ausgabe 11-0620,
  Kapitel 4.6 und Ethernet-Einstellungen:
  [Herstelleranleitung als Spiegel](https://manualzz.com/doc/68426676/evoqua-wallace-and-tiernan-700-p-betriebsanleitung).
- [Home Assistant: Config flow](https://contributors.home-assistant.io/core/integrations/config-flow/)
- [Home Assistant: DataUpdateCoordinator](https://contributors.home-assistant.io/core/integrations/fetching-data/)
- [Home Assistant: Options flow](https://contributors.home-assistant.io/core/integrations/options-flow/)
