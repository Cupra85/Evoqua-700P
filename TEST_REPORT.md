# Prüfstand – Version 0.1.5

## Lokale Prüfungen

- 41 Protokolltests mit fragmentierten simulierten Datenströmen bestanden.
- Unabhängige Registerfixtures nach Evoqua v2-Anleitung, Abschnitt 4.6.
- Alle 45 RW-FLOAT-Adressen und exakte FC16-Nutzdaten geprüft.
- FC06 Start/Stopp, Erhalt anderer Funktionsbits, Schutz gegen gesetztes Befehlsbit.
- Frische Bereiche/Grenzwertpaare, ungültige Werte, NaN/Infinity, identische Zahlen,
  Schreibabstand und Verbindungsfreigabe geprüft.
- Abweichendes Rücklesen, falsches Echo, Modbus-Ausnahme, Timeout und Verlust der
  Bestätigung nach wirksamem Schreiben: kein automatischer Wiederholversuch.
- Abfragen senden ausschließlich FC03, auch nach einem Schreibfehler.
- Optionale Register, zusätzliche Kanäle, Alarme 5–8, Betriebsarten und Fehlercodes.
- JSON, Übersetzungsabdeckung, Kompilierung und IP-only-Formulare bestanden.

## GitHub-Prüfungen

Die Workflows prüfen TCP unter Python 3.13/3.14 sowie die Integration mit echtem
Home Assistant und simulierten Gerätedaten. HA-Tests prüfen die vier Plattformen,
IP-only-Formulare, Migration, explizite Number-/Button-Bedienung und Fehlerweitergabe.
HACS und hassfest prüfen Paket und Metadaten ohne ausgeschaltete Prüfungen.
Der zugehörige Lauf wird vor Veröffentlichung geprüft:
[GitHub Actions](https://github.com/Cupra85/Evoqua-700P/actions).

## Herkunft und Grenzen

Referenz: Evoqua Originalbetriebsanleitung ab Version 2.00, Ausgabe 11-0620,
WT.050.810.010.DD.IM.0620, Abschnitt 4.6, Seiten 30–37.
FLOAT-/Textreihenfolge zusätzlich anhand der Herstellerdiagramme in der englischen
Anleitung WT.050.810.010.DE.IM.0718, Seiten 47–48 abgeglichen.
Die vorhandenen Node-RED-Verbindungsparameter bestimmen Port, Unit-ID und Timeout.
Private IPs und vollständige Workflows sind nicht Teil des öffentlichen Projekts.

0.1.5 korrigiert die Messwertabfragen aus dem ursprünglichen Flow gemäß Anleitung:
einbasierte Handbuchregister und CDAB statt des um ein Register verschobenen ABCD.
Softwaretests bestätigen diese dokumentierte Zuordnung. Ein Abgleich der neuen
Integration mit tatsächlichen Rohregistern und Geräteanzeige steht noch aus.
Die lokale Umgebung erlaubt keinen direkten Socket-Zugriff auf die Anlage.
Es wurden keine Parameter einer echten Anlage geändert und keine echten
Dosieraktionen ausgelöst. HA-/Node-RED-Konfigurationen wurden nicht verändert.

Die exakte Umrechnung der Hysteresegrenze 1–25 Anzeigedigits ist bei variablen
Messbereichen nicht per Modbus beschrieben. Roh-FLOAT in Geräteeinheit, positive
Spannenprüfung und exaktes Rücklesen; konkrete Digitgrenze am Gerät prüfen.
Der Start/Stopp-Befehl bestätigt nur den Modbus-Empfang, nicht den Prozessstart.
Iststatus und Geräteschutzfunktionen bleiben maßgeblich.
