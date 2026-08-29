#!/usr/bin/env python3
"""Erzeugt die Abo-Seite (index.html) aus der Datendatei des Generators.

Eine Seite fuer alle Mannschaften: oben die Auswahl, darunter je Mannschaft
die drei Bereiche Kalender, Spiele und Tabelle. Umgeschaltet wird im Browser,
alle Daten stehen bereits in der Seite.
"""

from __future__ import annotations

import argparse
import html
import json
import urllib.parse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from seite_ansicht import ANSICHT
from seite_meine import MEINE
from seite_grafik import GRAFIK
from seite_skript import SKRIPT
from seite_tipp import TIPP
from seite_zaehlung import ZAEHLUNG
from seite_stil import STIL

TZ = ZoneInfo("Europe/Berlin")
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
              "Freitag", "Samstag", "Sonntag"]
KURZTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]


def sicher(text) -> str:
    return html.escape(str(text if text is not None else ""))


def zeit(spiel: dict) -> datetime:
    return datetime.fromisoformat(spiel["datum"]).replace(tzinfo=TZ)


def strasse(spiel: dict) -> str:
    """Adresse ohne den vorangestellten Hallennamen - der steht schon daneben."""
    ort, halle = spiel.get("ort") or "", spiel.get("halle") or ""
    if halle and ort.startswith(halle):
        ort = ort[len(halle):].lstrip(", ")
    return ort


def kartenlink(spiel: dict) -> str:
    ziel = " ".join(t for t in [spiel.get("halle"), strasse(spiel)] if t)
    # &amp;, weil die URL direkt in ein href-Attribut geschrieben wird
    return "https://www.google.com/maps/search/?api=1&amp;query=" + urllib.parse.quote(ziel)


# --------------------------------------------------------------------------
# Bausteine
# --------------------------------------------------------------------------

def hero(spiel: dict, kurzname: str, heute: datetime) -> str:
    wann = zeit(spiel)
    tage = (wann.date() - heute.date()).days
    relativ = ("Heute" if tage == 0 else "Morgen" if tage == 1
               else f"In {tage} Tagen" if 0 < tage < 7 else "Nächstes Spiel")
    heim = spiel.get("heim")
    gegner = sicher(spiel.get("gegner"))
    paarung = (f"{sicher(kurzname)} &ndash; {gegner}" if heim
               else f"{gegner} &ndash; {sicher(kurzname)}")
    return f"""<div class="marker"><span data-anwurf="{wann.isoformat()}">{relativ}</span>
 &middot; {'Heimspiel' if heim else 'Auswärtsspiel'}</div>
<h2 class="paarung">{paarung}</h2>
<p class="countdown" data-countdown="{wann.isoformat()}"></p>
<dl class="fakten">
<div><dt>Anwurf</dt><dd>{WOCHENTAGE[wann.weekday()]}, {wann:%d.%m.%Y}, {wann:%H:%M} Uhr</dd></div>
<div><dt>Halle</dt><dd>{sicher(spiel.get('halle'))}</dd></div>
<div><dt>Adresse</dt><dd><a href="{kartenlink(spiel)}" target="_blank"
rel="noopener">{sicher(strasse(spiel))}</a></dd></div>
</dl>"""


def letztes_ergebnis(spiele: list[dict]) -> dict | None:
    fertig = [s for s in spiele if s.get("ergebnis")]
    return fertig[-1] if fertig else None


def ergebnis_satz(team: dict, spiel: dict) -> str:
    """Fertiger Satz fuers Weitergeben in die Mannschaftsgruppe."""
    e = spiel["ergebnis"]
    wort = {"S": "gewonnen", "N": "verloren", "U": "unentschieden gespielt"}[e["ausgang"]]
    wo = "zu Hause" if spiel.get("heim") else "auswärts"
    satz = (f'{team.get("name", "")}: {e["eigene"]}:{e["fremde"]} {wo} gegen '
            f'{spiel.get("gegner", "")} {wort}.')

    tab = team.get("tabelle") or {}
    zeile = next((x for x in tab.get("eintraege") or []
                  if x.get("team_id") == team.get("team_id")), None)
    if zeile and tab.get("gespielt"):
        satz += (f' Damit Platz {zeile["platz"]} mit {zeile["punkte"]} Punkten'
                 f' in der {team.get("liga", "Liga")}.')
    return satz


