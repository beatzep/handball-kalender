#!/usr/bin/env python3
"""Erzeugt die Abo-Seite (index.html) aus der Zustandsdatei des Generators.

Gestaltung orientiert sich an der Vereinsseite hsg-muru-handball.de:
Vereinsgold #DD9933 auf Schwarz, Versalien mit Sperrung fuer Rubriken.
"""

from __future__ import annotations

import argparse
import html
import json
import urllib.parse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
              "Freitag", "Samstag", "Sonntag"]
KURZTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]

STIL = """
:root {
  --gold: #dd9933;
  --gold-tief: #b87a22;
  --gold-schwach: rgba(221,153,51,.12);
  --tinte: #14140f;
  --tinte-weich: #3d3d36;
  --leise: #6e6e64;
  --linie: #e3e0d8;
  --flaeche: #ffffff;
  --grund: #f7f5f0;
  --schwarz: #14140f;
  --auf-schwarz: #f7f5f0;
}
@media (prefers-color-scheme: dark) {
  :root {
    --gold: #e8ac52;
    --gold-tief: #dd9933;
    --gold-schwach: rgba(232,172,82,.14);
    --tinte: #f2efe8;
    --tinte-weich: #c3bfb4;
    --leise: #8c877c;
    --linie: #2e2c27;
    --flaeche: #1a1916;
    --grund: #100f0d;
    --schwarz: #000000;
    --auf-schwarz: #f2efe8;
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  background: var(--grund);
  color: var(--tinte);
  font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        "Helvetica Neue", Arial, sans-serif;
  font-variant-numeric: tabular-nums;
  -webkit-font-smoothing: antialiased;
}
.huelle { max-width: 660px; margin: 0 auto; padding: 0 20px; }

/* ---------- Kopf ---------- */
.kopf { background: var(--schwarz); color: var(--auf-schwarz);
        border-bottom: 3px solid var(--gold); }
.kopf .huelle { padding-top: 30px; padding-bottom: 30px; }
.verein {
  font-size: .68rem; font-weight: 700; letter-spacing: .18em;
  text-transform: uppercase; color: var(--gold); margin: 0 0 10px;
}
.kopf h1 {
  margin: 0; font-size: 2.1rem; line-height: 1.1; font-weight: 800;
  letter-spacing: -.02em;
}
.unterzeile {
  margin: 10px 0 0; font-size: .88rem; color: rgba(247,245,240,.62);
}
.unterzeile b { color: rgba(247,245,240,.9); font-weight: 600; }

/* ---------- Rubriken ---------- */
.rubrik {
  font-size: .7rem; font-weight: 700; letter-spacing: .16em;
  text-transform: uppercase; color: var(--leise);
  margin: 44px 0 14px; display: flex; align-items: center; gap: 12px;
}
.rubrik::after {
  content: ""; flex: 1; height: 1px; background: var(--linie);
}

/* ---------- Nächstes Spiel ---------- */
.naechstes {
  background: var(--flaeche); border: 1px solid var(--linie);
  border-left: 3px solid var(--gold); border-radius: 3px;
  padding: 22px; margin-top: 26px;
  box-shadow: 0 1px 2px rgba(20,20,15,.05);
}
.naechstes .wann {
  font-size: .72rem; font-weight: 700; letter-spacing: .14em;
  text-transform: uppercase; color: var(--gold-tief); margin-bottom: 8px;
}
.naechstes .paarung {
  font-size: 1.32rem; font-weight: 700; line-height: 1.25; margin-bottom: 12px;
}
.naechstes dl { margin: 0; display: grid; grid-template-columns: auto 1fr;
                gap: 5px 16px; font-size: .9rem; }
.naechstes dt { color: var(--leise); }
.naechstes dd { margin: 0; }
.naechstes dd a { color: inherit; text-decoration: none;
                  border-bottom: 1px solid var(--gold); }
.naechstes dd a:hover { color: var(--gold-tief); }

/* ---------- Abo-Wege ---------- */
.weg {
  background: var(--flaeche); border: 1px solid var(--linie);
  border-radius: 3px; padding: 20px; margin-bottom: 12px;
}
.weg h3 { margin: 0 0 4px; font-size: 1rem; font-weight: 700; }
.weg p { margin: 0 0 14px; font-size: .88rem; color: var(--tinte-weich); }
.knopf {
  display: block; width: 100%; text-align: center; text-decoration: none;
  font: inherit; font-size: .95rem; font-weight: 700; letter-spacing: .01em;
  padding: 13px 18px; border-radius: 2px; cursor: pointer;
  border: 1px solid var(--gold); background: var(--gold); color: #14140f;
  transition: background .15s ease, border-color .15s ease;
}
.knopf:hover { background: var(--gold-tief); border-color: var(--gold-tief); }
.knopf.stumm {
  background: transparent; color: var(--tinte); border-color: var(--linie);
}
.knopf.stumm:hover { border-color: var(--gold); background: var(--gold-schwach); }
.knopf:focus-visible { outline: 2px solid var(--gold-tief); outline-offset: 2px; }
.schritte {
  margin: 14px 0 0; padding-left: 18px; font-size: .84rem;
  color: var(--tinte-weich);
}
.schritte li { margin: 5px 0; }
code {
  background: var(--gold-schwach); border-radius: 2px; padding: 1px 5px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .82em;
}

/* ---------- Hinweis auf Änderungen ---------- */
.hinweis {
  background: var(--gold-schwach); border: 1px solid var(--gold);
  border-radius: 3px; padding: 18px 20px; margin: 28px 0 0;
}
.hinweis h3 {
  margin: 0 0 8px; font-size: .72rem; font-weight: 700; letter-spacing: .14em;
  text-transform: uppercase; color: var(--gold-tief);
}
.hinweis ul { margin: 0; padding-left: 18px; font-size: .9rem; }
.hinweis li { margin: 4px 0; }

/* ---------- Spielplan ---------- */
.monat {
  font-size: .7rem; font-weight: 700; letter-spacing: .14em;
  text-transform: uppercase; color: var(--leise);
  padding: 22px 0 8px; border-bottom: 1px solid var(--linie);
}
.spiel {
  display: grid; grid-template-columns: 62px 1fr auto;
  gap: 0 14px; align-items: baseline;
  padding: 13px 0; border-bottom: 1px solid var(--linie);
}
.spiel .datum {
  font-size: .82rem; font-weight: 700; color: var(--tinte); line-height: 1.35;
}
.spiel .datum span { display: block; font-weight: 400; color: var(--leise); }
.spiel .gegner { font-size: .97rem; font-weight: 600; line-height: 1.35; }
.spiel .halle { font-size: .82rem; color: var(--leise); margin-top: 2px; }
.spiel .halle a { color: inherit; text-decoration: none;
                  border-bottom: 1px solid var(--linie); }
.spiel .halle a:hover { color: var(--gold-tief); border-color: var(--gold); }
.marke {
  font-size: .66rem; font-weight: 700; letter-spacing: .1em;
  width: 22px; height: 22px; line-height: 20px; text-align: center;
  border: 1px solid var(--gold); border-radius: 2px;
}
.marke.heim { background: var(--gold); color: #14140f; }
.marke.aus { color: var(--gold-tief); }
.spiel.vorbei { opacity: .38; }
.spiel.jetzt { background: var(--gold-schwach);
               box-shadow: inset 3px 0 0 var(--gold); padding-left: 12px;
               margin-left: -12px; }

/* ---------- Fuß ---------- */
.fuss {
  margin: 48px 0 0; padding: 22px 0 40px; border-top: 1px solid var(--linie);
  font-size: .8rem; color: var(--leise);
}
.fuss a { color: var(--leise); }
@media (max-width: 420px) {
  .kopf h1 { font-size: 1.7rem; }
  .spiel { grid-template-columns: 54px 1fr auto; }
}
"""


