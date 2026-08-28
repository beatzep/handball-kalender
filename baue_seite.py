#!/usr/bin/env python3
"""Erzeugt die Abo-Seite (index.html) aus der Zustandsdatei des Generators.

Die Seite liegt auf GitHub Pages neben der .ics und ist das, was die
Mannschaft zu sehen bekommt: drei Wege in den Kalender, der Stand der
letzten Aktualisierung und die Liste der Spiele.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")
WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

SEITE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITEL}}</title>
<style>
:root {
  color-scheme: light dark;
  --bg: #f6f7f9; --karte: #ffffff; --text: #14171c; --leise: #5c6570;
  --rand: #e2e6ea; --akzent: #1a6b3c; --akzent-text: #ffffff; --warn: #8a4b00;
  --warn-bg: #fff6e6;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #121417; --karte: #1b1f24; --text: #e8ebee; --leise: #9aa4af;
    --rand: #2b3138; --akzent: #4cc38a; --akzent-text: #06120b; --warn: #ffc46b;
    --warn-bg: #2a2113;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 24px 16px 64px; background: var(--bg); color: var(--text);
  font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
main { max-width: 640px; margin: 0 auto; }
h1 { font-size: 1.6rem; line-height: 1.25; margin: 0 0 4px; }
h2 { font-size: 1.05rem; margin: 32px 0 12px; }
.leise { color: var(--leise); font-size: .9rem; }
.karte {
  background: var(--karte); border: 1px solid var(--rand); border-radius: 12px;
  padding: 16px; margin: 12px 0;
}
a.knopf {
  display: block; background: var(--akzent); color: var(--akzent-text);
  text-decoration: none; text-align: center; font-weight: 600;
  padding: 14px 16px; border-radius: 10px; margin: 10px 0;
}
button.knopf {
  width: 100%; font: inherit; font-weight: 600; cursor: pointer;
  background: transparent; color: var(--text); border: 1px solid var(--rand);
  padding: 14px 16px; border-radius: 10px; margin: 10px 0;
}
ol, ul { padding-left: 20px; margin: 8px 0; }
li { margin: 4px 0; }
code {
  background: var(--bg); border: 1px solid var(--rand); border-radius: 6px;
  padding: 2px 6px; font-size: .82rem; word-break: break-all;
}
table { width: 100%; border-collapse: collapse; font-size: .92rem; }
td { padding: 9px 6px; border-bottom: 1px solid var(--rand); vertical-align: top; }
td.tag { white-space: nowrap; color: var(--leise); width: 1%; }
tr.vorbei { opacity: .42; }
.warnung {
  background: var(--warn-bg); border: 1px solid var(--warn); color: var(--warn);
  border-radius: 10px; padding: 14px 16px; margin: 12px 0;
}
.warnung strong { display: block; margin-bottom: 6px; }
</style>
</head>
<body>
<main>
<h1>{{TITEL}}</h1>
<p class="leise">Alle {{ANZAHL}} Saisonspiele im Handykalender — Termin, Halle mit
Adresse und Erinnerung. Verlegungen werden automatisch nachgezogen.</p>

{{AENDERUNGEN}}

<h2>In den Kalender holen</h2>

<div class="karte">
<strong>iPhone, iPad oder Mac</strong>
<p class="leise">Antippen, „Abonnieren" bestätigen — fertig.</p>
<a class="knopf" href="{{WEBCAL}}">Kalender abonnieren</a>
</div>

<div class="karte">
<strong>Android / Google Kalender</strong>
<p class="leise">Google lässt Kalender-Abos leider nur am Computer einrichten,
nicht in der Handy-App. Einmal am Rechner machen, danach ist es auf dem Handy.</p>
<button class="knopf" onclick="kopiere('{{ICS_URL}}', this)">Adresse kopieren</button>
<ol class="leise">
<li>Am Computer <code>calendar.google.com</code> öffnen</li>
<li>Links bei „Weitere Kalender" auf <strong>+</strong> klicken</li>
<li><strong>Per URL</strong> wählen, Adresse einfügen, hinzufügen</li>
</ol>
<p class="leise">Samsung Kalender zeigt den Kalender danach automatisch mit an.</p>
</div>

<div class="karte">
<strong>Nur einmalig importieren</strong>
<p class="leise">Ohne Abo — spätere Verlegungen kommen dann nicht an.</p>
<a class="knopf" style="background:transparent;color:var(--text);border:1px solid var(--rand)"
   href="{{DATEI}}" download>Datei herunterladen</a>
</div>

<h2>Spielplan</h2>
<table>{{TABELLE}}</table>

<p class="leise" style="margin-top:28px">
Zuletzt aktualisiert: {{STAND}}<br>
Daten von handball.net. Wird täglich automatisch abgeglichen.
</p>
</main>
<script>
function kopiere(text, knopf) {
  navigator.clipboard.writeText(text).then(function () {
    var alt = knopf.textContent;
    knopf.textContent = "Kopiert";
    setTimeout(function () { knopf.textContent = alt; }, 1800);
  });
}
</script>
</body>
</html>
"""