def teilenblock(team: dict, naechstes: dict | None, letztes: dict | None) -> str:
    """Knoepfe fuer die Grafiken. Die Daten haengen als JSON am Element -
    gezeichnet wird erst im Browser, wenn jemand tatsaechlich draufdrueckt."""
    if not naechstes and not letztes:
        return ""

    def paket(spiel, art):
        wann = zeit(spiel)
        d = {
            "art": art,
            "verein": "HSG Mutterstadt/Ruchheim",
            "mannschaft": team.get("name", ""),
            "gegner": spiel.get("gegner", ""),
            "heim": bool(spiel.get("heim")),
            "datum": wann.isoformat(),
            "datum_text": f"{WOCHENTAGE[wann.weekday()]}, {wann:%d.%m.%Y}",
            "uhrzeit": f"{wann:%H:%M}",
            "halle": spiel.get("halle", ""),
            "ort": strasse(spiel).split(",")[-1].strip(),
            "liga": team.get("liga", ""),
            "spieltag": spiel.get("spieltag"),
        }
        if art == "ergebnis" and spiel.get("ergebnis"):
            e = spiel["ergebnis"]
            d["stand"] = f'{e["eigene"]}:{e["fremde"]}'
            d["ausgang"] = {"S": "Sieg", "N": "Niederlage",
                            "U": "Unentschieden"}[e["ausgang"]]
        return d

    knoepfe = []
    if naechstes:
        knoepfe.append(
            f'<button type="button" class="knopf stumm" data-grafik=\'{json.dumps(paket(naechstes, "spiel"), ensure_ascii=False)}\'>'
            f'Bild fürs nächste Spiel</button>')
    if letztes and letztes.get("ergebnis"):
        knoepfe.append(
            f'<button type="button" class="knopf stumm" data-grafik=\'{json.dumps(paket(letztes, "ergebnis"), ensure_ascii=False)}\'>'
            f'Bild vom letzten Ergebnis</button>')

    satzknopf = ""
    if letztes and letztes.get("ergebnis"):
        satzknopf = (f'<button type="button" class="knopf stumm" '
                     f'data-teile="{sicher(ergebnis_satz(team, letztes))}">'
                     f'Ergebnis als Text</button>')

    return f"""<div class="teilen">
  <div class="rubrik">Zum Teilen</div>
  <div class="formatwahl" role="group" aria-label="Bildformat">
    <button type="button" data-format="story" aria-pressed="true">Story 9:16</button>
    <button type="button" data-format="post" aria-pressed="false">Beitrag 1:1</button>
  </div>
  {"".join(knoepfe)}
  {satzknopf}
  <p class="statfuss">Das Bild wird auf deinem Handy erzeugt. Es geht nichts
     an uns oder sonstwohin.</p>
</div>"""


def hinspiel_und_gegner(naechstes: dict, alle: list[dict], tabelle: dict) -> str:
    """Was es ueber den naechsten Gegner an Fakten gibt: das frühere
    Aufeinandertreffen dieser Saison und seine Tabellenwerte.

    Bewusst nur Zahlen - eine Einschaetzung waere geraten."""
    gegner_id = naechstes.get("gegner_id")
    teile = []

    frueher = [s for s in alle
               if s.get("gegner_id") == gegner_id and s.get("ergebnis")
               and s["datum"] < naechstes["datum"]]
    if frueher:
        s = frueher[-1]
        e = s["ergebnis"]
        wort = {"S": "gewonnen", "N": "verloren", "U": "unentschieden"}[e["ausgang"]]
        wo = "zu Hause" if s.get("heim") else "auswärts"
        verweis = (f'<a href="https://www.handball.net/match/{s["match_id"]}"'
                   f' target="_blank" rel="noopener">Spielbericht</a>'
                   if s.get("match_id") else "")
        teile.append(
            # Aus eigener Sicht, weil direkt daneben "gewonnen" steht -
            # die Heim:Gast-Schreibweise laese sich hier falschherum.
            f'<div class="hinspiel"><span class="stand">{e["eigene"]}:{e["fremde"]}</span>'
            f'<span class="wo">{wort}, {wo} am '
            f'{datetime.fromisoformat(s["datum"]):%d.%m.%Y}</span>{verweis}</div>')

    zeile = next((e for e in (tabelle or {}).get("eintraege") or []
                  if e.get("team_id") == gegner_id), None)
    if zeile and (tabelle or {}).get("gespielt"):
        teile.append(
            f'<dl class="gegnerdaten">'
            f'<div><dt>Tabelle</dt><dd>Platz {zeile["platz"]}</dd></div>'
            f'<div><dt>Punkte</dt><dd>{zeile["punkte"]}</dd></div>'
            f'<div><dt>Spiele</dt><dd>{zeile["spiele"]}</dd></div>'
            f'<div><dt>Tordifferenz</dt><dd>{zeile["differenz"]:+d}</dd></div>'
            f'</dl>')

    if not teile:
        return ""
    return (f'<div class="vorschau"><h3>Gegen {sicher(naechstes.get("gegner"))}</h3>'
            + "".join(teile) + "</div>")


