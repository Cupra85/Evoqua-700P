# Evoqua 700P für Home Assistant

![Evoqua](custom_components/evoqua_700p/brand/icon.png)

Lokale Modbus-TCP-Integration für Evoqua / Wallace & Tiernan DEPOLOX Pool E 700 P.
**Bei der Einrichtung nur die IP-Adresse eingeben.** Port 502, Unit-ID 1,
Register und Datenformate werden automatisch gesetzt. Kein MQTT oder Node-RED nötig.

## Installation

1. In HACS unter **Benutzerdefinierte Repositories**
   `https://github.com/Cupra85/Evoqua-700P` als **Integration** hinzufügen.
2. **Evoqua 700P** herunterladen und Home Assistant neu starten.
3. **Einstellungen → Geräte & Dienste → Integration hinzufügen → Evoqua 700P**.
4. **IP-Adresse eingeben und absenden.** Keine weiteren Eingabefelder.

Am Gerät muss Modbus TCP auf Port 502 aktiviert sein. Home Assistant muss die
Anlage im lokalen Netz erreichen. Mehrere Anlagen lassen sich mit verschiedenen
IPs einrichten. Die Adresse wird nur lokal in Home Assistant gespeichert und
kann über **Neu konfigurieren** geändert werden.

Alternativ das Release-ZIP entpacken und `custom_components/evoqua_700p` nach
`/config/custom_components/evoqua_700p` kopieren. Home Assistant neu starten.
Home Assistant ab 2025.12; eingebautes Logo ab 2026.3. Zielanlage: Firmware V2.06.

## Lesen und Schreiben ab 0.1.5

Die Integration deckt alle funktional bezeichneten R- und RW-Datenpunkte der
Evoqua-Anleitung ab Version 2.00, Ausgabe 11-0620, Abschnitt 4.6 ab.
Mit `--` markierte/reservierte Bereiche haben keine eigene Funktion.
Die vollständige Zuordnung steht in [REGISTERS.md](REGISTERS.md).

| Bereich | Unterstützung |
|---|---|
| Chlor, pH, Redox, Gesamtchlor, Leitfähigkeit, Temperatur | Messwert, Geräteeinheit, Messbereich |
| Umwälzung / Analogeingang 2 | Messwert, frei konfigurierte Geräteeinheit und Messbereich |
| Flockung | Aktuelle Dosierleistung |
| Chemische Kanäle | Aktueller Sollwert und Dosierleistung, soweit dokumentiert |
| Chlor / pH / Gesamtchlor / Leitfähigkeit | W, Xp, Tn lesen und schreiben: 12 Zahlenfelder |
| Chlor / pH / Redox / Gesamtchlor / Leitfähigkeit | Min1, Max1, Hyst1, Min2, Max2, Hyst2 lesen und schreiben |
| Temperatur | Min1, Max1, Hysterese lesen und schreiben; insgesamt 33 Grenzwertfelder |
| Stoßchlorung | Start/Stopp-Button (402000 Bit 9), separater Iststatus (400304 Bit 15) |
| Eingänge / Alarme / Relais | DI1–3, Messwasser-Stopp, Alarm 1–8, K1–K8 und K21–K24 |
| Betriebsart | Alle vier Regler, vollständige 16-Bit-Auswertung in Attributen |
| Fehler | Alle fünf chemischen Kanäle, vollständige UINT32-Codes und Meldungen |
| Information | Systemname, Softwareversion, Datum, Gerätezeit, rohe Statuswörter |

Es gibt 80 numerische Lesesensoren, zusätzliche Text-/Diagnosesensoren und
Binärsensoren sowie **45 Numbers und einen Button**. Bestehende Lesesensoren für
RW-Parameter bleiben erhalten. Die Bedienelemente befinden sich beim HA-Gerät
unter **Konfiguration**. Zusätzliche Einheiten und rohe Codes sind standardmäßig
deaktivierte Diagnosesensoren und können bei Bedarf aktiviert werden.

Relais, Betriebsart und Dosierleistung sind in der Modbus-Tabelle ausschließlich
lesbar. Dafür werden keine Schreibbefehle erfunden. Geräteinterne Einstellungen
wie Kalibrierung, Stoßchlorungsdauer und Stoßchlorungssollwert sind in dieser
Modbus-Tabelle nicht schreibbar und werden weiterhin am Gerät eingestellt.

## Verhalten beim Schreiben

Schreiben erfolgt nur durch eine ausdrückliche Bedienung oder eine vom Benutzer
angelegte HA-Automation. Einrichten, Starten und Abfragen senden ausschließlich
FC03. Zahlen werden atomar mit FC16 über beide FLOAT-Register geschrieben;
der Start/Stopp-Befehl verwendet FC06. Keine zusätzliche Einrichtung erforderlich.

Vor Zahlenänderungen liest die Integration Identität, aktuellen Wert und die
benötigten Messbereichs-/Grenzwertdaten frisch. Xp: 0–1000 %, Tn: 0–100 min
(0 deaktiviert Tn). Sollwerte und Grenzwerte müssen im Gerätemessbereich liegen,
Min/Max zusätzlich innerhalb ihres Grenzwertpaars. Zahlen werden erst nach
exaktem Rücklesen als bestätigt behandelt; keine optimistische Zustandsänderung.

