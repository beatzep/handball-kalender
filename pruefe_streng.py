#!/usr/bin/env python3
"""Strenge Konformitaetspruefung fuer .ics-Dateien.

Apple Kalender ist nachsichtig, Google deutlich weniger. Geprueft wird
hier das, woran fremde Parser typischerweise scheitern - Escaping,
Zeitzonendefinitionen, Pflichtfelder, Datumsformate.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Nach RFC 5545 in TEXT-Werten zu maskieren: Backslash, Semikolon, Komma,
# Zeilenumbruch. Ein unmaskiertes Semikolon beendet fuer einen strengen
# Parser den Wert - der Rest der Zeile wird stillschweigend verschluckt.
TEXTFELDER = {"SUMMARY", "DESCRIPTION", "LOCATION", "COMMENT", "TZNAME"}
PFLICHT_EVENT = {"UID", "DTSTAMP", "DTSTART", "SUMMARY"}
ERLAUBT = {
    "BEGIN", "END", "VERSION", "PRODID", "CALSCALE", "METHOD", "UID", "DTSTAMP",
    "DTSTART", "DTEND", "SUMMARY", "DESCRIPTION", "LOCATION", "URL", "GEO",
    "SEQUENCE", "STATUS", "TRANSP", "CATEGORIES", "ACTION", "TRIGGER",
    "TZID", "TZOFFSETFROM", "TZOFFSETTO", "TZNAME", "RRULE",
    "REFRESH-INTERVAL", "X-WR-CALNAME", "X-WR-TIMEZONE", "X-WR-CALDESC",
    "X-PUBLISHED-TTL",
}


def entfalte(roh: str) -> list[str]:
    zeilen: list[str] = []
    for z in roh.split("\r\n"):
        if z.startswith(" ") and zeilen:
            zeilen[-1] += z[1:]
        else:
            zeilen.append(z)
    return [z for z in zeilen if z]


def pruefe(pfad: Path) -> list[str]:
    fehler: list[str] = []
    roh = pfad.read_bytes().decode("utf-8")
    zeilen = entfalte(roh)

    kopf = {z.split(":", 1)[0] for z in zeilen[:8]}
    for pflicht in ("VERSION", "PRODID"):
        if pflicht not in kopf:
            fehler.append(f"{pflicht} fehlt im Kalenderkopf")

    genutzte_tzid, definierte_tzid = set(), set()
    ebene, event, alarm_offen = [], None, False

    for nr, zeile in enumerate(zeilen, 1):
        name = zeile.split(":", 1)[0].split(";", 1)[0].upper()
        if name not in ERLAUBT:
            fehler.append(f"Zeile {nr}: unbekannte Eigenschaft '{name}'")

        if zeile.startswith("BEGIN:"):
            ebene.append(zeile[6:])
            if zeile == "BEGIN:VEVENT":
                event = set()
            elif zeile == "BEGIN:VALARM":
                alarm_offen = True
        elif zeile.startswith("END:"):
            if not ebene or ebene[-1] != zeile[4:]:
                fehler.append(f"Zeile {nr}: {zeile} passt nicht zu {ebene[-1:] or ['nichts']}")
            else:
                ebene.pop()
            if zeile == "END:VEVENT":
                fehlend = PFLICHT_EVENT - (event or set())
                if fehlend:
                    fehler.append(f"Termin vor Zeile {nr}: {sorted(fehlend)} fehlt")
                event = None
            elif zeile == "END:VALARM":
                alarm_offen = False
        elif event is not None and not alarm_offen:
            event.add(name)

        # Zeitzonen
        m = re.search(r";TZID=([^;:]+)", zeile)
        if m:
            genutzte_tzid.add(m.group(1))
        if name == "TZID" and ebene and "VTIMEZONE" in ebene:
            definierte_tzid.add(zeile.split(":", 1)[1])

        # Datumsformate
        if name in ("DTSTART", "DTEND", "DTSTAMP"):
            wert = zeile.split(":", 1)[1]
            gueltig = (re.fullmatch(r"\d{8}T\d{6}Z?", wert)
                       or (re.fullmatch(r"\d{8}", wert) and "VALUE=DATE" in zeile))
            if not gueltig:
                fehler.append(f"Zeile {nr}: {name} hat ungültiges Format '{wert}'")

        # Maskierung in Textfeldern
        if name in TEXTFELDER and ":" in zeile:
            wert = zeile.split(":", 1)[1]
            ohne_maskiert = re.sub(r"\\[\;,nN]", "", wert)
            for zeichen, bezeichnung in ((";", "Semikolon"), (",", "Komma")):
                if zeichen in ohne_maskiert:
                    fehler.append(f"Zeile {nr}: unmaskiertes {bezeichnung} in {name}: "
                                  f"'{wert[:60]}'")

    if ebene:
        fehler.append(f"nicht geschlossen: {ebene}")
    fehlende_tz = genutzte_tzid - definierte_tzid
    if fehlende_tz:
        fehler.append(f"TZID {sorted(fehlende_tz)} benutzt, aber kein VTIMEZONE dafür")

    return fehler


def main() -> int:
    dateien = sorted(Path("docs").glob("*.ics"))
    gesamt = 0
    for pfad in dateien:
        fehler = pruefe(pfad)
        gesamt += len(fehler)
        if fehler:
            print(f"  {pfad.name}:")
            for f in fehler[:5]:
                print(f"     {f}")
    print(f"\n{len(dateien)} Dateien streng geprüft, {gesamt} Beanstandungen")
    return 1 if gesamt else 0


if __name__ == "__main__":
    sys.exit(main())