def spielzeile(spiel: dict, heute: datetime, naechster: bool) -> str:
    wann = zeit(spiel)
    heim = spiel.get("heim")
    erg = spiel.get("ergebnis")

    klassen = "spiel"
    if erg or wann < heute:
        klassen += " vorbei"
    if naechster:
        klassen += " jetzt"

    halle = sicher(spiel.get("halle"))
    ort = (f'<a href="{kartenlink(spiel)}" target="_blank" rel="noopener">{halle}</a>'
           if spiel.get("ort") else halle)

    rechts = f'<div class="hz {"heim" if heim else ""}">{"H" if heim else "A"}</div>'
    if erg:
        # Aus eigener Sicht: In der Zeile steht nur der Gegner, nichts klaert
        # sonst die Reihenfolge. "30:20" rot neben einem Auswaertsspiel liest
        # sich sonst, als haetten wir 30 geworfen.
        rechts += (f'<div class="stand {erg["ausgang"]}">'
                   f'{erg["eigene"]}:{erg["fremde"]}</div>')

    return f"""<div class="{klassen}">
<div class="datum">{KURZTAGE[wann.weekday()]} {wann:%d.%m.}<span>{wann:%H:%M}</span></div>
<div><div class="gegner">{sicher(spiel.get('gegner'))}</div>
<div class="halle">{ort}</div></div>
<div class="rechts">{rechts}</div>
</div>"""


def spielliste(spiele: list[dict], heute: datetime) -> str:
    kommend = [s for s in spiele if zeit(s) >= heute and not s.get("ergebnis")]
    naechstes = kommend[0]["datum"] if kommend else None
    zeilen, letzter_monat = [], None
    for spiel in spiele:
        wann = zeit(spiel)
        monat = (wann.year, wann.month)
        if monat != letzter_monat:
            zeilen.append(f'<div class="monat">{MONATE[wann.month - 1]} {wann.year}</div>')
            letzter_monat = monat
        zeilen.append(spielzeile(spiel, heute, spiel["datum"] == naechstes))
    return "".join(zeilen)


EMOJIS = ["\U0001F98A", "\U0001F525", "\U0001F389", "\U0001F37B"]


def paarung_namen(spiel: dict, team: dict) -> tuple[str, str]:
    """Wer steht links, wer rechts - der Tipp wird als Heim:Gast gespeichert."""
    eigen = team.get("kurzname") or team.get("name") or "Wir"
    gegner = spiel.get("gegner") or "Gegner"
    return (eigen, gegner) if spiel.get("heim") else (gegner, eigen)


def mitmachblock(spiel_code: str, vorher_code: str | None, worker: str,
                 heimname: str = "", gastname: str = "",
                 schluessel: str = "") -> str:
    """Hype-Zaehler und Zusagen fuer das naechste Spiel.

    Ohne Worker-Adresse entfaellt der Block ersatzlos - die Seite
    funktioniert dann wie zuvor."""
    if not worker or not spiel_code:
        return ""
    knoepfe = "".join(
        f'<button type="button" data-emoji="{e}" '
        f'aria-label="Anfeuern mit {e}">{e}</button>' for e in EMOJIS)
    return f"""<div class="mitmachen" data-spiel="{sicher(spiel_code)}"
     data-vorher="{sicher(vorher_code or '')}" data-worker="{sicher(worker)}">
  <div class="hype">
    <div class="titel">Hype vor dem Spiel</div>
    <div><span class="zahl" data-hype>&ndash;</span><span class="vergleich" data-vergleich></span></div>
    <div class="bahn" data-bahn></div>
    <div class="knoepfe">{knoepfe}</div>
  </div>
  <div class="tippspiel" data-tipp="{sicher(spiel_code)}" data-mannschaft="{sicher(schluessel)}"
       data-heimname="{sicher(heimname)}" data-gastname="{sicher(gastname)}">
    <div class="titel">Tipprunde</div>
    <div class="tippzeile">
      <div><label for="tipp-heim-{sicher(spiel_code)}">{sicher(heimname)}</label>
        <input id="tipp-heim-{sicher(spiel_code)}" data-tippfeld="heim" type="number"
               inputmode="numeric" min="0" max="99" placeholder="–"></div>
      <div class="doppel">:</div>
      <div><label for="tipp-gast-{sicher(spiel_code)}">{sicher(gastname)}</label>
        <input id="tipp-gast-{sicher(spiel_code)}" data-tippfeld="gast" type="number"
               inputmode="numeric" min="0" max="99" placeholder="–"></div>
    </div>
    <input class="name" data-tippname type="text" maxlength="24"
           placeholder="Dein Name für die Tabelle" autocomplete="nickname">
    <button type="button" class="knopf" data-tippsenden>Tipp abgeben</button>
    <p class="meldung" data-tippmeldung></p>
    <div class="tipptabelle" data-tipptabelle></div>
    <p class="nebensache">
      <button type="button" data-tippumzug>Auf anderem Gerät weitertippen</button>
    </p>
  </div>

  <div class="dabei">
    <div class="titel">Bist du dabei?</div>
    <div class="reihe">
      <button type="button" data-dabei aria-pressed="false">Ich bin dabei</button>
      <span class="anzahl" data-anzahl></span>
    </div>
    <p class="fussnote">Ohne Namen, gezählt wird pro Gerät.</p>
  </div>
</div>"""


