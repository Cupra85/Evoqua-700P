# Evoqua 700P für Home Assistant

![Evoqua](custom_components/evoqua_700p/brand/icon.png)

Lokale, ausschließlich lesende Integration für Evoqua / Wallace & Tiernan
DEPOLOX Pool E 700 P. **Bei der Einrichtung wird nur die IP-Adresse eingegeben.**
Port, Unit-ID, Registerzuordnung und Byte-Reihenfolgen sind automatisch gesetzt.
Kein MQTT-Broker und kein Node-RED sind für diese Integration erforderlich.

## Installation

1. In HACS unter **Benutzerdefinierte Repositories**
   `https://github.com/Cupra85/Evoqua-700P` als **Integration** hinzufügen.
2. **Evoqua 700P** herunterladen und Home Assistant neu starten.
3. **Einstellungen → Geräte & Dienste → Integration hinzufügen → Evoqua 700P**.
4. **IP-Adresse eingeben und absenden.** Es gibt keine weiteren Eingabefelder.

Am Gerät muss Modbus TCP auf Port **502** aktiviert sein. Home Assistant muss
die Anlage im lokalen Netz erreichen. Die IP-Adresse wird ausschließlich in der
jeweiligen Home-Assistant-Installation gespeichert; im Repository ist keine
Geräteadresse hinterlegt. Mehrere Anlagen können mit unterschiedlichen IPs
eingerichtet werden. Die Verbindung und das gesamte Leseprofil werden vor dem
Speichern geprüft. Die IP kann später über **Neu konfigurieren** geändert werden.

Alternativ das Release-ZIP entpacken und `custom_components/evoqua_700p` nach
`/config/custom_components/evoqua_700p` kopieren. Danach Home Assistant neu starten.
Home Assistant ab 2025.12; für das mitgelieferte Logo ab 2026.3.

## Leseprofil ab Version 0.1.4

Das Profil wurde aus einem bestehenden Node-RED-Flow **„700P Lesen“** einer Anlage
mit **V:2.06** übernommen. Der Systemname ist frei einstellbar (beispielsweise
„Pool“) und muss deshalb keine Modellnummer enthalten. Systemname, lesbare
Firmware ab 1.31 und gültige Antworten auf die Profilabfragen sind erforderlich.
Die Firmwarekennung allein beweist nicht das Gerätemodell.

- Chlor, pH, Redox und Temperatur.
- Aktuelle Chlor-/pH-Sollwerte sowie Dosierleistungen.
- Chlor-/pH-Reglerparameter W, Xp und Tn.
- Chlor-, pH-, Redox- und Temperaturgrenzwerte einschließlich Hysteresen.
- DI1–DI3, Messwasser, Messwasser-Stopp und Alarm 1–4.
- Zustände der Relais K1–K8 und K21–K24.
- Betriebsart, Stoßchlorungsstatus, Fehlertext und vollständige Fehlerbits.
- Systemname, Softwareversion, Gerätedatum und Gerätezeit.

Alle Entitäten sind Sensoren oder Binärsensoren. Auch Sollwerte, Reglerparameter
und Relais werden **nur gelesen**. Die Integration implementiert ausschließlich
Modbus **FC03** und keine Steuerung von Dosierung, Sollwerten oder Relais.

## Register und Datenformate

Die folgenden Adressen sind **direkte, nullbasierte Adressen im Modbus-Telegramm**.
Sie sind keine 4xxxxx-Handbuchnummern. Das Profil übernimmt die Adressierung der
Sequencer unverändert; die beiden FLOAT-Gruppen haben unterschiedliche Reihenfolgen.

| Inhalt | Wire-Adresse | Format |
|---|---:|---|
| Systemname / Softwareversion | 0 / 10 | Text, Bytes je Register vertauscht |
| Gerätedatum / Gerätezeit | 15 / 20 | Text, Bytes je Register vertauscht |
| Chlor / pH / Redox / Temperatur | 100 / 115 / 130 / 175 | FLOAT ABCD |
| Aktuelle Sollwerte Chlor / pH | 111 / 126 | FLOAT ABCD |
| Dosierleistung Chlor / pH | 113 / 128 | FLOAT ABCD |
| Alarm / Digitaleingänge | 299 / 300 | Bits des ersten UINT16 |
| Relais K1–K8 / K21–K24 | 301 / 302 | UINT16, Bits 0–7 / 0–3 |
| Betriebsart / Stoßchlorung | 303 | UINT16, Stoßchlorung Bit 15 |
| Fehler | 307 | UINT32, Low-Word zuerst (CDAB) |
| Chlor W / Xp / Tn | 999 / 1001 / 1003 | FLOAT CDAB |
| pH W / Xp / Tn | 1005 / 1007 / 1009 | FLOAT CDAB |
| Chlor Min1/Max1/Hyst1/Min2/Max2/Hyst2 | 1049–1059, Schritt 2 | FLOAT CDAB |
| pH Min1/Max1/Hyst1/Min2/Max2/Hyst2 | 1061–1071, Schritt 2 | FLOAT CDAB |
| Redox Min1/Max1/Hyst1/Min2/Max2/Hyst2 | 1073–1083, Schritt 2 | FLOAT CDAB |
| Temperatur Min1/Max1/Hyst1 | 1109 / 1111 / 1113 | FLOAT CDAB |

