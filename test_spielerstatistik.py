#!/usr/bin/env python3
"""Prueft die Auswertung der Spielberichte an erfundenen Faellen.

Mit echten Daten laesst sich nur pruefen, ob die Zahlen zu diesem Spieltag
passen. Hier stehen die Grenzfaelle: ein Spieler ohne Tore, ein fehlender
Bericht, eine Liga ohne Bericht, Namen bei der Jugend.
"""

from __future__ import annotations

import sys

import spielerstatistik as st

WIR = 100
SIE = 200

pruefungen: list[tuple[str, bool, str]] = []


def pruefe(name: str, ok: bool, info: str = "") -> None:
    pruefungen.append((name, ok, info))


def tor(minute: int, team: int, pid: str, vorname: str, nachname: str,
        heim_stand: int, gast_stand: int, art: str = "Tor") -> dict:
    return {"spielminute": minute, "minute": f"{minute:02}:00", "art": art,
            "ist_tor": True, "ist_strafe": False, "team_id": team,
            "spieler": {"id": pid, "vorname": vorname, "nachname": nachname},
            "stand": [heim_stand, gast_stand]}


def strafe(minute: int, team: int, pid: str, art: str = "Zwei Minuten") -> dict:
    return {"spielminute": minute, "minute": f"{minute:02}:00", "art": art,
            "ist_tor": False, "ist_strafe": True, "team_id": team,
            "spieler": {"id": pid, "vorname": "Timo", "nachname": "Streng"},
            "stand": None}


# Ein Spiel: wir treffen viermal in Folge, dann der Gegner, dann Siebenmeter
bericht = {"ereignisse": [
    tor(2, WIR, "a", "Anna", "Adler", 1, 0),
    tor(5, WIR, "b", "Bea", "Berger", 2, 0),
    tor(8, WIR, "a", "Anna", "Adler", 3, 0),
    tor(11, WIR, "a", "Anna", "Adler", 4, 0),
    tor(14, SIE, "x", "Xaver", "Xander", 4, 1),
    tor(20, SIE, "x", "Xaver", "Xander", 4, 2),
    tor(25, WIR, "b", "Bea", "Berger", 5, 2, art="Siebenmeter Tor"),
    {"spielminute": 27, "minute": "27:00", "art": "Siebenmeter Fehlwurf",
     "ist_tor": False, "ist_strafe": False, "team_id": WIR,
     "spieler": {"id": "b", "vorname": "Bea", "nachname": "Berger"},
     "stand": [5, 2]},
    strafe(50, WIR, "t"),
    strafe(58, WIR, "t"),
]}

# --- Schuetzen --------------------------------------------------------
s = st.schuetzen([bericht], WIR, jugend=False)
namen = [x["name"] for x in s]
pruefe("Nur eigene Spieler in der Liste", namen == ["Anna Adler", "Bea Berger"],
       str(namen))
pruefe("Tore richtig gezaehlt", s[0]["tore"] == 3 and s[1]["tore"] == 2,
       str([(x["name"], x["tore"]) for x in s]))
pruefe("Siebenmeter-Quote aus Treffern und Wuerfen",
       s[1]["siebenmeter_tore"] == 1 and s[1]["siebenmeter_wuerfe"] == 2
       and s[1]["siebenmeter_quote"] == 50, str(s[1]))
pruefe("Ein Feldtor zaehlt nicht als Siebenmeter",
       s[0]["siebenmeter_wuerfe"] == 0, str(s[0]))
pruefe("Wer nicht getroffen hat, steht nicht in der Schuetzenliste",
       "Timo Streng" not in namen, str(namen))

# --- Namen bei der Jugend ---------------------------------------------
j = st.schuetzen([bericht], WIR, jugend=True)
pruefe("Jugend nur mit Anfangsbuchstaben",
       [x["name"] for x in j] == ["Anna A.", "Bea B."], str([x["name"] for x in j]))
pruefe("Spieler-ID bleibt trotzdem erhalten", j[0]["id"] == "a", str(j[0]))

# --- Laeufe -----------------------------------------------------------
l = st.laeufe(bericht, WIR)
pruefe("Laengster eigener Lauf gefunden", l["eigene"] == 4, str(l))
pruefe("Beginn des Laufs vermerkt", l["eigene_ab"] == 2, str(l))
pruefe("Zwei Gegentore sind noch kein Lauf", l["fremde"] == 0, str(l))

