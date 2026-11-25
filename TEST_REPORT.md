# Prüfstand 25.11.2026

## Erfolgreich geprüft

- Python 3.13.17: 17 Protokolltests mit simulierten Modbus-Datenströmen,
  einschließlich weiterer Unterfälle für Byte-Reihenfolgen und fehlerhafte Antworten.
- Registeradressen aller acht Messkanäle, FC03-Telegramme, Unit-ID und beide Registerbasen.
- IEEE754, CP437 und Einheiten, UINT32-Fehlercodes, Nichtverfügbarkeit bei NaN/Infinity.
- Timeouts, Abbruch, Wiederverbindung und aufeinanderfolgende gleichzeitige Abfragen.
- Python-Syntax aller Integrations-, Werkzeug- und Testdateien.
- JSON-Syntax, Manifest-Felder und Übersetzungsabdeckung (Deutsch/Englisch).
- Versionskennung V2.06 und V:2.06 wird akzeptiert und unverändert weitergegeben.
- GitHub Actions: beide Jobs unter Python 3.13 und 3.14 erfolgreich; vollständige
  TCP-Tests, Syntaxprüfung und Metadatenprüfung bestanden.
  [Testlauf auf GitHub](https://github.com/Cupra85/Evoqua-700P/actions/runs/45671851737).

Die lokalen Tests wurden mit `EVOQUA_TEST_TRANSPORT=memory` ausgeführt. Dabei
werden die TCP-Streams simuliert; ausschließlich `asyncio.open_connection` wird
im Test ersetzt. Auf GitHub wurden dieselben Tests anschließend ohne diesen
Ersatz mit echten TCP-Verbindungen zum lokalen Simulator ausgeführt.

## Noch offen

- Home-Assistant-Laufzeit und HACS: Zusatzpakete konnten wegen fehlender
  Namensauflösung zu PyPI nicht installiert werden. Es liegt kein ausgeführter
  Home-Assistant-Kompatibilitätstest vor.
- Hardware: Firmware V2.06 laut Nutzer. Die IP-Adresse ist absichtlich universell
  und wird erst in Home Assistant abgefragt; sie wird für die Entwicklung nicht
  benötigt. Unit-ID, vorhandene Kanäle, Registerbasis und Byte-Reihenfolge müssen
  bei der Einrichtung anhand der echten Anlage bestätigt werden.

Die Quellen und Annahmen stehen in README.md. Dieses Paket ist eine vorbereitete
Erstversion und darf noch nicht als an der realen Anlage verifiziert bezeichnet werden.