ABCD entspricht Big Endian über beide Register; CDAB vertauscht die beiden
16-Bit-Wörter. Die Einheiten sind wie im Flow fest zugeordnet: mg/L, mV, °C, % und
min. pH ist dimensionslos. DI-Bit 3 bedeutet Messwasser-Stopp; „Messwasser“ zeigt
entsprechend die umgekehrte Polarität. Fehlercodes werden ohne Vorzeichen gelesen.
Lange Fehlerlisten stehen vollständig im Attribut `active_flags`.

Abfrageintervall: **10 Sekunden** für alle Werte, Port **502**, Unit-ID **1**,
Zeitlimit **1 Sekunde pro Anfrage**. Anders als im Ausgangsflow werden Relais
ebenfalls alle 10 Sekunden abgefragt. Eine Verbindung pro Zyklus, Anfragen
nacheinander. Nach einem Fehler werden die Entitäten nicht verfügbar; die nächste
erfolgreiche Abfrage stellt sie wieder her. NaN und Infinity werden nicht publiziert.

Die Gerätezeit wird ohne künstlichen Stundenaufschlag angezeigt. Der Ausgangsflow
enthielt einen festen +10-Stunden-Aufschlag; dieser anlagenspezifische Workaround
wurde nicht in eine universelle Integration übernommen. Unverwendete Sequenzen
ohne zugehörige Auswertung (329 und 1999) werden nicht zusätzlich abgefragt.

## Aktualisierung von 0.1.3

Die gespeicherte IP und die eindeutigen Kennungen bestehender Messwert-Entitäten
bleiben erhalten. Bisherige erweiterte Einstellungen werden durch das oben
beschriebene feste Profil ersetzt. Zusätzliche Entitäten werden automatisch
angelegt. Alte Entitäten für nicht im Profil enthaltene Kanäle können als nicht
verfügbar bestehen bleiben; sie werden nicht automatisch gelöscht.

## Prüfstand

27 Protokolltests prüfen Telegramme, exakte Profiladressen, gemischte Byte-
Reihenfolgen, Text, Eingänge, Relais, Meldungen, Nichtverfügbarkeit und Erholung.
Ein zusätzlicher Home-Assistant-Testlauf prüft das IP-Formular, Plattformen und
Migration mit simulierten Gerätedaten. Ergebnisse stehen unter
[GitHub Actions](https://github.com/Cupra85/Evoqua-700P/actions) und in
[TEST_REPORT.md](TEST_REPORT.md).

Die Zuordnung ist aus dem bereitgestellten Flow abgeleitet. Ein Ende-zu-Ende-Test
dieser Version an einer echten 700P steht noch aus. Auch endliche FLOAT-Werte
können bei einer falschen Zuordnung falsch sein: Messwerte beim ersten Test mit
der Geräteanzeige vergleichen. Das Paket ist kein offizielles Evoqua-Produkt.

Die [Aufnahme in den Marketplace-Katalog](https://github.com/hacs/default/pull/14943)
ist beantragt und wartet auf die Freigabe des HACS-Teams. Bis dahin ist die
Installation über das benutzerdefinierte Repository möglich.

## Diagnose und Entwicklung

```sh
python tools/probe.py 192.0.2.10
python -m unittest discover -s tests -p test_protocol.py -v
python tools/validate_metadata.py
```

`192.0.2.10` ist eine Beispieladresse. Das Diagnoseprogramm verwendet standardmäßig
dasselbe feste Profil wie Home Assistant. `--profile manual` aktiviert ausschließlich
für Entwickler das frühere Handbuchprofil mit wählbarer Registerbasis/Byte-Reihenfolge.
Für socketfreie Testumgebungen ist `EVOQUA_TEST_TRANSPORT=memory` verfügbar.

Home-Assistant-Tests: `pip install pytest-homeassistant`, danach
`python -m pytest tests/test_ha.py -v` (passende Python-/Home-Assistant-Version).

Fehlerberichte: [Issues](https://github.com/Cupra85/Evoqua-700P/issues). Lizenz: MIT.