def formblock(form: list[str]) -> str:
    if not form:
        return ""
    wort = {"S": "Sieg", "N": "Niederlage", "U": "Unentschieden"}
    kette = "".join(
        f'<b class="{a}" title="{wort.get(a, a)}">{a}</b>' for a in form)
    return (f'<div class="form"><span class="titel">Form</span>'
            f'<span class="kette">{kette}</span></div>')


def verlaufsblock(tabelle: dict) -> str:
    """Platzierung ueber die Spieltage als kleine Linie.

    Erst ab drei Spieltagen sinnvoll - zwei Punkte sind keine Kurve.
    Die y-Achse ist umgedreht: Platz 1 gehoert nach oben."""
    verlauf = (tabelle or {}).get("verlauf") or []
    if len(verlauf) < 3:
        return ""

    anzahl = max(tabelle.get("mannschaften") or 12, max(p["platz"] for p in verlauf))
    breite, hoehe = 320, 110
    links, rechts, oben, unten = 26, 8, 10, 20
    flaeche_b = breite - links - rechts
    flaeche_h = hoehe - oben - unten

    def x(i: int) -> float:
        teiler = max(len(verlauf) - 1, 1)
        return links + flaeche_b * i / teiler

    def y(platz: int) -> float:
        # Platz 1 oben, letzter Platz unten
        anteil = (platz - 1) / max(anzahl - 1, 1)
        return oben + flaeche_h * anteil

    punkte = " ".join(f"{x(i):.1f},{y(p['platz']):.1f}" for i, p in enumerate(verlauf))
    kreise = "".join(f'<circle class="punkt" cx="{x(i):.1f}" cy="{y(p["platz"]):.1f}" r="3"/>'
                     for i, p in enumerate(verlauf))

    gitter = "".join(
        f'<line class="gitter" x1="{links}" y1="{y(pl):.1f}" '
        f'x2="{breite - rechts}" y2="{y(pl):.1f}"/>'
        f'<text x="0" y="{y(pl) + 4:.1f}">{pl}.</text>'
        for pl in (1, anzahl))

    letzter = verlauf[-1]
    beschriftung = (
        f'<text class="jetzt" x="{x(len(verlauf) - 1):.1f}" '
        f'y="{y(letzter["platz"]) - 10:.1f}" text-anchor="end">'
        f'Platz {letzter["platz"]}</text>'
        f'<text x="{links}" y="{hoehe - 4}">Spieltag {verlauf[0]["runde"]}</text>'
        f'<text x="{breite - rechts}" y="{hoehe - 4}" text-anchor="end">'
        f'Spieltag {letzter["runde"]}</text>')

    return f"""<div class="verlauf">
<div class="titel">Platzierung im Saisonverlauf</div>
<svg viewBox="0 0 {breite} {hoehe}" role="img"
     aria-label="Platzierung von Spieltag {verlauf[0]['runde']} bis {letzter['runde']}:
     zuletzt Platz {letzter['platz']} von {anzahl}">
{gitter}
<polyline class="linie" points="{punkte}"/>
{kreise}
{beschriftung}
</svg>
</div>"""


def spiel_wort(n: int, fall: str = "nominativ") -> str:
    """1 Spiel, 2 Spiele - beziehungsweise 'aus 1 Spiel', 'aus 2 Spielen'."""
    if n == 1:
        return "1 Spiel"
    return f"{n} Spielen" if fall == "dativ" else f"{n} Spiele"


def zahl(n) -> str:
    """Tausenderpunkte, wie man Zahlen hierzulande schreibt."""
    return f"{n:,}".replace(",", ".")


def kennzahl(titel: str, wert: str, zusatz: str = "", breit: bool = False) -> str:
    z = f'<span class="zusatz">{zusatz}</span>' if zusatz else ""
    return (f'<div{" class=\"breit\"" if breit else ""}><dt>{titel}</dt>'
            f'<dd>{wert}{z}</dd></div>')