# --- Verlauf ----------------------------------------------------------
v = st.verlauf(bericht)
pruefe("Verlauf beginnt bei 0:0", v[0] == [0, 0, 0], str(v[:2]))
pruefe("Verlauf endet beim letzten Stand", v[-1][1:] == [5, 2], str(v[-1]))
pruefe("Keine doppelten Staende im Verlauf",
       len(v) == len({tuple(x[1:]) for x in v}), str(v))

# --- Verteilung -------------------------------------------------------
t = st.verteilung([bericht], WIR)
pruefe("Eigene Schuetzen gezaehlt", t["eigene_schuetzen"] == 2, str(t))
pruefe("Gegnerische Schuetzen getrennt", t["fremde_schuetzen"] == 1, str(t))
pruefe("Groesster Anteil in Prozent", t["groesster_anteil"] == 60, str(t))

# --- Strafen ----------------------------------------------------------
p = st.strafen_nach_abschnitt([bericht], WIR)
pruefe("Strafen gezaehlt", p["gesamt"] == 2, str(p))
pruefe("Strafen der Schlussphase zugeordnet", p["abschnitte"]["45-60"] == 2, str(p))

# --- Fehlende Berichte muessen benannt werden -------------------------
spiele = {
    "A": {"datum": "2026-08-29T20:00:00", "match_id": 1, "gegner": "A",
          "ergebnis": {"eigene": 5, "fremde": 2}},
    "B": {"datum": "2026-09-05T20:00:00", "match_id": 2, "gegner": "B",
          "ergebnis": {"eigene": 3, "fremde": 3}},
    "C": {"datum": "2026-09-12T20:00:00", "match_id": 3, "gegner": "C",
          "ergebnis": {"eigene": 1, "fremde": 9}},
    "D": {"datum": "2026-09-19T20:00:00", "match_id": 4, "gegner": "D"},
}
cache = {"1": bericht, "2": {"ereignisse": [], "ohne_bericht": True}}
a = st.alles(spiele, cache, WIR, jugend=False)
q = a["quelle"]
pruefe("Gelaufene Spiele gezaehlt", q["spiele_gelaufen"] == 3, str(q))
pruefe("Spiele mit Bericht gezaehlt", q["mit_bericht"] == 1, str(q))
pruefe("Liga ohne Bericht gesondert", q["ohne_bericht"] == 1, str(q))
pruefe("Noch nicht abgerufenes Spiel gesondert", q["offen"] == 1, str(q))
pruefe("Ein Spiel ohne Ergebnis zaehlt nicht mit",
       q["spiele_gelaufen"] + 1 == len(spiele), str(q))
pruefe("Nur Spiele mit Bericht im Verlauf", len(a["spiele"]) == 1,
       str(len(a["spiele"])))

# --- Ohne jeden Bericht darf nichts krachen ---------------------------
leer = st.alles(spiele, {}, WIR, jugend=False)
pruefe("Ohne Berichte keine Schuetzen", leer["schuetzen"] == [], str(leer["schuetzen"]))
pruefe("Ohne Berichte wird das gemeldet", leer["quelle"]["offen"] == 3,
       str(leer["quelle"]))

# --- Die Anzeige darf nichts Falsches ueber die Quelle behaupten ---------
sys.path.insert(0, ".")
import baue_seite as bs

# Nichts abgerufen (derzeit die Jugend): gar kein Block, kein Hinweis
kein_abruf = {"quelle": {"spiele_gelaufen": 3, "mit_bericht": 0,
                         "ohne_bericht": 0, "offen": 3}, "schuetzen": []}
pruefe("Ohne Abruf gar kein Spielerblock", bs.spielerblock(kein_abruf) == "",
       bs.spielerblock(kein_abruf)[:80])

# Abgerufen, aber die Quelle liefert nichts: das gehoert benannt
nichts_da = {"quelle": {"spiele_gelaufen": 2, "mit_bericht": 0,
                        "ohne_bericht": 2, "offen": 0}, "schuetzen": []}
text = bs.spielerblock(nichts_da)
pruefe("Liga ohne Bericht wird erklaert",
       "kein Spielbericht geführt" in text, text[:120])
pruefe("Kein 'Aus 0 Spielen'", "Aus 0 Spielen" not in text, text[:120])