def sicher(text) -> str:
    return html.escape(str(text or ""))


def strasse(spiel: dict) -> str:
    """Adresse ohne den vorangestellten Hallennamen - der steht schon daneben."""
    ort, halle = spiel.get("ort") or "", spiel.get("halle") or ""
    if halle and ort.startswith(halle):
        ort = ort[len(halle):].lstrip(", ")
    return ort


def kartenlink(spiel: dict) -> str:
    ziel = " ".join(t for t in [spiel.get("halle"), strasse(spiel)] if t)
    # &amp;, weil die URL direkt in ein href-Attribut geschrieben wird
    return ("https://www.google.com/maps/search/?api=1&amp;query="
            + urllib.parse.quote(ziel))


def hero(spiel: dict, heute: datetime) -> str:
    wann = datetime.fromisoformat(spiel["datum"]).replace(tzinfo=TZ)
    tage = (wann.date() - heute.date()).days
    if tage == 0:
        relativ = "Heute"
    elif tage == 1:
        relativ = "Morgen"
    elif tage < 7:
        relativ = f"In {tage} Tagen"
    else:
        relativ = "Nächstes Spiel"
    heim = spiel.get("heim")
    paarung = (f"HSG MuRu &ndash; {sicher(spiel.get('gegner'))}" if heim
               else f"{sicher(spiel.get('gegner'))} &ndash; HSG MuRu")
    return f"""<div class="naechstes">
<div class="wann">{relativ} &middot; {'Heimspiel' if heim else 'Auswärtsspiel'}</div>
<div class="paarung">{paarung}</div>
<dl>
<dt>Anwurf</dt><dd>{WOCHENTAGE[wann.weekday()]}, {wann:%d.%m.%Y}, {wann:%H:%M} Uhr</dd>
<dt>Halle</dt><dd>{sicher(spiel.get('halle'))}</dd>
<dt>Adresse</dt><dd><a href="{kartenlink(spiel)}" target="_blank"
rel="noopener">{sicher(strasse(spiel))}</a></dd>
</dl>
</div>"""


