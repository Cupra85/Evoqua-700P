# Modbus-Registerabdeckung

Quelle: Evoqua Originalbetriebsanleitung ab Version 2.00, Ausgabe 11-0620,
WT.050.810.010.DD.IM.0620, Abschnitt 4.6, Seiten 30–37.

[Anleitung](https://manualzz.com/doc/68426676/evoqua-wallace-and-tiernan-700-p-betriebsanleitung)

Alle funktional bezeichneten R- und RW-Datenpunkte sind enthalten. Mit `--`
markierte und nicht zugewiesene Register sind reserviert. Kein Zugriff auf
reservierte Daten als eigene Entitäten; keine generische Schreibfunktion.

4xxxxx ist eine einbasierte Handbuchnummer; Wire-Adresse = Register − 400001.
FLOAT und UINT32: CDAB (Low-Word zuerst); Text: CP437, Bytes je Wort vertauscht.

## Zahlenwerte

| Schlüssel | Handbuch | Wire | Zugriff | HA |
|---|---:|---:|---|---|
| `chlorine` | 400100 | 99 | R | Sensor |
| `chlorine_range_min` | 400107 | 106 | R | Sensor |
| `chlorine_range_max` | 400109 | 108 | R | Sensor |
| `chlorine_current_setpoint` | 400111 | 110 | R | Sensor |
| `chlorine_dosing` | 400113 | 112 | R | Sensor |
| `ph` | 400115 | 114 | R | Sensor |
| `ph_range_min` | 400122 | 121 | R | Sensor |
| `ph_range_max` | 400124 | 123 | R | Sensor |
| `ph_current_setpoint` | 400126 | 125 | R | Sensor |
| `ph_dosing` | 400128 | 127 | R | Sensor |
| `orp` | 400130 | 129 | R | Sensor |
| `orp_range_min` | 400137 | 136 | R | Sensor |
| `orp_range_max` | 400139 | 138 | R | Sensor |
| `orp_current_setpoint` | 400141 | 140 | R | Sensor |
| `orp_dosing` | 400143 | 142 | R | Sensor |
| `total_chlorine` | 400145 | 144 | R | Sensor |
| `total_chlorine_range_min` | 400152 | 151 | R | Sensor |
| `total_chlorine_range_max` | 400154 | 153 | R | Sensor |
| `total_chlorine_current_setpoint` | 400156 | 155 | R | Sensor |
| `total_chlorine_dosing` | 400158 | 157 | R | Sensor |
| `conductivity` | 400160 | 159 | R | Sensor |
| `conductivity_range_min` | 400167 | 166 | R | Sensor |
| `conductivity_range_max` | 400169 | 168 | R | Sensor |
| `conductivity_current_setpoint` | 400171 | 170 | R | Sensor |
| `conductivity_dosing` | 400173 | 172 | R | Sensor |
| `temperature` | 400175 | 174 | R | Sensor |
| `temperature_range_min` | 400182 | 181 | R | Sensor |
| `temperature_range_max` | 400184 | 183 | R | Sensor |
| `circulation` | 400205 | 204 | R | Sensor |
| `circulation_range_min` | 400212 | 211 | R | Sensor |
| `circulation_range_max` | 400214 | 213 | R | Sensor |
| `analog_input_2` | 400220 | 219 | R | Sensor |
| `analog_input_2_range_min` | 400227 | 226 | R | Sensor |
| `analog_input_2_range_max` | 400229 | 228 | R | Sensor |
| `flocculation_dosing` | 400190 | 189 | R | Sensor |
| `chlorine_setpoint` | 401000 | 999 | RW | Sensor + Number (FC16) |
| `chlorine_xp` | 401002 | 1001 | RW | Sensor + Number (FC16) |
| `chlorine_tn` | 401004 | 1003 | RW | Sensor + Number (FC16) |
| `ph_setpoint` | 401006 | 1005 | RW | Sensor + Number (FC16) |
| `ph_xp` | 401008 | 1007 | RW | Sensor + Number (FC16) |
| `ph_tn` | 401010 | 1009 | RW | Sensor + Number (FC16) |
| `total_chlorine_setpoint` | 401012 | 1011 | RW | Sensor + Number (FC16) |
| `total_chlorine_xp` | 401014 | 1013 | RW | Sensor + Number (FC16) |
| `total_chlorine_tn` | 401016 | 1015 | RW | Sensor + Number (FC16) |
| `conductivity_setpoint` | 401018 | 1017 | RW | Sensor + Number (FC16) |
| `conductivity_xp` | 401020 | 1019 | RW | Sensor + Number (FC16) |
| `conductivity_tn` | 401022 | 1021 | RW | Sensor + Number (FC16) |
| `chlorine_min1` | 401050 | 1049 | RW | Sensor + Number (FC16) |
| `chlorine_max1` | 401052 | 1051 | RW | Sensor + Number (FC16) |
| `chlorine_hyst1` | 401054 | 1053 | RW | Sensor + Number (FC16) |
| `chlorine_min2` | 401056 | 1055 | RW | Sensor + Number (FC16) |
| `chlorine_max2` | 401058 | 1057 | RW | Sensor + Number (FC16) |
| `chlorine_hyst2` | 401060 | 1059 | RW | Sensor + Number (FC16) |
| `ph_min1` | 401062 | 1061 | RW | Sensor + Number (FC16) |
| `ph_max1` | 401064 | 1063 | RW | Sensor + Number (FC16) |
| `ph_hyst1` | 401066 | 1065 | RW | Sensor + Number (FC16) |
| `ph_min2` | 401068 | 1067 | RW | Sensor + Number (FC16) |
| `ph_max2` | 401070 | 1069 | RW | Sensor + Number (FC16) |
| `ph_hyst2` | 401072 | 1071 | RW | Sensor + Number (FC16) |
| `orp_min1` | 401074 | 1073 | RW | Sensor + Number (FC16) |
| `orp_max1` | 401076 | 1075 | RW | Sensor + Number (FC16) |
| `orp_hyst1` | 401078 | 1077 | RW | Sensor + Number (FC16) |
| `orp_min2` | 401080 | 1079 | RW | Sensor + Number (FC16) |
| `orp_max2` | 401082 | 1081 | RW | Sensor + Number (FC16) |
| `orp_hyst2` | 401084 | 1083 | RW | Sensor + Number (FC16) |
| `total_chlorine_min1` | 401086 | 1085 | RW | Sensor + Number (FC16) |
| `total_chlorine_max1` | 401088 | 1087 | RW | Sensor + Number (FC16) |
| `total_chlorine_hyst1` | 401090 | 1089 | RW | Sensor + Number (FC16) |
| `total_chlorine_min2` | 401092 | 1091 | RW | Sensor + Number (FC16) |
| `total_chlorine_max2` | 401094 | 1093 | RW | Sensor + Number (FC16) |
| `total_chlorine_hyst2` | 401096 | 1095 | RW | Sensor + Number (FC16) |
| `conductivity_min1` | 401098 | 1097 | RW | Sensor + Number (FC16) |
| `conductivity_max1` | 401100 | 1099 | RW | Sensor + Number (FC16) |
| `conductivity_hyst1` | 401102 | 1101 | RW | Sensor + Number (FC16) |
| `conductivity_min2` | 401104 | 1103 | RW | Sensor + Number (FC16) |
| `conductivity_max2` | 401106 | 1105 | RW | Sensor + Number (FC16) |
| `conductivity_hyst2` | 401108 | 1107 | RW | Sensor + Number (FC16) |
| `temperature_min1` | 401110 | 1109 | RW | Sensor + Number (FC16) |
| `temperature_max1` | 401112 | 1111 | RW | Sensor + Number (FC16) |
| `temperature_hyst1` | 401114 | 1113 | RW | Sensor + Number (FC16) |

## Text und Status

| Inhalt | Handbuch | Wire | Format / Darstellung |
|---|---:|---:|---|
| Systemname | 400001 | 0 | ASCII 20 Byte, Sensor |
| Software | 400011 | 10 | ASCII 10 Byte, Sensor |
| Datum | 400016 | 15 | ASCII 10 Byte, Sensor |
| Zeit | 400021 | 20 | ASCII 6 Byte, Sensor |
| `chlorine_unit` | 400102 | 101 | ASCII 10 Byte, Einheit am Messwert und Diagnosesensor |
| `ph_unit` | 400117 | 116 | ASCII 10 Byte, Einheit am Messwert und Diagnosesensor |
| `orp_unit` | 400132 | 131 | ASCII 10 Byte, Einheit am Messwert und Diagnosesensor |
| `total_chlorine_unit` | 400147 | 146 | ASCII 10 Byte, Einheit am Messwert und Diagnosesensor |
| `conductivity_unit` | 400162 | 161 | ASCII 10 Byte, Einheit am Messwert und Diagnosesensor |
| `temperature_unit` | 400177 | 176 | ASCII 10 Byte, Einheit am Messwert und Diagnosesensor |
| `circulation_unit` | 400207 | 206 | ASCII 10 Byte, Einheit am Messwert und Diagnosesensor |
| `analog_input_2_unit` | 400222 | 221 | ASCII 10 Byte, Einheit am Messwert und Diagnosesensor |
| `alarm_word` | 400300 | 299 | UINT16, Diagnose; Bits als Zustände/Attribute |
| `input_word` | 400301 | 300 | UINT16, Diagnose; Bits als Zustände/Attribute |
| `relay_word` | 400302 | 301 | UINT16, Diagnose; Bits als Zustände/Attribute |
| `aux_relay_word` | 400303 | 302 | UINT16, Diagnose; Bits als Zustände/Attribute |
| `chlorine_mode_code` | 400304 | 303 | UINT16, Diagnose; Bits als Zustände/Attribute |
| `ph_mode_code` | 400305 | 304 | UINT16, Diagnose; Bits als Zustände/Attribute |
| `total_chlorine_mode_code` | 400306 | 305 | UINT16, Diagnose; Bits als Zustände/Attribute |
| `conductivity_mode_code` | 400307 | 306 | UINT16, Diagnose; Bits als Zustände/Attribute |
| `chlorine_error_code` | 400308 | 307 | UINT32, Fehlertext + `active_flags` + Störung |
| `ph_error_code` | 400310 | 309 | UINT32, Fehlertext + `active_flags` + Störung |
| `orp_error_code` | 400312 | 311 | UINT32, Fehlertext + `active_flags` + Störung |
| `total_chlorine_error_code` | 400314 | 313 | UINT32, Fehlertext + `active_flags` + Störung |
| `conductivity_error_code` | 400316 | 315 | UINT32, Fehlertext + `active_flags` + Störung |
| Stoßchlorung Start/Stopp | 402000 | 1999 | UINT16 RW, Bit 9 (0x0200), Button (FC06) + Diagnose |

Alarm 1–8: 400300 Bits 0–7; DI1–3: 400301 Bits 0–2, Messwasser-Stopp Bit 3.
Relais K1–K8: 400302 Bits 0–7; K21–K24: 400303 Bits 0–3. Ausschließlich R.
Alle 16 Betriebsartbits und alle 32 Fehlerbits werden vollständig in `active_flags` ausgegeben;
unbenannte Fehlerbits bleiben als unbekanntes Bit erkennbar. Stoßchlorung aktiv: 400304 Bit 15.

## Schreibverhalten

45 FLOAT-Bedienelemente: 12 Regelparameter und 33 Grenzen/Hysteresen. Ein Start/Stopp-Button.
Nur auf ausdrückliche Bedienung; keine Schreibzugriffe beim Einrichten, Starten oder Abfragen.
Vor Zahlenänderungen werden Identität, aktueller Wert und nötige Grenzen frisch gelesen.
Xp 0–1000 %, Tn 0–100 min (0 deaktiviert Tn). Sollwert im Gerätemessbereich;
Min/Max innerhalb des Messbereichs und des zugehörigen Grenzwertpaars.

Hysterese wird als unveränderter FLOAT in der Geräteeinheit angeboten. Die Anleitung nennt
1–25 Anzeigedigits; die variable Anzeigeschrittweite ist nicht per Modbus dokumentiert.
Darum erfolgt keine erfundene Digit-Umrechnung. HA prüft positiv und höchstens Messbereichsspanne;
die konkrete 1–25-Digit-Grenze muss am Gerät geprüft werden. Nur vom Gerät exakt zurückgelesene
FLOAT-Werte gelten als bestätigt. Ein abweichender oder verworfener Wert ergibt einen Fehler.

FLOAT wird atomar über FC16 in zwei Register geschrieben. Identische kodierte Werte werden übersprungen.
Höchstens ein Schreibversuch pro Sekunde. Auch nach Timeout kein automatischer Wiederholversuch.
Nach Fehlern wird nur lesend aktualisiert; ein Timeout kann trotz fehlender Bestätigung bereits wirksam sein.

Der Button sendet den dokumentierten Start/Stopp-Befehl als FC06 und erhält andere Bits des frisch
gelesenen Funktionswortes. Keine erfundene getrennte Start-/Stop-Zuordnung, kein automatisches
Rücksetzen, keine Wiederholung bei noch gesetztem Befehlsbit. Die bestätigte FC06-Antwort ist
keine Bestätigung des Prozessstarts; dafür den separaten Iststatus und die Anlage prüfen.

Die Anleitung warnt vor Speicherschäden durch zyklisches bzw. wiederholtes Schreiben gleicher Werte.
Automationen sollen nur bewusste Änderungen auslösen. Die Integration ersetzt keine Geräteschutzfunktionen.