def zeile(code: str, spiel: dict, heute: datetime) -> str:
    wann = datetime.fromisoformat(spiel["datum"]).replace(tzinfo=TZ)
    marke = "\U0001F3E0" if spiel.get("heim") else "\U0001F697"
    halle = spiel.get("halle") or (spiel.get("ort") or "").split(",")[0].strip()
    klasse = ' class="vorbei"' if wann < heute else ""
    return (f'<tr{klasse}><td class="tag">{WOCHENTAGE[wann.weekday()]} '
            f'{wann:%d.%m.}<br>{wann:%H:%M}</td>'
            f'<td>{marke} {spiel.get("gegner","?")}<br>'
            f'<span class="leise">{halle}</span></td></tr>')


def main() -> None:
    p = argparse.ArgumentParser(description="Abo-Seite fuer den Spielplan-Feed bauen")
    p.add_argument("--stand", default="docs/stand.json")
    p.add_argument("--ics", default="spielplan.ics",
                   help="Dateiname der .ics relativ zur Seite")
    p.add_argument("--basis-url", default="https://example.github.io/handball-kalender",
                   help="oeffentliche Basis-URL ohne Schraegstrich am Ende")
    p.add_argument("--out", default="docs/index.html")
    cfg = p.parse_args()

    daten = json.loads(Path(cfg.stand).read_text(encoding="utf-8"))
    spiele = daten.get("spiele", {})
    heute = datetime.now(TZ)

    sortiert = sorted(spiele.items(), key=lambda kv: kv[1]["datum"])
    tabelle = "".join(zeile(code, spiel, heute) for code, spiel in sortiert)

    aenderungen = daten.get("letzte_aenderungen") or []
    if aenderungen:
        punkte = "".join(f"<li>{a['text']}</li>" for a in aenderungen)
        block = (f'<div class="warnung"><strong>Zuletzt geändert</strong>'
                 f'<ul>{punkte}</ul></div>')
    else:
        block = ""

    ics_url = f"{cfg.basis_url.rstrip('/')}/{cfg.ics}"
    webcal = ics_url.replace("https://", "webcal://").replace("http://", "webcal://")

    stand_text = "unbekannt"
    if daten.get("aktualisiert"):
        wann = datetime.fromisoformat(daten["aktualisiert"]).astimezone(TZ)
        stand_text = f"{wann:%d.%m.%Y, %H:%M} Uhr"

    seite = (SEITE
             .replace("{{TITEL}}", daten.get("kalender", "Spielplan"))
             .replace("{{ANZAHL}}", str(len(spiele)))
             .replace("{{AENDERUNGEN}}", block)
             .replace("{{TABELLE}}", tabelle)
             .replace("{{WEBCAL}}", webcal)
             .replace("{{ICS_URL}}", ics_url)
             .replace("{{DATEI}}", cfg.ics)
             .replace("{{STAND}}", stand_text))

    ziel = Path(cfg.out)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(seite, encoding="utf-8")
    print(f"Seite geschrieben: {ziel} ({len(spiele)} Spiele, "
          f"{len(aenderungen)} Änderung(en))")


if __name__ == "__main__":
    main()