def statistikblock(st: dict) -> str:
    """Kennzahlen, die handball.net so nicht ausweist.

    Der Fahrtenteil steht ab dem ersten Tag, alles Ergebnisabhaengige
    erscheint erst, wenn gespielt wurde - leere Nullen sind keine Statistik."""
    if not st:
        return '<p class="statfuss">Noch keine Daten.</p>'

    teile = []
    f = st.get("fahrten") or {}
    if f.get("gesamt_km"):
        felder = [
            kennzahl("Kilometer", zahl(f["gesamt_km"]),
                     f'{f["fahrten"]} Fahrten, hin und zurück'),
            kennzahl("Im Auto", f'{str(f["stunden"]).replace(".", ",")}'
                     f'<span class="klein"> Std</span>', "geschätzt bei 70 km/h"),
        ]
        if f.get("weiteste"):
            felder.append(kennzahl(
                "Weiteste Fahrt", f'{zahl(round(f["weiteste"]["km"]))}'
                f'<span class="klein"> km</span>', sicher(f["weiteste"]["halle"])))
        if f.get("naechste"):
            felder.append(kennzahl(
                "Kürzeste Fahrt", f'{zahl(round(f["naechste"]["km"]))}'
                f'<span class="klein"> km</span>', sicher(f["naechste"]["halle"])))
        teile.append('<div class="rubrik">Unterwegs</div>'
                     f'<dl class="kennzahlen">{"".join(felder)}</dl>')
        if f.get("ohne_koordinaten"):
            teile.append(
                '<p class="statfuss">Bei diesen Hallen fehlt beim Verband die '
                'Adresse, die Kilometer fehlen also in der Summe: '
                + ", ".join(sicher(h) for h in f["ohne_koordinaten"]) + ".</p>")

    a = st.get("alltag") or {}
    if a.get("verbrauch"):
        teile.append(f"""<div class="verbrauch">
<div class="wert">{str(a["verbrauch"]).replace(".", ",")}<span class="einheit">Liter Bier / 100 km</span></div>
<p class="rechnung">{zahl(a["biere"])} Bier über die Saison, das sind {zahl(a["liter"])} Liter.
Aus {a["trainings"]} Trainings in {a["wochen"]} Wochen und {spiel_wort(a["spiele"], "dativ")},
geteilt durch {zahl(f.get("gesamt_km", 0))} gefahrene Kilometer.</p>
<p class="pointe">Ein Sattelschlepper kommt mit 30 aus.</p>
</div>""")
        teile.append('<dl class="kennzahlen">'
                     + kennzahl("Zeit für Handball", f'{zahl(a["stunden"])}'
                                f'<span class="klein"> Std</span>',
                                f'{str(a["tage"]).replace(".", ",")} Tage am Stück. '
                                'Training, Spiele, Warmup, Dritte Halbzeit und Fahrten.',
                                breit=True)
                     + "</dl>")

    b = st.get("bilanz") or {}
    if (b.get("gesamt") or {}).get("spiele"):
        g, h, aw = b["gesamt"], b["heim"], b["auswaerts"]
        se = st.get("serien") or {}
        kr = st.get("krimis") or {}
        to = st.get("tore") or {}
        felder = [
            kennzahl("Gesamt", f'{g["s"]}<span class="klein">S</span> '
                     f'{g["u"]}<span class="klein">U</span> '
                     f'{g["n"]}<span class="klein">N</span>',
                     f'aus {spiel_wort(g["spiele"], "dativ")}'),
            kennzahl("Zu Hause", f'{h["s"]}<span class="klein">S</span> '
                     f'{h["u"]}<span class="klein">U</span> '
                     f'{h["n"]}<span class="klein">N</span>'),
            kennzahl("Auswärts", f'{aw["s"]}<span class="klein">S</span> '
                     f'{aw["u"]}<span class="klein">U</span> '
                     f'{aw["n"]}<span class="klein">N</span>'),
        ]
        if to.get("schnitt"):
            felder.append(kennzahl("Tore pro Spiel",
                                   str(to["schnitt"]).replace(".", ","),
                                   f'{to["erzielt"]}:{to["kassiert"]} insgesamt'))
        if kr.get("gesamt"):
            felder.append(kennzahl("Krimis", f'{kr["anteil"]}<span class="klein">%</span>',
                                   f'{kr["anzahl"]} von {spiel_wort(kr["gesamt"], "dativ")} '
                                   'mit höchstens zwei Toren Unterschied'))
        if se.get("ohne_niederlage"):
            felder.append(kennzahl("Längste Serie",
                                   f'{se["ohne_niederlage"]}<span class="klein">'
                                   f'{" Spiel" if se["ohne_niederlage"] == 1 else " Spiele"}</span>',
                                   "ohne Niederlage"))
        teile.append('<div class="rubrik">Bilanz</div>'
                     f'<dl class="kennzahlen">{"".join(felder)}</dl>')

        anw = st.get("anwurf") or {}
        geg = st.get("gegner") or {}
        weitere = []
        if (anw.get("spaet") or {}).get("spiele") and (anw.get("frueh") or {}).get("spiele"):
            weitere.append(kennzahl(
                "Spätanwurf", str(anw["spaet"]["schnitt"]).replace(".", ","),
                f'Punkte je Spiel ab 19 Uhr – früher: '
                f'{str(anw["frueh"]["schnitt"]).replace(".", ",")}'))
        if geg.get("liebster"):
            weitere.append(kennzahl("Liebster Gegner", sicher(geg["liebster"]["gegner"]),
                                    f'{geg["liebster"]["punkte"]} Punkte, '
                                    f'{geg["liebster"]["differenz"]:+d} Tore', breit=True))
        if geg.get("schwerster"):
            weitere.append(kennzahl("Schwerster Gegner", sicher(geg["schwerster"]["gegner"]),
                                    f'{geg["schwerster"]["punkte"]} Punkte, '
                                    f'{geg["schwerster"]["differenz"]:+d} Tore', breit=True))
        if to.get("torreichstes"):
            t = to["torreichstes"]
            weitere.append(kennzahl("Torreichstes Spiel", sicher(t["stand"]),
                                    f'gegen {sicher(t["gegner"])}, {t["summe"]} Tore',
                                    breit=True))
        if weitere:
            teile.append('<div class="rubrik">Rekorde</div>'
                         f'<dl class="kennzahlen">{"".join(weitere)}</dl>')
    else:
        teile.append('<p class="statfuss">Sobald gespielt wird, kommen hier '
                     'Bilanz, Serien und Rekorde dazu.</p>')

    return "".join(teile)


