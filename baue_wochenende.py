#!/usr/bin/env python3
"""Erzeugt docs/wochenende.html - alle Spiele aller Mannschaften nach Tag.

Gedacht fuer alle, die nicht ihren eigenen Spielplan suchen, sondern wissen
wollen, wer wann wo spielt: Zuschauer, Eltern, Betreuer.
"""

from __future__ import annotations

import argparse
import html
import json
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from seite_stil import STIL

TZ = ZoneInfo("Europe/Berlin")
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
              "Freitag", "Samstag", "Sonntag"]
TAGE_VORAUS = 14


def sicher(text) -> str:
    return html.escape(str(text if text is not None else ""))


def strasse(spiel: dict) -> str:
    ort, halle = spiel.get("ort") or "", spiel.get("halle") or ""
    if halle and ort.startswith(halle):
        ort = ort[len(halle):].lstrip(", ")
    return ort


def kartenlink(spiel: dict) -> str:
    ziel = " ".join(t for t in [spiel.get("halle"), strasse(spiel)] if t)
    return "https://www.google.com/maps/search/?api=1&amp;query=" + urllib.parse.quote(ziel)


def sammle(daten: dict, von: datetime, bis: datetime) -> list[dict]:
    """Alle Spiele im Zeitraum, quer über alle Mannschaften."""
    treffer = []
    for team in (daten.get("teams") or {}).values():
        for spiel in (team.get("spiele") or {}).values():
            wann = datetime.fromisoformat(spiel["datum"]).replace(tzinfo=TZ)
            if von <= wann <= bis:
                treffer.append({**spiel, "mannschaft": team.get("name", ""),
                                "kurzname": team.get("kurzname", ""),
                                "wann": wann})
    # Nach Zeit, bei gleicher Zeit nach Mannschaft
    return sorted(treffer, key=lambda s: (s["wann"], s["mannschaft"]))


def zeile(spiel: dict) -> str:
    heim = spiel.get("heim")
    uhr = ("offen" if spiel.get("ohne_zeit") else f'{spiel["wann"]:%H:%M}')
    halle = sicher(spiel.get("halle")) or "Halle offen"
    ort = (f'<a href="{kartenlink(spiel)}" target="_blank" rel="noopener">{halle}</a>'
           if spiel.get("ort") else halle)
    ergebnis = ""
    if spiel.get("ergebnis"):
        e = spiel["ergebnis"]
        ergebnis = (f'<span class="stand {e["ausgang"]}">{e["heim"]}:{e["gast"]}</span>')
    return f"""<div class="partie{' heimspiel' if heim else ''}" data-heim="{'ja' if heim else 'nein'}">
<div class="uhr">{uhr}</div>
<div><div class="wer">{sicher(spiel.get('mannschaft'))}</div>
<div class="gegen">{'gegen' if heim else 'bei'} {sicher(spiel.get('gegner'))}</div>
<div class="wo">{ort}</div></div>
<div class="rechts"><div class="hz {'heim' if heim else ''}">{'H' if heim else 'A'}</div>{ergebnis}</div>
</div>"""


def main() -> None:
    p = argparse.ArgumentParser(description="Wochenend-Uebersicht bauen")
    p.add_argument("--daten", default="docs/daten.json")
    p.add_argument("--out", default="docs/wochenende.html")
    cfg = p.parse_args()

    daten = json.loads(Path(cfg.daten).read_text(encoding="utf-8"))
    jetzt = datetime.now(TZ)
    von = jetzt.replace(hour=0, minute=0, second=0, microsecond=0)
    bis = von + timedelta(days=TAGE_VORAUS)
    spiele = sammle(daten, von, bis)

    bloecke, letzter_tag = [], None
    for spiel in spiele:
        tag = spiel["wann"].date()
        if tag != letzter_tag:
            heute_morgen = ("Heute" if tag == jetzt.date()
                            else "Morgen" if tag == jetzt.date() + timedelta(days=1)
                            else WOCHENTAGE[spiel["wann"].weekday()])
            bloecke.append(f'<div class="tag">{heute_morgen}, {spiel["wann"]:%d.%m.}</div>')
            letzter_tag = tag
        bloecke.append(zeile(spiel))

    inhalt = "".join(bloecke) if bloecke else (
        '<p class="statfuss">In den nächsten zwei Wochen ist nichts angesetzt.</p>')
    heimspiele = sum(1 for s in spiele if s.get("heim"))

    seite = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Wer spielt wann – HSG Mutterstadt/Ruchheim</title>
