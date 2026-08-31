#!/usr/bin/env python3
"""Grober Audit der Grundfunktionen: Daten, Kalender und Seite.

Prueft das, was im Betrieb still kaputtgehen kann - falsche Zeiten,
doppelte Termin-Kennungen, fehlende Adressen, tote Verweise.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")
DOCS = Path("docs")
fehler: list[str] = []
warnung: list[str] = []


def pruefe(bedingung: bool, text: str, hart: bool = True) -> None:
    if not bedingung:
        (fehler if hart else warnung).append(text)


def main() -> int:
    daten = json.loads((DOCS / "daten.json").read_text(encoding="utf-8"))
    teams = daten.get("teams") or {}
    konfig = json.loads(Path("teams.json").read_text(encoding="utf-8"))

    heute = datetime.now(TZ)
    print(f"Mannschaften: {len(teams)}")
    pruefe(len(teams) == len(konfig["teams"]),
           f"{len(konfig['teams'])} Mannschaften konfiguriert, {len(teams)} in den Daten")

    alle_uids: list[str] = []
    for schluessel, team in teams.items():
        spiele = list((team.get("spiele") or {}).values())
        print(f"\n{team['name']} ({schluessel}) - {len(spiele)} Spiele, {team.get('liga')}")

        pruefe(bool(spiele), f"{schluessel}: keine Spiele")
        pruefe(bool(team.get("liga")), f"{schluessel}: keine Liga hinterlegt", hart=False)

        # Turnierspiele stehen beim Verband ohne Uhrzeit und oft ohne Halle -
        # das ist kein Fehler, sondern schlicht noch nicht angesetzt.
        offen = [s for s in spiele if s.get("ohne_zeit")]
        if offen:
            print(f"  {len(offen)} Spiele noch ohne Ansetzung (Uhrzeit offen)")

        ohne_ort = [s for s in spiele if not s.get("ort") and not s.get("ohne_zeit")]
        pruefe(not ohne_ort, f"{schluessel}: {len(ohne_ort)} angesetzte Spiele ohne Adresse",
               hart=False)

        # Anwurfzeiten muessen plausibel sein - faengt Zeitzonenfehler ab
        for s in spiele:
            if s.get("ohne_zeit"):
                continue
            t = datetime.fromisoformat(s["datum"])
            pruefe(8 <= t.hour <= 22,
                   f"{schluessel}: Anwurf {t:%d.%m. %H:%M} unplausibel (Zeitzone?)")

        # Heim/Auswaerts muss ausgewogen sein
        heim = sum(1 for s in spiele if s.get("heim"))
        pruefe(abs(heim - (len(spiele) - heim)) <= 2,
               f"{schluessel}: {heim} Heim / {len(spiele)-heim} Auswärts - unausgewogen",
               hart=False)

        # --- Datenqualitaet der Verbandsangaben ---
        # Diese Pruefungen gibt es, weil zwei Hallen mit Koordinaten 0/0
        # gefuehrt waren: Das stand als Navigationsziel in den Kalendern und
        # ergab Fahrtstrecken von 7.000 km, ohne dass es jemand bemerkt haette.
        for s in spiele:
            kennung = f"{schluessel} {s.get('datum','?')[:10]}"
            if not s.get("ohne_zeit"):
                pruefe(bool(s.get("halle")), f"{kennung}: Halle ohne Namen", hart=False)
            pruefe(s.get("gegner") not in (None, "", "Unbekannt"),
                   f"{kennung}: Gegner nicht benannt")
            pruefe(bool(s.get("match_id")),
                   f"{kennung}: keine Spielkennung - Verweis auf handball.net fehlt",
                   hart=False)
            if s.get("lat") is not None:
                pruefe(47.0 <= float(s["lat"]) <= 55.5 and 5.0 <= float(s["lon"]) <= 16.0,
                       f"{kennung}: Koordinaten ausserhalb Deutschlands "
                       f"({s['lat']}/{s['lon']})")

        # Laengst gespielte Partien ohne Ergebnis deuten auf eine Luecke beim
        # Verband hin - oder darauf, dass unser Abgleich nicht mehr laeuft.
        ueberfaellig = [s for s in spiele
                        if not s.get("ergebnis") and not s.get("ohne_zeit")
                        and (heute - datetime.fromisoformat(s["datum"]).replace(tzinfo=TZ)).days > 3]
        pruefe(not ueberfaellig,
               f"{schluessel}: {len(ueberfaellig)} Spiele länger als 3 Tage vorbei, "
               f"aber ohne Ergebnis", hart=False)

        # Zwei Spiele zur selben Zeit sind bei Turnieren und Spielfesten normal
        # (mehrere Felder, kurze Spielzeiten). Verdaechtig wird es erst, wenn
        # sie in verschiedenen Hallen stattfinden sollen.
        nach_zeit: dict[str, set] = {}
        for s in spiele:
            nach_zeit.setdefault(s["datum"], set()).add(s.get("halle") or "?")
        unmoeglich = [t for t, hallen in nach_zeit.items() if len(hallen) > 1]
        pruefe(not unmoeglich,
               f"{schluessel}: gleichzeitige Spiele in verschiedenen Hallen "
               f"({unmoeglich[:2]})")

        parallel = sum(1 for t, h in nach_zeit.items()
                       if len(h) == 1 and sum(1 for s in spiele if s["datum"] == t) > 1)
        if parallel:
            print(f"  {parallel} Zeitpunkte mit mehreren Spielen (Turnierbetrieb)")

        # Tabelle
        tab = team.get("tabelle") or {}
        eintraege = tab.get("eintraege") or []
        pruefe(bool(eintraege), f"{schluessel}: keine Tabelle", hart=False)
        if eintraege:
            eigene = [e for e in eintraege if e.get("team_id") == team.get("team_id")]
            pruefe(len(eigene) == 1,
                   f"{schluessel}: eigene Mannschaft {len(eigene)}x in der Tabelle")

        # Kalenderdatei
        pfad = DOCS / team["datei"]
        pruefe(pfad.exists(), f"{schluessel}: {team['datei']} fehlt")
        if not pfad.exists():
            continue
        roh = pfad.read_bytes().decode("utf-8")
        uids = re.findall(r"^UID:(.+)$", roh, re.MULTILINE)
        alle_uids += uids
        anzahl = roh.count("BEGIN:VEVENT")
        pruefe(anzahl == len(spiele),
               f"{schluessel}: {anzahl} Termine in der .ics, aber {len(spiele)} Spiele")
        pruefe("\r\n" in roh, f"{schluessel}: keine CRLF-Zeilenenden")
        pruefe("TZID=Europe/Berlin" in roh, f"{schluessel}: keine Zeitzone gesetzt")
        for nr, zeile in enumerate(roh.split("\r\n"), 1):
            if len(zeile.encode("utf-8")) > 75:
                fehler.append(f"{schluessel}: Zeile {nr} laenger als 75 Byte")
        print(f"  .ics: {anzahl} Termine, {len(set(uids))} eindeutige Kennungen")

        # Aliasdateien muessen inhaltsgleich sein - sonst laufen alte Abos leer
        konf = next((t for t in konfig["teams"] if t["schluessel"] == schluessel), {})
        for alias in konf.get("alias") or []:
            apfad = DOCS / alias
            pruefe(apfad.exists(), f"{schluessel}: Aliasdatei {alias} fehlt")
            if apfad.exists():
                pruefe(apfad.read_bytes() == pfad.read_bytes(),
                       f"{schluessel}: Alias {alias} weicht vom Original ab")
                print(f"  Alias {alias}: inhaltsgleich")

    doppelt = [u for u, n in Counter(alle_uids).items() if n > 1]
    pruefe(not doppelt, f"Termin-Kennungen mehrfach vergeben: {doppelt[:3]}")

    # Seite
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    print(f"\nSeite: {len(html)//1024} kB")
    for schluessel in teams:
        pruefe(f'data-team="{schluessel}"' in html, f"Seite: Block für {schluessel} fehlt")
    # Uebersicht und Auswertung muessen ebenfalls erzeugt worden sein
    for weitere in ["wochenende.html", "admin.html"]:
        pruefe((DOCS / weitere).exists(), f"{weitere} fehlt")
    if (DOCS / "wochenende.html").exists():
        uebersicht = (DOCS / "wochenende.html").read_text(encoding="utf-8")
        pruefe("class=\"partie" in uebersicht,
               "wochenende.html enthält keine Spiele", hart=False)

    for datei in ["logo.png", "icon-32.png", "icon-180.png", "manifest.json"]:
        pruefe(datei in html, f"Seite: Verweis auf {datei} fehlt", hart=False)
        pruefe((DOCS / datei).exists(), f"Datei {datei} fehlt")

    # Verweise in der Seite muessen auch existieren
    for verweis in set(re.findall(r'(?:href|src)="(?!http|webcal|#)([^"]+)"', html)):
        ziel = verweis.split("?")[0]
        pruefe((DOCS / ziel).exists(), f"Seite verweist auf fehlende Datei: {ziel}")

    manifest = json.loads((DOCS / "manifest.json").read_text(encoding="utf-8"))
    for icon in manifest["icons"]:
        pruefe((DOCS / icon["src"]).exists(), f"Manifest: {icon['src']} fehlt")

    # Strassenkilometer: fehlt eine Halle im Cache, faellt sie still auf die
    # Luftlinien-Schaetzung zurueck - die lag hier durchweg 5 bis 13 Prozent
    # zu niedrig. Ohne Hinweis merkt das niemand.
    try:
        cache = json.loads(Path("strassen_cache.json").read_bytes().decode("utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        cache = {}
    hallen = {}
    for team in daten.get("teams", {}).values():
        for spiel in (team.get("spiele") or {}).values():
            if spiel.get("lat") and spiel.get("lon"):
                k = f'{float(spiel["lat"]):.5f},{float(spiel["lon"]):.5f}'
                hallen.setdefault(k, spiel.get("halle") or "?")
    ohne = {k: v for k, v in hallen.items() if k not in cache}
    if not cache:
        warnung.append("keine Strassenkilometer vorhanden - alle Entfernungen "
                       "sind Luftlinien-Schaetzungen")
    elif ohne:
        namen = ", ".join(sorted(set(ohne.values()))[:4])
        warnung.append(f"{len(ohne)} von {len(hallen)} Hallen ohne "
                       f"Strassenkilometer ({namen}) - dort wird geschaetzt")

    print()
    for w in warnung:
        print(f"  HINWEIS  {w}")
    for f in fehler:
        print(f"  FEHLER   {f}")
    if not fehler:
        print(f"  Audit bestanden ({len(warnung)} Hinweise)")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