def spielzeile(spiel: dict, heute: datetime, naechstes: str | None, code: str) -> str:
    wann = datetime.fromisoformat(spiel["datum"]).replace(tzinfo=TZ)
    heim = spiel.get("heim")
    klassen = "spiel"
    if wann < heute:
        klassen += " vorbei"
    elif code == naechstes:
        klassen += " jetzt"
    halle = sicher(spiel.get("halle"))
    ort = (f'<a href="{kartenlink(spiel)}" target="_blank" rel="noopener">{halle}</a>'
           if spiel.get("ort") else halle)
    return f"""<div class="{klassen}">
<div class="datum">{KURZTAGE[wann.weekday()]} {wann:%d.%m.}<span>{wann:%H:%M}</span></div>
<div><div class="gegner">{sicher(spiel.get('gegner'))}</div>
<div class="halle">{ort}</div></div>
<div class="marke {'heim' if heim else 'aus'}">{'H' if heim else 'A'}</div>
</div>"""


def main() -> None:
    p = argparse.ArgumentParser(description="Abo-Seite fuer den Spielplan-Feed bauen")
    p.add_argument("--stand", default="docs/stand.json")
    p.add_argument("--ics", default="spielplan.ics")
    p.add_argument("--basis-url", default="https://example.github.io/handball-kalender")
    p.add_argument("--out", default="docs/index.html")
    cfg = p.parse_args()

    daten = json.loads(Path(cfg.stand).read_text(encoding="utf-8"))
    spiele = sorted(daten.get("spiele", {}).items(), key=lambda kv: kv[1]["datum"])
    heute = datetime.now(TZ)

    kommend = [(c, s) for c, s in spiele
               if datetime.fromisoformat(s["datum"]).replace(tzinfo=TZ) >= heute]
    naechster_code = kommend[0][0] if kommend else None

    # Spielplan nach Monaten gliedern
    tabelle, letzter_monat = [], None
    for code, spiel in spiele:
        wann = datetime.fromisoformat(spiel["datum"]).replace(tzinfo=TZ)
        monat = (wann.year, wann.month)
        if monat != letzter_monat:
            tabelle.append(f'<div class="monat">{MONATE[wann.month - 1]} {wann.year}</div>')
            letzter_monat = monat
        tabelle.append(spielzeile(spiel, heute, naechster_code, code))

    aenderungen = daten.get("letzte_aenderungen") or []
    hinweis = ""
    if aenderungen:
        punkte = "".join(f"<li>{sicher(a['text'])}</li>" for a in aenderungen)
        hinweis = (f'<div class="hinweis"><h3>Zuletzt geändert</h3>'
                   f'<ul>{punkte}</ul></div>')

    ics_url = f"{cfg.basis_url.rstrip('/')}/{cfg.ics}"
    webcal = ics_url.replace("https://", "webcal://").replace("http://", "webcal://")

    stand_text = "unbekannt"
    if daten.get("aktualisiert"):
        w = datetime.fromisoformat(daten["aktualisiert"]).astimezone(TZ)
        stand_text = f"{w:%d.%m.%Y} um {w:%H:%M} Uhr"

    kopfzeile = " &middot; ".join(t for t in [
        sicher(daten.get("liga")),
        f"Saison {sicher(daten.get('saison'))}" if daten.get("saison") else "",
        f"{len(spiele)} Spiele"] if t)

    seite = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{sicher(daten.get('kalender', 'Spielplan'))}</title>
