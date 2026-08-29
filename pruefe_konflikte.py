#!/usr/bin/env python3
"""Prueft den Datenblock, aus dem "Meine Mannschaften" gebaut wird.

Die verschraenkte Ansicht liest nicht die Spielplaene im Dokument, sondern
eine eigene, knappe Liste. Weicht die von den Spielplaenen ab, zeigt die
Seite an zwei Stellen Verschiedenes - und genau das faellt niemandem auf.
"""

import itertools
import json
import math
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

SPIELDAUER = 105
RUESTZEIT = 10
UMWEG = 1.3
KMH = 70


def entfernung(a, b) -> float:
    R, r = 6371, math.radians
    dla, dlo = r(b[0] - a[0]), r(b[1] - a[1])
    h = math.sin(dla / 2) ** 2 + math.cos(r(a[0])) * math.cos(r(b[0])) * math.sin(dlo / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h)) * UMWEG


def pruefe_paar(a, b):
    """Dieselbe Entscheidung wie im Browser - hier zweitens gerechnet."""
    ta, tb = datetime.fromisoformat(a["d"]), datetime.fromisoformat(b["d"])
    if a.get("k") or b.get("k"):
        return "offen"
    puffer = int((tb - (ta + timedelta(minutes=SPIELDAUER))).total_seconds() // 60)
    if a.get("p") and b.get("p"):
        weg = entfernung(a["p"], b["p"])
    elif a["h"] and a["h"] == b["h"]:
        weg = 0.0
    else:
        weg = None
    brauche = RUESTZEIT if weg is None else RUESTZEIT + round(weg / KMH * 60)
    if puffer < 0:
        return "hart"
    if weg is not None and weg < 1:
        return None
    if puffer < brauche:
        return "hart"
    if puffer < brauche + 30:
        return "knapp"
    return None


def main() -> int:
    seite = Path("docs/index.html").read_bytes().decode("utf-8")
    treffer = re.search(r'<script id="spieldaten"[^>]*>(.*?)</script>', seite, re.S)
    if not treffer:
        print("FEHLER: Datenblock fehlt in der Seite")
        return 1
    eingebettet = json.loads(treffer.group(1))
    quelle = json.loads(Path("docs/daten.json").read_bytes().decode("utf-8"))
    fehler: list[str] = []

    # 1. Vollstaendigkeit gegen die Quelle
    teams = quelle.get("teams", quelle)
    erwartet = {}
    for schluessel, team in teams.items():
        for spiel in (team.get("spiele") or {}).values():
            erwartet[(schluessel, spiel["datum"], spiel.get("gegner", ""))] = spiel
    gefunden = {(e["m"], e["d"], e["g"]): e for e in eingebettet}

    if len(eingebettet) != len(gefunden):
        fehler.append(f"{len(eingebettet) - len(gefunden)} doppelte Eintraege im Datenblock")
    for k in erwartet.keys() - gefunden.keys():
        fehler.append(f"Spiel fehlt im Datenblock: {k[0]} {k[1]} gegen {k[2]}")
    for k in gefunden.keys() - erwartet.keys():
        fehler.append(f"Spiel im Datenblock, aber nicht in den Daten: {k}")

    # 2. Feld fuer Feld
    for k, soll in erwartet.items():
        ist = gefunden.get(k)
        if not ist:
            continue
        if (ist["h"] or "") != (soll.get("halle") or ""):
            fehler.append(f"{k[0]} {k[1]}: Halle weicht ab ({ist['h']!r} statt {soll.get('halle')!r})")
        if bool(ist.get("z")) != bool(soll.get("heim")):
            fehler.append(f"{k[0]} {k[1]}: Heim/Auswaerts weicht ab")
        if bool(ist.get("k")) != bool(soll.get("ohne_zeit")):
            fehler.append(f"{k[0]} {k[1]}: Angabe zur Anwurfzeit weicht ab")
        if soll.get("lat") and soll.get("lon"):
            if not ist.get("p"):
                fehler.append(f"{k[0]} {k[1]}: Koordinaten fehlen im Datenblock")
            elif abs(ist["p"][0] - float(soll["lat"])) > 0.0001 \
                    or abs(ist["p"][1] - float(soll["lon"])) > 0.0001:
                fehler.append(f"{k[0]} {k[1]}: Koordinaten weichen ab")
        elif ist.get("p"):
            fehler.append(f"{k[0]} {k[1]}: Koordinaten im Datenblock, aber nicht in den Daten")

    # 3. Koordinaten muessen im Land liegen, sonst rechnet die Fahrzeit Unsinn
    for e in eingebettet:
        if e.get("p") and not (47.0 <= e["p"][0] <= 55.5 and 5.0 <= e["p"][1] <= 16.0):
            fehler.append(f"{e['m']} {e['d']}: Koordinaten ausserhalb Deutschlands {e['p']}")

    # 4. Die Konfliktrechnung selbst
    nach_tag: dict = {}
    for e in eingebettet:
        nach_tag.setdefault(datetime.fromisoformat(e["d"]).date(), []).append(e)
    zahl = {"hart": 0, "knapp": 0, "offen": 0}
    for tag, liste in nach_tag.items():
        liste = sorted(liste, key=lambda x: x["d"])
        for a, b in itertools.combinations(liste, 2):
            if a["m"] == b["m"]:
                continue
            art = pruefe_paar(a, b)
            if not art:
                continue
            zahl[art] += 1
            if art == "offen":
                continue
            # Gleiche Halle nacheinander darf kein Konflikt sein
            ta, tb = datetime.fromisoformat(a["d"]), datetime.fromisoformat(b["d"])
            if a.get("p") and b.get("p") and entfernung(a["p"], b["p"]) < 1 \
                    and tb >= ta + timedelta(minutes=SPIELDAUER):
                fehler.append(f"{tag}: gleiche Halle nacheinander als Konflikt gemeldet "
                              f"({a['m']} {a['d'][11:16]} / {b['m']} {b['d'][11:16]})")

    print(f"Datenblock: {len(eingebettet)} Spiele, {len(teams)} Mannschaften")
    print(f"Konflikte ueber alle Mannschaften: {zahl['hart']} hart, "
          f"{zahl['knapp']} knapp, {zahl['offen']} ohne Anwurfzeit")
    for f in fehler[:25]:
        print(f"  FEHLER   {f}")
    if len(fehler) > 25:
        print(f"  ... und {len(fehler) - 25} weitere")
    if not fehler:
        print("  Datenblock deckt sich mit den Spielplaenen")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