<meta name="description" content="Alle Spiele aller Mannschaften der HSG
Mutterstadt/Ruchheim in den nächsten zwei Wochen.">
<meta name="theme-color" content="#14140f">
<link rel="icon" href="icon-32.png" sizes="32x32">
<link rel="apple-touch-icon" href="icon-180.png">
<style>{STIL}{ZUSATZSTIL}</style>
</head>
<body>

<header class="kopf">
  <div class="huelle">
    <div class="marke">
      <img src="logo.png" alt="Wappen der HSG Mutterstadt/Ruchheim" width="149" height="200">
      <div>
        <div class="zeile1">HSG Mutterstadt/Ruchheim</div>
        <div class="zeile2">Alle Mannschaften</div>
      </div>
    </div>
    <h1>Wer spielt<br>wann</h1>
    <p class="saison">{len(spiele)} Spiele in den nächsten zwei Wochen,
       davon {heimspiele} zu Hause</p>
    <p class="uebersichtlink"><a href="./">Zum Spielplan einer Mannschaft &rsaquo;</a></p>
  </div>
</header>

<main class="huelle">
  <div class="filter" role="group" aria-label="Auswahl">
    <button type="button" data-filter="alle" aria-pressed="true">Alle Spiele</button>
    <button type="button" data-filter="heim" aria-pressed="false">Nur Heimspiele</button>
  </div>

  <div id="liste">{inhalt}</div>

  <p class="fuss">
    Stand: {jetzt:%d.%m.%Y, %H:%M} Uhr. Wird täglich mit
    <a href="https://www.handball.net" target="_blank" rel="noopener">handball.net</a>
    abgeglichen. <a href="./">Spielplan abonnieren</a>
  </p>
</main>

<script>
(function () {{
  var knoepfe = [].slice.call(document.querySelectorAll('[data-filter]'));
  var liste = document.getElementById('liste');

  function setze(art) {{
    knoepfe.forEach(function (k) {{
      k.setAttribute('aria-pressed', k.getAttribute('data-filter') === art ? 'true' : 'false');
    }});
    liste.querySelectorAll('.partie').forEach(function (p) {{
      p.hidden = art === 'heim' && p.getAttribute('data-heim') !== 'ja';
    }});
    // Tagesüberschriften ohne sichtbare Spiele verschwinden mit
    var sichtbar = false, letzte = null;
    [].slice.call(liste.children).reverse().forEach(function (el) {{
      if (el.classList.contains('tag')) {{
        el.hidden = !sichtbar;
        sichtbar = false;
      }} else if (!el.hidden) {{
        sichtbar = true;
      }}
    }});
  }}

  knoepfe.forEach(function (k) {{
    k.addEventListener('click', function () {{ setze(k.getAttribute('data-filter')); }});
  }});
}})();
</script>
</body>
</html>
"""
    ziel = Path(cfg.out)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(seite, encoding="utf-8")
    print(f"Übersicht geschrieben: {ziel} ({len(spiele)} Spiele, {heimspiele} Heimspiele)")


ZUSATZSTIL = """
.filter { display: flex; margin: 30px 0 6px; }
.filter button { font: inherit; font-size: .88rem; font-weight: 600; cursor: pointer;
                 background: transparent; color: var(--leise);
                 border: 1px solid var(--linie); padding: 10px 16px; margin-right: -1px; }
.filter button[aria-pressed="true"] { color: var(--tinte); border-color: var(--tinte);
                                      position: relative; z-index: 1; }
.tag { font-size: .82rem; font-weight: 600; letter-spacing: .06em;
       text-transform: uppercase; color: var(--leise); padding: 30px 0 10px; }
.partie { display: grid; grid-template-columns: 58px 1fr auto; gap: 0 14px;
          align-items: start; padding: 14px 0; border-top: 1px solid var(--linie); }
.partie .uhr { font-size: .88rem; font-weight: 600; }
.partie .wer { font-size: 1.02rem; font-weight: 600; line-height: 1.3; }
.partie .gegen { font-size: .95rem; line-height: 1.35; overflow-wrap: anywhere; }
.partie .wo { font-size: .86rem; color: var(--leise); margin-top: 2px; }
.partie .wo a { text-decoration: none; box-shadow: inset 0 -1px 0 var(--linie); }
.partie .wo a:hover { box-shadow: inset 0 -1px 0 var(--gold); }
.partie.heimspiel { box-shadow: inset 3px 0 0 var(--gold); padding-left: 12px;
                    margin-left: -12px; }
"""

if __name__ == "__main__":
    main()