def tabellenblock(tabelle: dict, eigenes_team: int | None) -> str:
    """Vor dem ersten Spieltag steht ueberall 0 - die Reihenfolge ist dann
    ohne Aussage, darum der Hinweis darunter."""
    if not tabelle or not tabelle.get("eintraege"):
        return ('<p class="tabellenfuss">Hier wird nicht gewertet, '
                'deshalb gibt es keine Tabelle.</p>')

    zeilen = []
    for e in tabelle["eintraege"]:
        wir = ' class="wir"' if e.get("team_id") == eigenes_team else ""
        zeilen.append(
            f'<tr{wir}><td class="platz">{e["platz"]}</td>'
            f'<td class="mann">{sicher(e["team"])}</td>'
            f'<td>{e["spiele"]}</td>'
            f'<td class="nur-breit">{e["tore"]}:{e["gegentore"]}</td>'
            f'<td>{e["differenz"]:+d}</td>'
            f'<td class="pkt">{e["punkte"]}</td></tr>')

    fuss = (f'Stand nach Spieltag {tabelle["runde"]}.' if tabelle.get("gespielt")
            else "Die Saison hat noch nicht begonnen.")

    return f"""<div class="tabellenhuelle">
<table class="tabelle">
<thead><tr>
<th class="platz">Pl</th><th class="mann">Mannschaft</th><th>Sp</th>
<th class="nur-breit">Tore</th><th>Diff</th><th>Pkt</th>
</tr></thead>
<tbody>{"".join(zeilen)}</tbody>
</table>
</div>
<p class="tabellenfuss">{fuss}</p>"""


def aenderungsblock(team: dict) -> str:
    aenderungen = team.get("letzte_aenderungen") or []
    if not aenderungen:
        return ""
    punkte = "".join(f"<li>{sicher(a['text'])}</li>" for a in aenderungen)
    text = (f"Spielplan {team['name']} – Änderung:\n"
            + "\n".join("• " + a["text"] for a in aenderungen))
    return f"""<div class="hinweis">
<h3>Zuletzt geändert</h3>
<ul>{punkte}</ul>
<button type="button" data-teile="{sicher(text)}">Änderung weitergeben</button>
</div>"""


def abo_block(team: dict, basis: str) -> str:
    ics_url = f"{basis.rstrip('/')}/{team['datei']}"
    webcal = ics_url.replace("https://", "webcal://").replace("http://", "webcal://")
    return f"""<div class="rubrik">In den Kalender</div>

<div class="weg">
  <h3>iPhone, iPad und Mac</h3>
  <p>Antippen, „Abonnieren“ bestätigen. Verlegungen ziehen sich danach automatisch nach.</p>
  <a class="knopf" href="{webcal}">{sicher(team['name'])} abonnieren</a>
  <p class="tipp">
    <b>Am Mac</b> fragt der Kalender vorher noch was: Den Haken bei
    „Entfernen: Hinweise“ <b>rausnehmen</b>, sonst kriegst du keine
    Erinnerungen. Und „Automatisch aktualisieren“ auf <b>Jede Stunde</b>
    stellen. Wöchentlich ist zu selten, dann kriegst du Verlegungen zu spät mit.
  </p>
  <p class="tipp" data-ios-tipp hidden>
    <b>Tipp:</b> Diese Seite über <b>Teilen&nbsp;→ Zum Home-Bildschirm</b> ablegen.
    Dann liegt der Spielplan als App auf dem Handy.
  </p>
</div>

<div class="weg">
  <h3>Android und Google Kalender</h3>
  <p>Bei Google geht das Abonnieren nur am Computer, nicht in der Handy-App.
     Einmal am Rechner einrichten, danach ist es auf dem Handy.</p>
  <button class="knopf stumm" type="button" data-kopiere="{ics_url}">Adresse kopieren</button>
  <ol class="schritte">
    <li>Am Computer <code>calendar.google.com</code> öffnen</li>
    <li>Links bei „Weitere Kalender“ auf <strong>+</strong> klicken</li>
    <li>„Per URL“ wählen, Adresse einfügen, hinzufügen</li>
  </ol>
</div>

<div class="weg">
  <h3>Einmalig importieren</h3>
  <p>Ohne Abo. Spätere Verlegungen kommen dann nicht mehr an.</p>
  <a class="knopf stumm" href="{sicher(team['datei'])}" download>Datei herunterladen</a>
</div>"""


