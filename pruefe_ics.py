#!/usr/bin/env python3
"""Prueft eine erzeugte .ics-Datei auf die Fehler, die in Kalender-Apps
typischerweise erst auffallen, wenn man zu spaet in der Halle steht."""

import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")


def zeit(wert: str) -> datetime | None:
    """Liest Zeitpunkte und reine Tagesangaben; gibt None zurueck statt zu
    werfen, damit eine kaputte Datei als Befund und nicht als Absturz erscheint."""
    roh = wert.rstrip("Z")
    for muster in ("%Y%m%dT%H%M%S", "%Y%m%d"):
        try:
            return datetime.strptime(roh, muster)
        except ValueError:
            continue
    return None


def entfalte(roh: str) -> list[str]:
    zeilen: list[str] = []
    for zeile in roh.split("\r\n"):
        if zeile.startswith(" ") and zeilen:
            zeilen[-1] += zeile[1:]
        else:
            zeilen.append(zeile)
    return [z for z in zeilen if z]


def main(pfad: str) -> int:
    # Bewusst read_bytes: read_text() wuerde CRLF still zu LF uebersetzen und
    # die Pruefung auf RFC-konforme Zeilenenden ins Leere laufen lassen. Der
    # newline-Parameter von read_text existiert zudem erst ab Python 3.13.
    roh = Path(pfad).read_bytes().decode("utf-8")
    fehler: list[str] = []
    warnung: list[str] = []

    # 1. Zeilenenden und Zeilenlaenge (RFC 5545)
    if "\r\n" not in roh:
        fehler.append("Datei benutzt keine CRLF-Zeilenenden")
    for nr, zeile in enumerate(roh.split("\r\n"), 1):
        if len(zeile.encode("utf-8")) > 75:
            fehler.append(f"Zeile {nr} ist {len(zeile.encode('utf-8'))} Byte lang (max 75)")

    zeilen = entfalte(roh)

    # 2. Struktur
    for anfang, ende in (("BEGIN:VCALENDAR", "END:VCALENDAR"),):
        if zeilen[0] != anfang or zeilen[-1] != ende:
            fehler.append(f"Datei ist nicht in {anfang}/{ende} eingefasst")
    offen = Counter()
    for zeile in zeilen:
        if zeile.startswith("BEGIN:"):
            offen[zeile[6:]] += 1
        elif zeile.startswith("END:"):
            offen[zeile[4:]] -= 1
    if any(offen.values()):
        fehler.append(f"unausgeglichene BEGIN/END-Bloecke: {dict(offen)}")

    # 3. Events einsammeln
    events, aktuell = [], None
    for zeile in zeilen:
        if zeile == "BEGIN:VEVENT":
            aktuell = {}
        elif zeile == "END:VEVENT":
            events.append(aktuell)
            aktuell = None
        elif aktuell is not None and ":" in zeile:
            schluessel, _, wert = zeile.partition(":")
            aktuell.setdefault(schluessel.split(";")[0], []).append((schluessel, wert))

    if not events:
        fehler.append("keine VEVENTs gefunden")

    # 4. Pflichtfelder und Zeitzone
    uids = []
    for i, ev in enumerate(events, 1):
        for pflicht in ("UID", "DTSTAMP", "DTSTART", "SUMMARY"):
            if pflicht not in ev:
                fehler.append(f"Event {i}: {pflicht} fehlt")
        if "UID" in ev:
            uids.append(ev["UID"][0][1])
        if "DTSTART" in ev:
            schluessel, wert = ev["DTSTART"][0]
            # Spiele ohne angesetzte Uhrzeit stehen als Tagestermin - dort
            # ist eine Zeitzone weder noetig noch erlaubt.
            ganztags = "VALUE=DATE" in schluessel
            if not ganztags and "TZID=Europe/Berlin" not in schluessel:
                fehler.append(f"Event {i}: DTSTART ohne TZID=Europe/Berlin ({schluessel})")
            if ganztags and not re.fullmatch(r"\d{8}", wert):
                fehler.append(f"Event {i}: Tagestermin mit ungültigem Datum ({wert})")
            if wert.endswith("Z"):
                fehler.append(f"Event {i}: DTSTART als UTC statt Ortszeit")
        if "DTSTART" in ev and "DTEND" in ev:
            s, e = zeit(ev["DTSTART"][0][1]), zeit(ev["DTEND"][0][1])
            if s and e and e <= s:
                fehler.append(f"Event {i}: DTEND liegt nicht nach DTSTART")

    doppelt = [u for u, n in Counter(uids).items() if n > 1]
    if doppelt:
        fehler.append(f"doppelte UIDs (erzeugen Duplikate im Kalender): {doppelt}")

    # 5. Plausibilitaet der Anwurfzeiten
    for i, ev in enumerate(events, 1):
        if "DTSTART" not in ev:
            continue
        if "VALUE=DATE" in ev["DTSTART"][0][0]:
            continue          # Tagestermin: es gibt keine Anwurfzeit zu pruefen
        start = zeit(ev["DTSTART"][0][1])
        if start is None:
            continue
        start = start.replace(tzinfo=TZ)
        if not (8 <= start.hour <= 22):
            warnung.append(f"Event {i}: Anwurf um {start:%H:%M} - unplausibel, "
                           f"Verdacht auf Zeitzonenfehler")
        if start.weekday() < 4:
            warnung.append(f"Event {i}: {start:%A %d.%m.} - Spiel unter der Woche?")

    # 6. Inhaltliche Vollstaendigkeit
    ohne_ort = sum(1 for ev in events if "LOCATION" not in ev)
    if ohne_ort:
        warnung.append(f"{ohne_ort} Events ohne LOCATION (Navi funktioniert nicht)")
    ohne_geo = sum(1 for ev in events if "GEO" not in ev)
    if ohne_geo:
        warnung.append(f"{ohne_geo} Events ohne GEO-Koordinaten")
    grossschrift = [ev["LOCATION"][0][1] for ev in events
                    if "LOCATION" in ev and ev["LOCATION"][0][1].isupper()]
    if grossschrift:
        warnung.append(f"{len(grossschrift)} Ortsangaben noch in GROSSSCHRIFT")

    print(f"{Path(pfad).name}: {len(events)} Termine geprueft")
    for w in warnung:
        print(f"  HINWEIS  {w}")
    for f in fehler:
        print(f"  FEHLER   {f}")
    if not fehler and not warnung:
        print("  alles in Ordnung")
    elif not fehler:
        print("  keine Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "dist/spielplan.ics"))
