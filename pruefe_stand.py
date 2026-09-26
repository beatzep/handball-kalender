#!/usr/bin/env python3
"""Prueft den Hinweis fuer einen haengenden Abgleich (seite_stand.py).

Zwei Teile. Die Grenzen werden an festen Zeitpunkten nachgerechnet, mit
Node, also mit genau dem Code, der im Browser laeuft. Und jede Seite muss
den Hinweis tragen, mit dem Stand aus daten.json. Fehlt er, merkt das
sonst keiner, bis der Abgleich das naechste Mal haengt.
"""

from __future__ import annotations

import html
import json
import subprocess
import sys
from pathlib import Path

from seite_stand import AUSFUEHREN, PRUEFUNG

DOCS = Path("docs")
SEITEN = ["index.html", "wochenende.html", "torjaeger.html"]

# (Stand, jetzt, erwarteter Befund) - alles in UTC
FAELLE = [
    # Werktags: der Lauf kommt gegen 08:00 UTC, mal etwas spaeter
    ("2026-09-23T08:32:23+00:00", "2026-09-24T09:00:00Z", None),
    ("2026-08-28T09:02:00+00:00", "2026-08-29T10:01:00Z", None),   # laengste echte Luecke
    ("2026-09-23T08:32:23+00:00", "2026-09-24T10:30:00Z", "alt"),  # 24.09., Lauf gescheitert
    ("2026-09-23T08:32:23+00:00", "2026-09-26T12:00:00Z", "alt"),
    # Samstag vor 14 Uhr UTC: noch der Stand vom Morgen, das ist normal
    ("2026-09-26T08:00:00+00:00", "2026-09-26T13:30:00Z", None),
    # Samstag ab 14 Uhr UTC: stuendliche Laeufe
    ("2026-09-26T12:15:00+00:00", "2026-09-26T15:00:00Z", None),
    ("2026-09-26T11:00:00+00:00", "2026-09-26T15:00:00Z", "alt"),
    ("2026-09-26T08:00:00+00:00", "2026-09-26T14:10:00Z", "alt"),
    ("2026-09-20T21:19:00+00:00", "2026-09-20T23:50:00Z", None),   # Sonntagabend, 2,5 h
    # Montag kurz nach Mitternacht UTC gilt wieder die Tagesgrenze
    ("2026-09-20T21:19:00+00:00", "2026-09-21T00:30:00Z", None),
    # Winterzeit: gerechnet wird in UTC, das verschiebt nichts
    ("2026-11-07T12:10:00+00:00", "2026-11-07T15:30:00Z", "alt"),
    # Stand unlesbar oder Geraeteuhr falsch: nie Entwarnung
    ("", "2026-09-26T12:00:00Z", "unbekannt"),
    ("kaputt", "2026-09-26T12:00:00Z", "unbekannt"),
    ("2026-09-26T12:00:00+00:00", "2026-09-26T10:00:00Z", "uhr"),
]


def rechne() -> list[str]:
    skript = PRUEFUNG + """
var faelle = JSON.parse(process.argv[1]);
var aus = faelle.map(function (f) {
  var b = muruVeraltet(f[0], Date.parse(f[1]));
  return { grund: b ? b.grund : null, text: b ? muruStandText(b) : '' };
});
console.log(JSON.stringify(aus));
"""
    lauf = subprocess.run(["node", "-e", skript, json.dumps(FAELLE)],
                          capture_output=True, text=True)
    if lauf.returncode:
        return [f"Node: {lauf.stderr.strip()[:300]}"]
    ergebnisse = json.loads(lauf.stdout)
    fehler = []
    for (stand, jetzt, soll), ist in zip(FAELLE, ergebnisse):
        if ist["grund"] != soll:
            fehler.append(f"Stand {stand or '(leer)'}, jetzt {jetzt}: "
                          f"{ist['grund']} statt {soll}")
    # Der Text zum Fall vom 26.09.: drei Tage alt, Ortszeit
    text = ergebnisse[3]["text"]
    for teil in ("Mittwoch", "23.09.", "10:32", "vor 3 Tagen"):
        if teil not in text:
            fehler.append(f"Text ohne '{teil}': {text}")
    return fehler


def seiten() -> list[str]:
    stand = json.loads((DOCS / "daten.json").read_text(encoding="utf-8")).get("aktualisiert")
    fehler = []
    for name in SEITEN:
        seite = (DOCS / name).read_text(encoding="utf-8")
        if f'data-stand="{html.escape(stand or "")}"' not in seite:
            fehler.append(f"{name}: Hinweis fehlt oder Stand weicht von daten.json ab")
        # Auf das ausgefuehrte Skript pruefen, nicht auf den Namen allein
        if AUSFUEHREN.strip() not in seite:
            fehler.append(f"{name}: Pruefskript fuer den Stand fehlt")
        elif seite.index('id="veraltet"') > seite.index(AUSFUEHREN.strip()):
            fehler.append(f"{name}: Pruefskript steht vor dem Hinweis")
        # Von Haus aus sichtbar, sonst bleibt er bei einem Skriptfehler weg
        kopf = seite[seite.find('<div class="veraltet"'):][:200]
        if "hidden" in kopf.split(">")[0]:
            fehler.append(f"{name}: Hinweis ist von Haus aus versteckt")
    return fehler


def main() -> int:
    fehler = rechne() + seiten()
    for f in fehler:
        print(f"  FEHLER   {f}")
    if not fehler:
        print(f"Stand-Hinweis: {len(FAELLE)} Faelle gerechnet, "
              f"{len(SEITEN)} Seiten geprueft")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
