# Prüfstand 25.11.2026 – Version 0.1.4

## Bestanden

- 27 Protokolltests: alle bisherigen 17 Prüfungen und zehn zusätzliche Tests
  für das aus Node-RED übernommene Leseprofil.
- Auf GitHub unter Python 3.13 und 3.14 mit einem echten lokalen TCP-Simulator.
  Lokal zusätzlich mit simulierten Datenströmen ohne OS-Sockets geprüft.
- Exakte Wire-Adressen, FC03, Unit-ID, gemischte FLOAT-Reihenfolgen,
  bytevertauschter Text, frei einstellbarer Systemname „Pool“ und V:2.06.
- Eingänge, invertierte Messwasseranzeige, Alarmbits, Relais K1–K8 und K21–K24,
  Betriebsart, Stoßchlorung und vorzeichenlose 32-Bit-Fehlerauswertung.
- Fehlende Antworten, Timeout, Wiederverbindung, fragmentierte und fehlerhafte
  Telegramme, NaN/Infinity sowie lange Fehlerlisten ohne zu lange HA-Zustände.
- JSON, Übersetzungen und Metadaten; beide Formulare enthalten nur `host`.
- Zehn Tests mit echtem Home Assistant **2026.11.3**, Python **3.14.10** und
  simulierten Gerätedaten: IP-Eingabe und Speicherung, ungültige IPs,
  Verbindungsfehler, doppelte Einrichtung, Entitäten laden/entladen,
  Migration bestehender Einträge und IP-Neukonfiguration.

[Erfolgreicher Testlauf](https://github.com/Cupra85/Evoqua-700P/actions/runs/45682152090).
[Home-Assistant-Testergebnisse](https://github.com/Cupra85/Evoqua-700P/actions/runs/45682152090/job/139445194849).

Home Assistant lädt ausschließlich Sensoren und Binärsensoren; es werden keine
Schalter, Schreibdienste oder steuerbaren Zahlenfelder angelegt.

## Herkunft und praktische Grenzen

Der vorhandene Node-RED-Flow „700P Lesen“ wurde über die lesende API eingesehen.
Die ausgewerteten Register und deren jeweilige Dekodierung wurden übernommen.
Node-RED und vorhandene Home-Assistant-Entitäten wurden dabei nicht verändert.
Private Verbindungsdaten und der vollständige Workflow werden nicht veröffentlicht.

Die Prüfung bestätigt die Übereinstimmung mit der ausgelesenen Flow-Konfiguration,
nicht die physikalische Richtigkeit jeder Registerzuordnung. Bei einigen Istwerten
des vorhandenen Flows sind Werte auffällig; eine Verschiebung um ein Register
kann erst anhand echter Rohregister und der Geräteanzeige abschließend beurteilt
werden. Ein direkter FC03-Vergleich konnte in der Entwicklungsumgebung wegen
gesperrter Socket-Verbindungen nicht ausgeführt werden. Die neue Integration
wurde daher noch nicht Ende zu Ende mit der echten Anlage verifiziert.

Vor Verwendung der Messwerte in Automationen müssen diese mit der Geräteanzeige
verglichen werden. Es werden keine Werte anhand vermeintlich plausibler Bereiche
umgedeutet oder still auf andere Register umgestellt.

Abweichungen zum Ausgangsflow sind ausdrücklich dokumentiert: alle Werte werden
alle zehn Sekunden abgefragt, auch Relais; die Gerätezeit erhält keinen festen
+10-Stunden-Aufschlag. Unverwendete Sequenzen ohne Auswertung sind ausgelassen.
