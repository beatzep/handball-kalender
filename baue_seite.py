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

from seite_skript import SKRIPT
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
<dl class="fakten">
<div><dt>Anwurf</dt><dd>{WOCHENTAGE[wann.weekday()]}, {wann:%d.%m.%Y}, {wann:%H:%M} Uhr</dd></div>
<div><dt>Halle</dt><dd>{sicher(spiel.get('halle'))}</dd></div>
<div><dt>Adresse</dt><dd><a href="{kartenlink(spiel)}" target="_blank"
rel="noopener">{sicher(strasse(spiel))}</a></dd></div>
</dl>"""


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
        rechts += (f'<div class="stand {erg["ausgang"]}">'
                   f'{erg["heim"]}:{erg["gast"]}</div>')

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


def mitmachblock(spiel_code: str, vorher_code: str | None, worker: str) -> str:
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
  <div class="dabei">
    <div class="titel">Bist du dabei?</div>
    <div class="reihe">
      <button type="button" data-dabei aria-pressed="false">Ich bin dabei</button>
      <span class="anzahl" data-anzahl></span>
    </div>
    <p class="fussnote">Ohne Namen, nur als Anhaltspunkt – gezählt wird pro Gerät,
       und du kannst dich jederzeit wieder abmelden.</p>
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


def tabellenblock(tabelle: dict, eigenes_team: int | None) -> str:
    """Vor dem ersten Spieltag steht ueberall 0 - die Reihenfolge ist dann
    ohne Aussage, darum der Hinweis darunter."""
    if not tabelle or not tabelle.get("eintraege"):
        return "<p class=\"tabellenfuss\">Für diese Liga liegt noch keine Tabelle vor.</p>"

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
            else "Die Saison hat noch nicht begonnen – alle Mannschaften stehen "
                 "bei null, die Reihenfolge hat noch keine Aussagekraft.")

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
  <p>Antippen, „Abonnieren“ bestätigen. Verlegungen kommen danach von selbst an.</p>
  <a class="knopf" href="{webcal}">{sicher(team['name'])} abonnieren</a>
  <p class="tipp">
    <b>Am Mac</b> fragt der Kalender vorher nach Einstellungen: Haken bei
    „Entfernen: Hinweise“ <b>abwählen</b> (sonst fehlen die Erinnerungen) und
    „Automatisch aktualisieren“ auf <b>Jede Stunde</b> stellen – der Standard
    „Wöchentlich“ ist für Verlegungen zu träge.
  </p>
  <p class="tipp" data-ios-tipp hidden>
    <b>Tipp:</b> Diese Seite über <b>Teilen&nbsp;→ Zum Home-Bildschirm</b> ablegen –
    dann liegt der Spielplan als App auf dem Handy.
  </p>
</div>

<div class="weg">
  <h3>Android und Google Kalender</h3>
  <p>Google erlaubt das Abonnieren nur am Computer, nicht in der Handy-App.
     Einmal am Rechner einrichten – danach ist es auf dem Handy.</p>
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
        sicher(team.get("liga")), f"{len(spiele)} Spiele"] if t)

    return f"""<section data-team="{sicher(schluessel)}" hidden>
  <p class="liga">{kopf}</p>
  {hero(kommend[0], team['kurzname'], heute) if kommend else
   '<p class="marker">Saison beendet</p>'}
  {mitmachblock(naechster_code, vorheriger_code, worker) if kommend else ''}
  {aenderungsblock(team)}

  <nav class="reiter" role="tablist" aria-label="Bereiche">
    <button type="button" role="tab" data-ziel="kalender" aria-selected="true">In den Kalender</button>
    <button type="button" role="tab" data-ziel="spiele" aria-selected="false">Alle Spiele</button>
    <button type="button" role="tab" data-ziel="tabelle" aria-selected="false">Tabelle</button>
  </nav>

  <div class="teil" data-ansicht="kalender">{abo_block(team, basis)}</div>
  <div class="teil" data-ansicht="spiele" hidden>{spielliste(spiele, heute)}</div>
  <div class="teil" data-ansicht="tabelle" hidden>
    {formblock(team.get('form') or [])}
    {verlaufsblock(team.get('tabelle') or {})}
    {tabellenblock(team.get('tabelle') or {}, team.get('team_id'))}
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

    optionen = "".join(
        f'<option value="{sicher(k)}">{sicher(t["name"])}</option>'
        for k, t in teams.items())
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
    </div>
  </div>
</header>

<main class="huelle">
{bloecke}
  <p class="fuss">
    Zuletzt abgeglichen am {stand_text}. Die Spielpläne werden täglich automatisch
    mit <a href="https://www.handball.net" target="_blank" rel="noopener">handball.net</a>
    abgeglichen; Änderungen erscheinen hier und in abonnierten Kalendern.
  </p>
</main>

<script>{SKRIPT}</script>
</body>
</html>
"""
    ziel = Path(cfg.out)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(seite, encoding="utf-8")
    print(f"Seite geschrieben: {ziel} ({len(teams)} Mannschaften)")


if __name__ == "__main__":
    main()