def spieldaten_kompakt(teams: dict) -> str:
    """Alle Spiele in einer knappen Liste fuer die verschraenkte Ansicht.

    Kurze Schluesselnamen, weil das im Dokument landet: bei 338 Spielen
    macht das den Unterschied zwischen 40 und 90 kB."""
    eintraege = []
    for schluessel, team in teams.items():
        for spiel in (team.get("spiele") or {}).values():
            e = {
                "m": schluessel,
                "n": team.get("name", ""),
                "d": spiel["datum"],
                "g": spiel.get("gegner", ""),
                "h": spiel.get("halle", ""),
                "o": spiel.get("ort", ""),
                "z": 1 if spiel.get("heim") else 0,
            }
            if spiel.get("ohne_zeit"):
                e["k"] = 1                      # keine Anwurfzeit
            if spiel.get("lat") and spiel.get("lon"):
                e["p"] = [round(float(spiel["lat"]), 4), round(float(spiel["lon"]), 4)]
            if spiel.get("ergebnis"):
                erg = spiel["ergebnis"]
                e["e"] = [erg["eigene"], erg["fremde"], erg["ausgang"]]
            eintraege.append(e)
    eintraege.sort(key=lambda x: x["d"])
    return json.dumps(eintraege, ensure_ascii=False, separators=(",", ":"))


def mannschaftsblock(schluessel: str, team: dict, basis: str, heute: datetime,
                     worker: str = "") -> str:
    spiele_mit_code = sorted((team.get("spiele") or {}).items(),
                             key=lambda kv: kv[1]["datum"])
    spiele = [s for _, s in spiele_mit_code]
    kommend = [(c, s) for c, s in spiele_mit_code
               if zeit(s) >= heute and not s.get("ergebnis")]
    vergangen = [c for c, s in spiele_mit_code
                 if s.get("ergebnis") or zeit(s) < heute]
    naechster_code = kommend[0][0] if kommend else ""
    vorheriger_code = vergangen[-1] if vergangen else ""
    kommend = [s for _, s in kommend]

    kopf = " &middot; ".join(t for t in [
        sicher(team.get("liga")), spiel_wort(len(spiele))] if t)

    return f"""<section data-team="{sicher(schluessel)}" hidden>
  <p class="liga">{kopf}</p>
  {hero(kommend[0], team['kurzname'], heute) if kommend else
   '<p class="marker">Saison beendet</p>'}
  {hinspiel_und_gegner(kommend[0], spiele, team.get('tabelle') or {}) if kommend else ''}
  {mitmachblock(naechster_code, vorheriger_code, worker,
                *paarung_namen(kommend[0], team), schluessel) if kommend else ''}
  {aenderungsblock(team)}

  <nav class="reiter" role="tablist" aria-label="Bereiche">
    <button type="button" role="tab" data-ziel="kalender" aria-selected="true">Kalender</button>
    <button type="button" role="tab" data-ziel="spiele" aria-selected="false">Spiele</button>
    <button type="button" role="tab" data-ziel="tabelle" aria-selected="false">Tabelle</button>
    <button type="button" role="tab" data-ziel="statistik" aria-selected="false">Statistik</button>
  </nav>

  <div class="teil" data-ansicht="kalender">{abo_block(team, basis)}
    {teilenblock(team, kommend[0] if kommend else None,
                 letztes_ergebnis(spiele))}</div>
  <div class="teil" data-ansicht="spiele" hidden>{spielliste(spiele, heute)}</div>
  <div class="teil" data-ansicht="tabelle" hidden>
    {formblock(team.get('form') or [])}
    {verlaufsblock(team.get('tabelle') or {})}
    {tabellenblock(team.get('tabelle') or {}, team.get('team_id'))}
  </div>
  <div class="teil" data-ansicht="statistik" hidden>
    {statistikblock(team.get('statistik') or {})}
  </div>
</section>"""