**Hysteresen:** Eingabe in der Einheit des Geräts, beispielsweise mg/L oder mV.
Die Anleitung nennt 1–25 Anzeigedigits, deren variable Schrittweite jedoch nicht
über Modbus. Es erfolgt deshalb keine angenommene Digit-Umrechnung. Die Software
prüft auf positive Werte bis zur Messbereichsspanne; die konkrete zulässige
Digitspanne muss mit der Geräteanzeige abgeglichen werden. Abweichende
Rücklesewerte führen zu einem Fehler. Details und Grenzen in [REGISTERS.md](REGISTERS.md).

**Stoßchlorung Start/Stopp:** Der Button sendet den dokumentierten 0x0200-Befehl
und bewahrt die übrigen Bits des frisch gelesenen Funktionsworts. Er besitzt
keinen angenommenen Ein-/Aus-Zustand. Dafür den separaten Sensor **Stoßchlorung**
und die Geräteanzeige verwenden. Ein noch gesetztes Befehlsbit verhindert eine
erneute Sendung. Kein automatisches Rücksetzen des Bits.
Eine Stoßchlorung darf gemäß Anleitung nur außerhalb des Badebetriebs erfolgen.

Die Anleitung warnt vor Speicherschäden durch zyklisches bzw. wiederholtes
Schreiben gleicher Werte. Identische kodierte Zahlen werden übersprungen;
höchstens ein Schreibversuch pro Sekunde. Nach Timeout oder verlorener
Bestätigung erfolgt **kein automatischer Schreibwiederholversuch**. Ein Befehl
kann dann bereits ausgeführt worden sein: erst den tatsächlichen Zustand prüfen.
Nach einem Befehl oder Fehler wird ausschließlich lesend aktualisiert.

## Registerformate und Aktualisierung

Handbuchregister sind einbasiert: `Wire-Adresse = Register − 400001`.
FLOAT und UINT32: **CDAB**, Low-Word zuerst. ASCII: CP437, Bytes innerhalb eines
16-Bit-Worts vertauscht. Geräteeinheiten werden ausgelesen, auch °F und mS/cm.
Keine fest angenommene Temperatureinheit und kein künstlicher Zeitaufschlag.
Der frei vergebene Systemname darf beispielsweise „Pool“ lauten.

Alle Werte werden alle **10 Sekunden** abgefragt. Pro Zyklus eine Verbindung,
Anfragen seriell; Zeitlimit 1 Sekunde pro Anfrage. Abfragen und Schreibaktionen
teilen eine Sperre. Nach Kommunikationsfehlern erfolgt Erholung beim nächsten
erfolgreichen Poll. Nicht endliche Werte werden nicht veröffentlicht. Modbus-
Ausnahmen 2/3 einzelner optionaler Messkanäle/Parameter machen nur diese Werte
nicht verfügbar; Transport- oder Protokollfehler betreffen den ganzen Zyklus.

**Upgrade von 0.1.4:** Die acht aus dem Node-RED-Flow übernommenen Messwertabfragen
wurden anhand der Anleitung auf die dokumentierten einbasierten Register und
CDAB berichtigt. Beispielsweise Chlor: Wire 99/CDAB statt 100/ABCD. Zahlen können
dadurch anders ausfallen. Vor Verwendung mit der Geräteanzeige vergleichen.
Gespeicherte IP und bestehende eindeutige Entitätskennungen bleiben erhalten.
Die neuen Werte und Bedienelemente werden automatisch ergänzt.

## Prüfungen und praktische Grenzen

41 Protokolltests prüfen Adressen, Dekodierung, alle 45 FLOAT-Schreibregister,
FC06, Grenzen, doppelte Werte, Rücklesefehler, verlorene Bestätigungen und
Wiederverbindung. Zusätzliche Tests mit echtem Home Assistant prüfen Formular,
Plattformen, Migration und die Bedienung der Numbers und des Buttons.
Ergebnisse: [GitHub Actions](https://github.com/Cupra85/Evoqua-700P/actions),
[TEST_REPORT.md](TEST_REPORT.md).

Diese Version ist softwareseitig mit simulierten Registern geprüft. Ein
Ende-zu-Ende-Test an der echten 700P steht aus. Es wurden keine Dosier- oder
Regelparameter an einer echten Anlage geändert. Die Integration ersetzt weder
die Geräteschutzfunktionen noch die Prüfung der Messwerte und Einstellungen.
Kein offizielles Evoqua-Produkt.

Die [Aufnahme in den HACS-Katalog](https://github.com/hacs/default/pull/14943)
ist beantragt; die Freigabe durch das HACS-Team steht aus. Bis dahin über das
benutzerdefinierte Repository installieren.

## Entwicklung

```sh
python tools/probe.py 192.0.2.10
python -m unittest discover -s tests -p test_protocol.py -v
python tools/validate_metadata.py
```

`192.0.2.10` ist eine Beispieladresse. Das Diagnoseprogramm liest ausschließlich.
Der interne Profilname `node_red_206` bleibt aus Kompatibilitätsgründen erhalten;
ab 0.1.5 entspricht er der vollständigen v2-Handbuchtabelle. `--profile manual`
ist das ältere, nur lesende Entwicklerprofil mit wählbaren Formaten.
Socketfreie Tests: `EVOQUA_TEST_TRANSPORT=memory`.
HA-Tests: `pip install pytest-homeassistant`, dann `python -m pytest tests/test_ha.py -v`.

[Fehler melden](https://github.com/Cupra85/Evoqua-700P/issues). Lizenz: MIT.
