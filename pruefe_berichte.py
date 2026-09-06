#!/usr/bin/env python3
"""Prueft die Spielberichte gegen die Endstaende aus dem Spielplan.

Der Bericht ist die Grundlage jeder Einzelstatistik. Zaehlt man seine Tore
zusammen und kommt etwas anderes heraus als der Endstand, dann ist eine der
beiden Quellen unbrauchbar - und jede Torschuetzenliste daraus waere
falsch, ohne dass es jemandem auffiele.

Lieber gar keine Zahl als eine falsche: Ein Bericht, der diese Pruefung
nicht besteht, gehoert von der Auswertung ausgeschlossen und auf der Seite
als "liegt bei handball.net noch nicht vollstaendig vor" benannt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    daten = json.loads(Path("docs/daten.json").read_bytes().decode("utf-8"))
    try:
        cache = json.loads(Path("berichte_cache.json").read_bytes().decode("utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        print("Noch keine Spielberichte vorhanden.")
        return 0

    teams = {t["schluessel"]: t["team_id"] for t in
             json.loads(Path("teams.json").read_bytes().decode("utf-8"))["teams"]}

    fehler: list[str] = []
    hinweise: list[str] = []
    geprueft = ohne_bericht = 0

    for schluessel, team in (daten.get("teams") or {}).items():
        tid = teams.get(schluessel)
        for spiel in (team.get("spiele") or {}).values():
            mid = str(spiel.get("match_id") or "")
            if mid not in cache or not spiel.get("ergebnis"):
                continue
            bericht = cache[mid]
            if bericht.get("ohne_bericht"):
                ohne_bericht += 1
                continue
            ereignisse = bericht.get("ereignisse") or []
            geprueft += 1
            name = f"{team['name']} {spiel['datum'][:10]}"

            # 1. Tore zaehlen und mit dem Endstand vergleichen
            eigene = sum(1 for e in ereignisse
                         if e.get("ist_tor") and e.get("team_id") == tid)
            fremde = sum(1 for e in ereignisse
                         if e.get("ist_tor") and e.get("team_id") != tid
                         and e.get("team_id") is not None)
            soll = spiel["ergebnis"]
            if eigene != soll["eigene"] or fremde != soll["fremde"]:
                fehler.append(f"{name}: Bericht zaehlt {eigene}:{fremde}, "
                              f"der Endstand ist {soll['eigene']}:{soll['fremde']}")
                continue

            # 2. Jedes Tor braucht einen Schuetzen, sonst fehlt er in der Liste
            ohne_spieler = [e for e in ereignisse
                            if e.get("ist_tor") and e.get("team_id") == tid
                            and not (e.get("spieler") or {}).get("nachname")]
            if ohne_spieler:
                hinweise.append(f"{name}: {len(ohne_spieler)} eigene Tore ohne "
                                f"Schuetzen im Bericht")

            # 3. Der Spielstand im Bericht muss monoton wachsen
            vorher = (0, 0)
            for e in ereignisse:
                stand = e.get("stand")
                if not stand or stand[0] is None or stand[1] is None:
                    continue
                jetzt = (stand[0], stand[1])
                if jetzt[0] < vorher[0] or jetzt[1] < vorher[1]:
                    fehler.append(f"{name}: Spielstand springt zurueck "
                                  f"({vorher} -> {jetzt}) in Minute {e.get('minute')}")
                    break
                vorher = jetzt

            # 4. Der letzte Stand muss der Endstand sein
            staende = [e["stand"] for e in ereignisse
                       if e.get("stand") and e["stand"][0] is not None]
            if staende:
                letzter = staende[-1]
                heim, gast = ((soll["eigene"], soll["fremde"]) if spiel.get("heim")
                              else (soll["fremde"], soll["eigene"]))
                if letzter != [heim, gast]:
                    fehler.append(f"{name}: letzter Stand im Bericht {letzter}, "
                                  f"Endstand waere {[heim, gast]}")

    print(f"{geprueft} Spielberichte geprueft"
          + (f", {ohne_bericht} Ligen ohne Bericht" if ohne_bericht else ""))
    for h in hinweise:
        print(f"  HINWEIS  {h}")
    for f in fehler:
        print(f"  FEHLER   {f}")
    if not fehler:
        print("  Jeder Bericht deckt sich mit dem Endstand aus dem Spielplan")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