# --------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description="Abo-Seite fuer die Spielplaene bauen")
    p.add_argument("--daten", default="docs/daten.json")
    p.add_argument("--basis-url", default="https://example.github.io/handball-kalender")
    p.add_argument("--out", default="docs/index.html")
    p.add_argument("--worker-url", default="",
                   help="Adresse des Zaehler-Workers; leer = Funktion aus")
    cfg = p.parse_args()

    daten = json.loads(Path(cfg.daten).read_text(encoding="utf-8"))
    teams = daten.get("teams") or {}
    heute = datetime.now(TZ)

    # Nach Gruppen gliedern: 23 Einträge in einer Liste findet niemand.
    gruppen: dict[str, list[str]] = {}
    for k, t in teams.items():
        gruppen.setdefault(t.get("gruppe") or "Mannschaften", []).append(
            f'<option value="{sicher(k)}">{sicher(t["name"])}</option>')
    optionen = ('<option value="meine" hidden>Meine Mannschaften</option>'
                + "".join(
        f'<optgroup label="{sicher(name)}" data-gruppe="{sicher(name)}">{"".join(eintraege)}</optgroup>'
        for name, eintraege in gruppen.items()))
    bloecke = "".join(
        mannschaftsblock(k, t, cfg.basis_url, heute, cfg.worker_url)
        for k, t in teams.items())

    saison = next((t.get("saison") for t in teams.values() if t.get("saison")), "")
    stand_text = "unbekannt"
    if daten.get("aktualisiert"):
        w = datetime.fromisoformat(daten["aktualisiert"]).astimezone(TZ)
        stand_text = f"{w:%d.%m.%Y} um {w:%H:%M} Uhr"

    seite = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Spielplan {sicher(daten.get('verein', ''))}</title>
<meta name="description" content="Spielpläne zum Abonnieren – alle Spiele
automatisch im Handykalender, Verlegungen inklusive.">
<meta name="theme-color" content="#14140f">
<link rel="manifest" href="manifest.json">
<link rel="icon" href="icon-32.png" sizes="32x32">
<link rel="apple-touch-icon" href="icon-180.png">
<meta name="apple-mobile-web-app-title" content="MuRu Spielplan">
<style>{STIL}</style>
</head>
<body>

<header class="kopf">
  <div class="huelle">
    <button id="ansicht" type="button" aria-label="Ansicht umschalten">
      <svg class="mond" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"
           aria-hidden="true">
        <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z"/>
      </svg>
      <svg class="sonne" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"
           aria-hidden="true">
        <circle cx="12" cy="12" r="4.2"/>
        <path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.2 5.2l1.4 1.4M17.4 17.4l1.4 1.4M18.8 5.2l-1.4 1.4M6.6 17.4l-1.4 1.4"/>
      </svg>
    </button>
    <div class="marke">
      <img src="logo.png" alt="Wappen der HSG Mutterstadt/Ruchheim" width="149" height="200">
      <div>
        <div class="zeile1">{sicher(daten.get('verein', ''))}</div>
        <div class="zeile2">Die Füchse</div>
      </div>
    </div>
    <h1>Spielplan</h1>
    <p class="saison">Saison {sicher(saison)}</p>
    <div class="wahl">
      <label for="teamwahl">Mannschaft</label>
      <select id="teamwahl">{optionen}</select>
      <button id="anheften" type="button" aria-pressed="false"
              title="Mannschaft oben in der Liste festhalten">Anheften</button>
      <p class="anheftwink" id="anheftwink" hidden></p>
      <p class="uebersichtlink"><a href="wochenende.html">Alle Spiele am Wochenende &rsaquo;</a></p>
    </div>
  </div>
</header>

<main class="huelle">
  <section data-team="meine" hidden>
    <p class="liga" id="meine-kopf">Angeheftete Mannschaften</p>
    <div id="meine-inhalt"></div>
  </section>
{bloecke}
  <p class="fuss">
    Zuletzt abgeglichen am {stand_text}. Die Spielpläne werden täglich automatisch
    mit <a href="https://www.handball.net" target="_blank" rel="noopener">handball.net</a>
    abgeglichen; Änderungen erscheinen hier und in abonnierten Kalendern.
  </p>
</main>

<script id="spieldaten" type="application/json">{spieldaten_kompakt(teams)}</script>
<script>{ANSICHT}
{SKRIPT}{MEINE}
{TIPP}
{GRAFIK}
{ZAEHLUNG}</script>
</body>
</html>
"""
    ziel = Path(cfg.out)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(seite, encoding="utf-8")
    print(f"Seite geschrieben: {ziel} ({len(teams)} Mannschaften)")


if __name__ == "__main__":
    main()
