# Änderungen

## 0.1.4

- Einrichtung und Neukonfiguration fragen ausschließlich die IP-Adresse ab.
- Leseprofil aus dem bestehenden Node-RED-Flow für Firmware V2.06 übernommen.
- Unterschiedliche Adressierung und Byte-Reihenfolgen je Registergruppe berücksichtigt.
- Frei einstellbare Systemnamen wie „Pool“ zugelassen.
- Sollwerte, Dosierleistungen, Reglerparameter, Grenzwerte, Eingänge, Alarme,
  Relaiszustände, Betriebsart, Fehler und Geräteinformationen als Sensoren ergänzt.
- Vorhandene Einträge auf das feste Profil migriert; gespeicherte IP bleibt erhalten.
- 27 Protokolltests und zusätzliche Home-Assistant-Tests für Formular und Plattformen.
- Gerätezeit ohne anlagenspezifischen +10-Stunden-Aufschlag; Relaisintervall 10 Sekunden.

## 0.1.3

- Evoqua-Logo für die Anzeige der Integration hinzugefügt.
- Offizielle Prüfungen mit HACS und Home Assistant hassfest ergänzt.
- Metadaten für die Aufnahme in den Marketplace-Katalog vorbereitet.

## 0.1.2

- Erstveröffentlichung auf GitHub mit Konfiguration über IP-Adresse.
- Ausschließlich lesende Modbus-TCP-Auslesung der ausgewählten Messkanäle.
- Deutsche und englische Übersetzungen sowie Diagnoseprogramm.
- 17 Protokolltests unter Python 3.13 und 3.14 bestanden.
