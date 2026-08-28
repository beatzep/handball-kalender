#!/usr/bin/env python3
"""Erzeugt die Commit-Nachricht fuer den naechtlichen Lauf.

Der Betreff ist kurz genug fuer die GitHub-Oberflaeche, die Details stehen im
Rumpf. Wer das Repo auf "Watch" hat, sieht Verlegungen so in der
Benachrichtigung, ohne die Seite aufzurufen.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BETREFF = {
    "verlegt": "Spieltag {spieltag} verlegt",
    "halle": "Spieltag {spieltag}: andere Halle",
    "neu": "Neues Spiel im Spielplan",
    "entfallen": "Spiel entfaellt",
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--daten", default="docs/daten.json")
    cfg = p.parse_args()

    daten = json.loads(Path(cfg.daten).read_text(encoding="utf-8"))
    aenderungen = []
    for team in (daten.get("teams") or {}).values():
        for a in team.get("letzte_aenderungen") or []:
            aenderungen.append(dict(a, mannschaft=team.get("name", "")))
    heute = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%d.%m.%Y")

    if not aenderungen:
        print(f"Abgleich {heute}: keine Aenderungen")
        return

    if len(aenderungen) == 1:
        a = aenderungen[0]
        betreff = f"{a['mannschaft']}: " + BETREFF.get(
            a["art"], "Spielplan geaendert").format(spieltag=a.get("spieltag") or "?")
    else:
        betreff = f"{len(aenderungen)} Aenderungen im Spielplan"

    print(betreff)
    print()
    for a in aenderungen:
        print(f"- {a['mannschaft']}: {a['text']}")


if __name__ == "__main__":
    main()
