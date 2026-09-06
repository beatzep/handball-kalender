#!/usr/bin/env python3
"""Prueft, ob der Hinweis auf einen Tabellenrueckstand richtig gesetzt ist.

Der Verband pflegt Ergebnisse und Tabellenstand getrennt: das Ergebnis steht
sofort beim Spiel, in der Tabelle erscheint es teils Tage spaeter. Ohne
Hinweis sieht es aus, als haette die Mannschaft ihren Sieg verschlafen.

Der Vergleich darf dabei nur Spiele desselben Wettbewerbs zaehlen. Die
gD-Jugend hatte am 16.08. drei Spiele eines Qualifikationsturniers, die in
der Bezirksliga-Tabelle nichts zu suchen haben - ein Vergleich ueber alle
Spiele meldete dort einen Rueckstand von drei, den es nicht gab.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import spielplan2ics as sp


def main() -> int:
    daten = json.loads(Path("docs/daten.json").read_bytes().decode("utf-8"))
    teams = {t["schluessel"]: t["team_id"] for t in
             json.loads(Path("teams.json").read_bytes().decode("utf-8"))["teams"]}
    fehler: list[str] = []
    hinweise: list[str] = []
    ohne_phase = 0

    for schluessel, team in daten.get("teams", {}).items():
        tabelle = team.get("tabelle") or {}
        if not tabelle.get("eintraege"):
            continue
        tid = teams.get(schluessel)
        spiele = team.get("spiele") or {}

        if not tabelle.get("phase_id"):
            ohne_phase += 1
            if tabelle.get("fehlend"):
                fehler.append(f"{team['name']}: Rueckstand gemeldet, aber der "
                              f"Wettbewerb der Tabelle ist unbekannt")
            continue

        # Der Vergleich, unabhaengig vom Generator noch einmal gerechnet
        eigene = next((e for e in tabelle["eintraege"] if e.get("team_id") == tid), None)
        if not eigene:
            continue
        liga = [s for s in spiele.values()
                if s.get("ergebnis") and s.get("phase_id") == tabelle["phase_id"]]
        erwartet = max(0, len(liga) - int(eigene.get("spiele") or 0))
        gemeldet = len(tabelle.get("fehlend") or [])
        if erwartet != gemeldet:
            fehler.append(f"{team['name']}: {gemeldet} Spiele als fehlend gemeldet, "
                          f"rechnerisch sind es {erwartet}")

        # Ein gemeldetes Spiel muss auch wirklich zur Liga gehoeren
        for f in tabelle.get("fehlend") or []:
            passend = [s for s in liga if s["datum"] == f["datum"]]
            if not passend:
                fehler.append(f"{team['name']}: gemeldetes Spiel vom "
                              f"{f['datum'][:10]} gehoert nicht zu dieser Liga")
        if gemeldet:
            hinweise.append(f"{team['name']}: {gemeldet} Spiel(e) noch nicht "
                            f"in der Tabelle")

    print(f"Tabellen geprueft, {ohne_phase} ohne Wettbewerbsangabe")
    for h in hinweise:
        print(f"  HINWEIS  {h}")
    for f in fehler:
        print(f"  FEHLER   {f}")
    if not fehler:
        print("  Jeder gemeldete Rueckstand stimmt mit den Spielen ueberein")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