# Teilweise vorhanden: "weitere" ist dann richtig
teils = {"quelle": {"spiele_gelaufen": 3, "mit_bericht": 2,
                    "ohne_bericht": 0, "offen": 1},
         "schuetzen": [{"id": "a", "name": "Anna Adler", "tore": 3, "spiele": 2,
                        "tore_je_spiel": 1.5, "siebenmeter_tore": 0,
                        "siebenmeter_wuerfe": 0, "siebenmeter_quote": None}],
         "verteilung": {}, "strafen": {}}
text = bs.spielerblock(teils)
pruefe("Teilweise vorhanden: 'Aus 2 Spielen von 3'",
       "Aus 2 Spielen von 3" in text, text[-260:])
pruefe("Ein fehlendes Spiel heisst 'ein weiteres'",
       "ein weiteres Spiel" in text, text[-260:])
pruefe("Die Schuld liegt sichtbar bei der Quelle",
       "handball.net" in text, text[-260:])

# Nichts fehlt: dann auch kein Hinweis auf Fehlendes
vollstaendig = dict(teils)
vollstaendig["quelle"] = {"spiele_gelaufen": 2, "mit_bericht": 2,
                          "ohne_bericht": 0, "offen": 0}
text = bs.spielerblock(vollstaendig)
pruefe("Ohne Luecke kein Hinweis auf handball.net",
       "handball.net" not in text and "Aus 2 Spielen." in text, text[-160:])

# --- Spielfilm ----------------------------------------------------------
import re as _re

def zeichne(verlauf, heim=True, ergebnis=None, laeufe=None):
    return bs.spielfilm({"verlauf": verlauf, "heim": heim,
                         "datum": "2026-09-05T20:00:00", "gegner": "HSG Worms",
                         "ergebnis": ergebnis or {"eigene": 5, "fremde": 2},
                         "laeufe": laeufe or {}})

def punkte_aus(svg):
    m = _re.search(r'class="linie" points="([^"]+)"', svg)
    return [tuple(float(z) for z in p.split(",")) for p in m.group(1).split()]

# Ein Spiel, in dem wir durchgehend fuehren
svg = zeichne([[0, 0, 0], [5, 1, 0], [20, 4, 1], [40, 8, 3], [58, 12, 5]])
ys = [y for _, y in punkte_aus(svg)]
pruefe("Kurve bleibt im Bild", all(0 <= y <= 96 for y in ys), str(ys))
pruefe("Fuehrung liegt oben", ys[-1] < ys[0], f"Start {ys[0]}, Ende {ys[-1]}")
pruefe("Nulllinie ist beschriftet", ">0<" in svg, svg[:200])
pruefe("Endstand steht an der Kurve", "+7" in svg, svg[-300:])

# Auswaerts dreht sich die Sicht: der Verlauf steht als [Heim, Gast] da,
# gezeichnet wird der eigene Abstand.
svg = zeichne([[0, 0, 0], [30, 6, 2]], heim=False)   # Heim 6, wir 2
ys = [y for _, y in punkte_aus(svg)]
pruefe("Auswaerts ist 6:2 fuer die Heimmannschaft ein Rueckstand",
       ys[-1] > ys[0], f"Start {ys[0]}, Ende {ys[-1]}")
svg = zeichne([[0, 0, 0], [30, 2, 6]], heim=False)   # wir 6, Heim 2
ys = [y for _, y in punkte_aus(svg)]
pruefe("und 2:6 als Gast eine Fuehrung", ys[-1] < ys[0],
       f"Start {ys[0]}, Ende {ys[-1]}")

# Ein Spiel ohne Fuehrungswechsel darf die Hoehe nicht verschenken
svg = zeichne([[0, 0, 0], [58, 20, 3]])
pruefe("Skala richtet sich nach dem Verlauf, nicht symmetrisch",
       "+17" in svg and "-17" not in svg, svg[:400])

# Zu wenig Daten: lieber nichts zeichnen als eine leere Flaeche
pruefe("Ohne Verlauf keine Grafik", zeichne([]) == "", zeichne([])[:60])
pruefe("Ein einzelner Punkt ergibt keine Kurve", zeichne([[0, 0, 0]]) == "")

# Der Lauf gehoert unter die Kurve
svg = zeichne([[0, 0, 0], [40, 7, 0]],
              laeufe={"eigene": 7, "eigene_ab": 33, "fremde": 0, "fremde_ab": None})
pruefe("Lauf wird benannt", "7 Tore in Folge ab Minute 33" in svg, svg[-200:])
svg = zeichne([[0, 0, 0], [40, 0, 7]],
              laeufe={"eigene": 0, "eigene_ab": None, "fremde": 5, "fremde_ab": 12})
