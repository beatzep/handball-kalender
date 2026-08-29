#!/usr/bin/env python3
"""Gleicht die erzeugten Kalenderdateien gegen handball.net ab.

Bewusst unabhaengig vom Generator: Es wird frisch bei der API gefragt und
die fertige .ics gelesen. Ein Fehler in der Verarbeitung faellt hier auf,
weil beide Seiten getrennt ermittelt werden - nicht aus derselben Quelle
im Speicher stammen.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

API = "https://www.handball.net/api/new"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")


def hole(pfad: str) -> dict:
    req = urllib.request.Request(f"{API}/{pfad}", headers={
        "accept": "application/json", "user-agent": UA,
        "referer": "https://www.handball.net/"})
    with urllib.request.urlopen(req, timeout=30) as a:
        return json.load(a)


def entfalte(roh: str) -> list[str]:
    zeilen: list[str] = []
    for z in roh.split("\r\n"):
        if z.startswith(" ") and zeilen:
            zeilen[-1] += z[1:]
        else:
            zeilen.append(z)
    return zeilen


def lies_ics(pfad: Path) -> dict[str, dict]:
    """Termine aus der Datei, gekeyt auf die Spielnummer aus der UID."""
    termine, aktuell = {}, None
    for zeile in entfalte(pfad.read_bytes().decode("utf-8")):
        if zeile == "BEGIN:VEVENT":
            aktuell = {}
        elif zeile == "END:VEVENT":
            if aktuell and aktuell.get("code"):
                termine[aktuell["code"]] = aktuell
            aktuell = None
        elif aktuell is not None:
            if zeile.startswith("UID:"):
                aktuell["code"] = zeile[4:].split("@")[0]
            elif zeile.startswith("DTSTART"):
                schluessel, _, wert = zeile.partition(":")
                aktuell["ganztags"] = "VALUE=DATE" in schluessel
                aktuell["start"] = wert
            elif zeile.startswith("SUMMARY:"):
                aktuell["titel"] = zeile[8:]
            elif zeile.startswith("LOCATION:"):
                aktuell["ort"] = zeile[9:].replace("\\,", ",")
            elif zeile.startswith("DESCRIPTION:"):
                aktuell["text"] = zeile[12:]
    return termine


def rohzeit(iso: str) -> str:
    """Der Zeitanteil, wie ihn die API liefert - ohne Zeitzonenumrechnung."""
    return iso[:19].replace("-", "").replace(":", "")


def main() -> int:
    konfig = json.loads(Path("teams.json").read_text(encoding="utf-8"))
    fehler: list[str] = []
    warnung: list[str] = []
    gesamt_spiele = 0

    for team in konfig["teams"]:
        name, tid = team["name"], team["team_id"]
        datei = Path("docs") / team["datei"]
        if not datei.exists():
            fehler.append(f"{name}: {team['datei']} fehlt")
            continue

        api_spiele = hole(f"matches?team_id={tid}")["data"]
        ics = lies_ics(datei)
        gesamt_spiele += len(api_spiele)

        # 1. Vollstaendigkeit
        api_codes = {s.get("code") or str(s["id"]) for s in api_spiele}
        if api_codes != set(ics):
            fehlend = api_codes - set(ics)
            zuviel = set(ics) - api_codes
            if fehlend:
                fehler.append(f"{name}: {len(fehlend)} Spiele fehlen im Kalender "
                              f"({sorted(fehlend)[:2]})")
            if zuviel:
                fehler.append(f"{name}: {len(zuviel)} Termine ohne Entsprechung "
                              f"bei handball.net ({sorted(zuviel)[:2]})")

        # 2. Zeitpunkt, Gegner, Halle je Spiel
        for spiel in api_spiele:
            code = spiel.get("code") or str(spiel["id"])
            eintrag = ics.get(code)
            if not eintrag:
                continue

            roh = rohzeit(spiel["date"])
            mitternacht = roh[9:] == "000000"
            if mitternacht:
                if not eintrag["ganztags"]:
                    fehler.append(f"{name} {code}: ohne Anwurfzeit, aber kein Tagestermin")
                elif eintrag["start"] != roh[:8]:
                    fehler.append(f"{name} {code}: Datum {eintrag['start']} statt {roh[:8]}")
            else:
                if eintrag["ganztags"]:
                    fehler.append(f"{name} {code}: Tagestermin trotz Anwurfzeit {roh}")
                elif eintrag["start"] != roh:
                    fehler.append(f"{name} {code}: Zeit {eintrag['start']} statt {roh} "
                                  f"(API: {spiel['date']})")

            # Gegner muss im Titel vorkommen
            heim = (spiel.get("local") or {}).get("id") == tid
            gegner_roh = ((spiel.get("visitor") if heim else spiel.get("local")) or {}).get("name", "")
            kern = re.sub(r"[^a-zA-ZäöüÄÖÜß]", "", gegner_roh.split("/")[0])[:6].lower()
            if kern and kern not in re.sub(r"[^a-zA-ZäöüÄÖÜß]", "", eintrag.get("titel", "")).lower():
                warnung.append(f"{name} {code}: Gegner '{gegner_roh}' nicht im Titel "
                               f"'{eintrag.get('titel','')}'")

            # Halle
            halle_roh = (((spiel.get("field") or {}).get("installation")) or {}).get("name") or ""
            if halle_roh:
                kern_h = re.sub(r"[^a-zA-ZäöüÄÖÜß]", "", halle_roh)[:6].lower()
                vorhanden = re.sub(r"[^a-zA-ZäöüÄÖÜß]", "", eintrag.get("ort", "")).lower()
                if kern_h and kern_h not in vorhanden:
                    warnung.append(f"{name} {code}: Halle '{halle_roh}' nicht in "
                                   f"'{eintrag.get('ort','')}'")

            # Ergebnis
            fertig = (spiel.get("status") or {}).get("is_finished")
            r = spiel.get("result") or {}
            if fertig and r.get("local") is not None:
                stand = f'{r["local"]}:{r["visitor"]}'
                if stand not in eintrag.get("titel", ""):
                    fehler.append(f"{name} {code}: Endstand {stand} fehlt im Titel "
                                  f"'{eintrag.get('titel','')}'")

        print(f"  {name:<15} {len(api_spiele):3} bei handball.net, "
              f"{len(ics):3} im Kalender")

    print(f"\n{gesamt_spiele} Spiele abgeglichen")
    for w in warnung[:15]:
        print(f"  HINWEIS  {w}")
    if len(warnung) > 15:
        print(f"  ... und {len(warnung) - 15} weitere Hinweise")
    for f in fehler:
        print(f"  FEHLER   {f}")
    if not fehler:
        print(f"\n  Kein Abweichung gefunden ({len(warnung)} Hinweise)")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
