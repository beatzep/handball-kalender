#!/usr/bin/env python3
"""Prueft, ob jeder Verweis auf eine Mannschaft auch dort ankommt.

Ein Tippfehler im Schluessel faellt sonst niemandem auf: die Seite zeigt
dann stumm die erste Mannschaft, statt einen Fehler zu melden.
"""

import re
import sys
from pathlib import Path


def lies(pfad: str) -> str:
    return Path(pfad).read_bytes().decode("utf-8")


def main() -> int:
    seite = lies("docs/index.html")
    # Nur echte Schluessel: im Skript steht auch data-team="' + schluessel + '"
    vorhanden = set(re.findall(r'data-team="([a-z0-9-]+)"', seite))
    vorhanden.discard("meine")          # kein Spielplan, sondern der Sammelblick
    if not vorhanden:
        print("FEHLER: keine Mannschaften in docs/index.html gefunden")
        return 1

    fehler: list[str] = []
    gepruefte = 0

    # Wochenend-Uebersicht: index.html#<schluessel>
    uebersicht = lies("docs/wochenende.html")
    verweise = re.findall(r'href="index\.html#([^"]+)"', uebersicht)
    gepruefte += len(verweise)
    for ziel in set(verweise):
        if ziel.split("/")[0] not in vorhanden:
            fehler.append(f"wochenende.html verweist auf '{ziel}' - "
                          f"diese Mannschaft gibt es auf index.html nicht")
    if not verweise:
        fehler.append("wochenende.html enthaelt keinen einzigen Mannschaftsverweis")

    # Jede Partie muss einen Verweis tragen, sonst ist eine Zeile stumm
    partien = uebersicht.count('class="partie')
    if partien != len(verweise):
        fehler.append(f"{partien} Partien, aber {len(verweise)} Verweise - "
                      f"{partien - len(verweise)} Zeile(n) ohne Weg zur Mannschaft")

    # "Meine Mannschaften" verweist innerhalb der Seite: #<schluessel>
    for ziel in set(re.findall(r"href=.#. \+ esc\(s\.roh\.m\)", seite)):
        gepruefte += 1                 # im Skript erzeugt, Ziel erst zur Laufzeit
    if 'class="zurmannschaft"' not in seite:
        fehler.append("index.html enthaelt keinen Verweis aus 'Meine Mannschaften'")
    # Genau den Ereignisnamen suchen: "hashchange" allein traefe auch auf
    # einen Tippfehler wie "hashchangeX" zu.
    if "addEventListener('hashchange'" not in seite:
        fehler.append("index.html reagiert nicht auf Adressaenderungen - "
                      "Verweise innerhalb der Seite blieben wirkungslos")

    # Die Ruecktueren muessen ebenfalls stehen
    if 'href="wochenende.html"' not in seite:
        fehler.append("index.html hat keinen Weg zurueck zur Wochenend-Uebersicht")

    print(f"{gepruefte} Verweise geprueft, {len(vorhanden)} Mannschaften vorhanden")
    for f in fehler:
        print(f"  FEHLER   {f}")
    if not fehler:
        print("  Jeder Verweis kommt an, und der Weg zurueck steht")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