pruefe("Auch ein gegnerischer Lauf wird benannt",
       "Gegner traf 5-mal in Folge ab Minute 12" in svg, svg[-200:])

# Klassennamen, die es im Projekt schon gibt, duerfen nicht wiederverwendet
# werden - .kopf traegt im Seitenkopf einen schwarzen Grund.
pruefe("Kein kollidierender Klassenname 'kopf'",
       'class="kopf"' not in zeichne([[0, 0, 0], [30, 3, 1]]),
       zeichne([[0, 0, 0], [30, 3, 1]])[:120])

# --- Detailansicht in der Spieleliste -----------------------------------
bericht = {"verlauf": [[0, 0, 0], [30, 8, 4], [58, 15, 9]], "heim": True,
           "datum": "2026-09-05T20:00:00", "gegner": "HSG Worms",
           "ergebnis": {"eigene": 15, "fremde": 9},
           "laeufe": {"eigene": 4, "eigene_ab": 12, "fremde": 0, "fremde_ab": None},
           "schuetzen": [{"id": "a", "name": "Anna Adler", "tore": 6, "spiele": 1,
                          "tore_je_spiel": 6.0, "siebenmeter_tore": 2,
                          "siebenmeter_wuerfe": 3, "siebenmeter_quote": 67}],
           "strafen": 2}
d = bs.spieldetails(bericht)
pruefe("Detailansicht traegt die Klasse fuer die Farben",
       'class="spielfilm"' in d, d[:100])
pruefe("Detailansicht enthaelt die Kurve", "<svg" in d and "polyline" in d, d[:100])
pruefe("Detailansicht nennt die Schuetzen dieses Spiels",
       "Anna Adler 6" in d and "(2/3 7m)" in d, d[-200:])
pruefe("Zeitstrafen des Spiels stehen dabei", "2 Zeitstrafen" in d, d[-160:])
pruefe("Kein verschachteltes details in der Detailansicht",
       "<details" not in d, d[:120])
pruefe("Ohne Bericht keine Detailansicht", bs.spieldetails(None) == "")
pruefe("Ohne Verlauf keine Detailansicht",
       bs.spieldetails({"verlauf": [], "heim": True,
                        "datum": "2026-09-05T20:00:00", "gegner": "X"}) == "")

# --- Muster ueber mehrere Spiele ----------------------------------------
def spiel_mit(verlauf, heim=True):
    return {"verlauf": verlauf, "heim": heim}

# Drei Spiele, in denen der letzte Block jeweils schwach ist
drei = [
    spiel_mit([[0, 0, 0], [10, 3, 1], [50, 12, 7], [60, 13, 11]]),
    spiel_mit([[0, 0, 0], [10, 2, 1], [50, 10, 6], [60, 11, 10]]),
    spiel_mit([[0, 0, 0], [10, 4, 1], [50, 14, 8], [60, 15, 12]]),
]
m = st.muster(drei, [], WIR)
pruefe("Ab drei Spielen gibt es Muster", m["genug"] is True, str(m.get("genug")))
pruefe("Zwei Spiele reichen nicht", st.muster(drei[:2], [], WIR)["genug"] is False)
pruefe("Und es steht dabei, ab wann", st.muster(drei[:2], [], WIR)["ab"] == 3)

bloecke = {b["von"]: b for b in m["bloecke"]}
pruefe("Sechs Bloecke ueber 60 Minuten", len(m["bloecke"]) == 6, str(len(m["bloecke"])))
pruefe("Starker Anfang wird erkannt", bloecke[0]["schnitt"] > 0, str(bloecke[0]))
pruefe("Schwache Schlussphase wird erkannt", bloecke[50]["schnitt"] < 0,
       str(bloecke[50]))
pruefe("Verlorene Bloecke werden gezaehlt", bloecke[50]["verloren"] == 3,
       str(bloecke[50]))

# Auswaerts dreht sich die Sicht auch hier
auswaerts = [spiel_mit([[0, 0, 0], [60, 20, 10]], heim=False)] * 3
ma = st.muster(auswaerts, [], WIR)
pruefe("Auswaerts wird 20:10 fuer die Heimmannschaft zum Minus",
       all(b["schnitt"] <= 0 for b in ma["bloecke"]),
       str([b["schnitt"] for b in ma["bloecke"]]))