<meta name="description" content="Spielplan zum Abonnieren – alle Spiele
automatisch im Handykalender, inklusive Verlegungen.">
<meta name="theme-color" content="#14140f">
<style>{STIL}</style>
</head>
<body>

<header class="kopf">
  <div class="huelle">
    <p class="verein">HSG Mutterstadt/Ruchheim</p>
    <h1>Herren I &ndash; Spielplan</h1>
    <p class="unterzeile">{kopfzeile}</p>
  </div>
</header>

<div class="huelle">
  {hero(kommend[0][1], heute) if kommend else ''}
  {hinweis}

  <div class="rubrik">In den Kalender</div>

  <div class="weg">
    <h3>iPhone, iPad und Mac</h3>
    <p>Antippen, „Abonnieren“ bestätigen. Verlegungen kommen danach von selbst an.</p>
    <a class="knopf" href="{webcal}">Kalender abonnieren</a>
  </div>

  <div class="weg">
    <h3>Android und Google Kalender</h3>
    <p>Google erlaubt das Abonnieren nur am Computer, nicht in der Handy-App.
       Einmal am Rechner einrichten – danach ist es auf dem Handy.</p>
    <button class="knopf stumm" onclick="kopiere('{ics_url}', this)">Adresse kopieren</button>
    <ol class="schritte">
      <li>Am Computer <code>calendar.google.com</code> öffnen</li>
      <li>Links bei „Weitere Kalender“ auf <strong>+</strong> klicken</li>
      <li><strong>Per URL</strong> wählen, Adresse einfügen, hinzufügen</li>
    </ol>
  </div>

  <div class="weg">
    <h3>Einmalig importieren</h3>
    <p>Ohne Abo. Spätere Verlegungen kommen dann nicht mehr an.</p>
    <a class="knopf stumm" href="{sicher(cfg.ics)}" download>Datei herunterladen</a>
  </div>

  <div class="rubrik">Alle Spiele</div>
  {''.join(tabelle)}

  <p class="fuss">
    Zuletzt abgeglichen am {stand_text}. Der Spielplan wird täglich automatisch
    mit <a href="https://www.handball.net" target="_blank" rel="noopener">handball.net</a>
    abgeglichen; Änderungen erscheinen hier und in abonnierten Kalendern.
  </p>
</div>

<script>
function kopiere(text, knopf) {{
  navigator.clipboard.writeText(text).then(function () {{
    var alt = knopf.textContent;
    knopf.textContent = "Adresse kopiert";
    setTimeout(function () {{ knopf.textContent = alt; }}, 1800);
  }});
}}
</script>
</body>
</html>
"""
    ziel = Path(cfg.out)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(seite, encoding="utf-8")
    print(f"Seite geschrieben: {ziel} ({len(spiele)} Spiele, "
          f"{len(aenderungen)} Änderung(en))")


if __name__ == "__main__":
    main()