# Antwort auf einen gegnerischen Lauf
def t(minute, team):
    return {"spielminute": minute, "ist_tor": True, "team_id": team,
            "art": "Tor", "spieler": {"id": "x", "vorname": "A", "nachname": "B"}}
lauf = {"ereignisse": [
    t(1, WIR), t(2, SIE), t(3, SIE), t(4, SIE),   # Gegner trifft dreimal
    t(6, WIR), t(7, WIR), t(8, WIR), t(9, WIR),   # wir antworten viermal
]}
a = st.antwort_auf_laeufe([lauf], WIR)
pruefe("Gegnerischer Lauf wird erkannt", a and a["faelle"] == 1, str(a))
pruefe("Die Antwort wird gezaehlt", a["schnitt"] == 4.0, str(a))
pruefe("Und als Drehung vermerkt", a["gedreht"] == 1, str(a))
pruefe("Zwei Gegentore sind noch kein Lauf",
       st.antwort_auf_laeufe([{"ereignisse": [t(1, SIE), t(2, SIE), t(5, WIR)]}],
                             WIR) is None)

# Enge Schlussphasen
eng = [
    spiel_mit([[0, 0, 0], [50, 10, 9], [60, 14, 12]]),   # eng, gewonnen
    spiel_mit([[0, 0, 0], [50, 8, 9], [60, 10, 13]]),    # eng, verloren
    spiel_mit([[0, 0, 0], [50, 20, 5], [60, 25, 8]]),    # nie eng
]
e = st.enge_schlussphasen(eng)
pruefe("Nur wirklich enge Spiele zaehlen", e["spiele"] == 2, str(e))
pruefe("Ausgang wird unterschieden", e["gewonnen"] == 1 and e["verloren"] == 1,
       str(e))

# --- Die Deutung in Worten ----------------------------------------------
import re as _re2

def deutung(spiele, berichte=None):
    return _re2.sub(r"<[^>]+>", "", bs.musterdeutung(
        st.muster(spiele, berichte or [], WIR))).strip()

stark_schwach = [spiel_mit([[0, 0, 0], [10, 6, 1], [60, 15, 12]]),
                 spiel_mit([[0, 0, 0], [10, 5, 1], [60, 14, 11]]),
                 spiel_mit([[0, 0, 0], [10, 7, 2], [60, 16, 13]])]
t = deutung(stark_schwach)
pruefe("Staerkste Phase wird benannt", "stärkste Phase" in t, t)
pruefe("Schwaechste Phase ebenfalls", "gebt ihr im Schnitt" in t, t)
pruefe("Kommazahlen mit Komma", "4,7" in t, t)
pruefe("Und der Satzpunkt bleibt ein Punkt", t.rstrip().endswith("."), t[-40:])

# Ein Unentschieden ist keine Niederlage
unentschieden = [spiel_mit([[0, 0, 0], [50, 10, 10], [60, 12, 12]])] * 3
t = deutung(unentschieden)
pruefe("Unentschieden wird als solches benannt", "unentschieden" in t, t)
pruefe("Und nicht als 'null gewonnen' abgetan", "0 gewonnen" not in t, t)

# Wo nichts heraussticht, wird nichts behauptet
gleichmaessig = [spiel_mit([[0, 0, 0], [10, 2, 1], [20, 4, 2], [30, 6, 3],
                            [40, 8, 4], [50, 10, 5], [60, 12, 6]])] * 3
t = deutung(gleichmaessig)
pruefe("Ohne Auffaelligkeit keine erfundene Aussage",
       "hebt sich kein Abschnitt" in t or "stärkste Phase" in t, t)

# Der Hinweis vor der Schwelle nennt, was noch fehlt
vor = bs.musterblock({"muster": st.muster(stark_schwach[:2], [], WIR)})
pruefe("Vor der Schwelle steht, wie viele Spiele fehlen",
       "fehlt noch ein Spiel" in vor, _re2.sub(r"<[^>]+>", "", vor)[-90:])
pruefe("Ohne jedes Spiel gar kein Musterblock",
       bs.musterblock({"muster": st.muster([], [], WIR)}) == "")

fehler = 0
for name, ok, info in pruefungen:
    if not ok:
        fehler += 1
    print(f"{'  ok  ' if ok else 'FEHLER'}  {name}" + ("" if ok else f"   {info}"))
print(f"\n{f'{fehler} Prüfung(en) fehlgeschlagen' if fehler else f'Alle {len(pruefungen)} Prüfungen bestanden'}")
sys.exit(1 if fehler else 0)
