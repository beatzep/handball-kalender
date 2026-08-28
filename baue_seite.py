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
/* Formensprache nach mckinsey.de: durchgaengig border-radius 0, keine
   umrandeten Karten, Gliederung ueber Weissraum und 1px-Linien, grosse
   Ueberschriften in leichtem Schnitt. Farben vom Verein. Mobil zuerst. */
:root {
  --gold: #dd9933;
  --gold-tief: #b87a22;
  --gold-schwach: rgba(221,153,51,.10);
  --tinte: #14140f;
  --tinte-weich: #4a4a42;
  --leise: #7a776d;
  --linie: #dedbd3;
  --linie-zart: #ebe9e3;
  --grund: #ffffff;
  --schwarz: #14140f;
  --auf-schwarz: #f7f5f0;
}
@media (prefers-color-scheme: dark) {
  :root {
    --gold: #e8ac52;
    --gold-tief: #dd9933;
    --gold-schwach: rgba(232,172,82,.12);
    --tinte: #f2efe8;
    --tinte-weich: #b8b4a9;
    --leise: #8c877c;
    --linie: #33312b;
    --linie-zart: #24221e;
    --grund: #0d0d0b;
    --schwarz: #000000;
    --auf-schwarz: #f2efe8;
  }
}
*, *::before, *::after { box-sizing: border-box; border-radius: 0; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  background: var(--grund);
  color: var(--tinte);
  font: 400 17px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        "Helvetica Neue", Arial, sans-serif;
  font-variant-numeric: tabular-nums;
  -webkit-font-smoothing: antialiased;
}
.huelle { max-width: 720px; margin: 0 auto; padding: 0 22px; }
a { color: inherit; }

/* ---------- Kopf ---------- */
.kopf { background: var(--schwarz); color: var(--auf-schwarz);
        border-bottom: 2px solid var(--gold); }
.kopf .huelle { padding: 26px 22px 34px; }
.marke { display: flex; align-items: center; gap: 14px; margin-bottom: 30px; }
.marke img { width: 54px; height: auto; display: block; }
.marke .zeile1 {
  font-size: .82rem; font-weight: 600; letter-spacing: .04em;
  color: var(--gold); line-height: 1.3;
}
.marke .zeile2 {
  font-size: .78rem; color: rgba(247,245,240,.55); line-height: 1.3;
}
.kopf h1 {
  margin: 0; font-size: clamp(2.1rem, 11vw, 3.2rem); font-weight: 300;
  line-height: 1.04; letter-spacing: -.015em;
}
.kopf .saison {
  margin: 14px 0 0; font-size: .92rem; color: rgba(247,245,240,.62);
}

/* ---------- Abschnitte ---------- */
.teil { padding: 40px 0 0; }
.rubrik {
  border-top: 1px solid var(--linie); padding-top: 14px; margin-bottom: 26px;
  font-size: .95rem; font-weight: 600; letter-spacing: .02em; color: var(--leise);
}

/* ---------- Nächstes Spiel ---------- */
.marker { font-size: .82rem; font-weight: 600; color: var(--gold-tief);
          letter-spacing: .04em; margin-bottom: 10px; }
.paarung {
  font-size: clamp(1.5rem, 7vw, 2rem); font-weight: 400; line-height: 1.16;
  overflow-wrap: anywhere;
  letter-spacing: -.01em; margin: 0 0 22px;
}
.fakten { margin: 0; }
.fakten > div {
  display: flex; gap: 18px; padding: 11px 0;
  border-top: 1px solid var(--linie-zart); font-size: .95rem;
}
.fakten dt { flex: 0 0 78px; color: var(--leise); }
.fakten dd { margin: 0; flex: 1; }
.fakten a { color: inherit; text-decoration: none;
            box-shadow: inset 0 -1px 0 var(--gold); }

/* ---------- Abo-Wege ---------- */
.weg { padding: 26px 0; border-top: 1px solid var(--linie-zart); }
/* :first-of-type zaehlt Elementtypen, nicht Klassen - das erste div
   im Abschnitt ist die Rubrik. Darum ueber den Geschwisterselektor. */
.rubrik + .weg { border-top: 0; padding-top: 0; }
.weg h3 { margin: 0 0 6px; font-size: 1.12rem; font-weight: 600;
          letter-spacing: -.005em; }
.weg p { margin: 0 0 18px; font-size: .95rem; color: var(--tinte-weich); }
.knopf {
  display: block; width: 100%; text-align: center; text-decoration: none;
  font: inherit; font-size: 1rem; font-weight: 600; padding: 16px 20px;
  border: 1px solid var(--gold); background: var(--gold); color: #14140f;
  cursor: pointer; transition: background .15s ease;
}
.knopf:hover { background: var(--gold-tief); border-color: var(--gold-tief); }
.knopf.stumm { background: transparent; color: var(--tinte);
               border-color: var(--tinte); }
.knopf.stumm:hover { background: var(--gold-schwach); border-color: var(--gold); }
.knopf:focus-visible { outline: 2px solid var(--gold-tief); outline-offset: 3px; }
.schritte { margin: 18px 0 0; padding: 0; list-style: none;
            font-size: .92rem; color: var(--tinte-weich);
            counter-reset: schritt; }
.schritte li {
  counter-increment: schritt; position: relative; padding: 8px 0 8px 34px;
  border-top: 1px solid var(--linie-zart);
}
.schritte li::before {
  content: counter(schritt); position: absolute; left: 0; top: 8px;
  font-size: .82rem; font-weight: 600; color: var(--gold-tief);
}
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
       font-size: .88em; color: var(--tinte); }

/* ---------- Änderungen ---------- */
.hinweis { border-left: 2px solid var(--gold); padding: 4px 0 4px 18px;
           margin: 30px 0 0; }
.hinweis h3 { margin: 0 0 8px; font-size: .82rem; font-weight: 600;
              letter-spacing: .04em; color: var(--gold-tief); }
.hinweis ul { margin: 0; padding-left: 18px; font-size: .95rem; }
.hinweis li { margin: 5px 0; }

/* ---------- Spielplan ---------- */
.monat {
  font-size: .82rem; font-weight: 600; letter-spacing: .06em;
  text-transform: uppercase; color: var(--leise);
  padding: 30px 0 10px;
}
.teil > .monat:first-of-type { padding-top: 6px; }
.spiel {
  display: grid; grid-template-columns: 58px 1fr 24px; gap: 0 16px;
  align-items: start; padding: 15px 0; border-top: 1px solid var(--linie);
}
.spiel .datum { font-size: .88rem; font-weight: 600; line-height: 1.3; }
.spiel .datum span { display: block; font-weight: 400; color: var(--leise); }
.spiel .gegner { font-size: 1.02rem; font-weight: 500; line-height: 1.3;
                 /* Vereinsnamen wie 'Zotzenheim/St.Johann/Sprendlingen' haben
                    keine Leerzeichen und wuerden sonst aus der Spalte laufen */
                 overflow-wrap: anywhere; }
.spiel .halle { font-size: .88rem; color: var(--leise); margin-top: 3px; }
.spiel .halle a { text-decoration: none;
                  box-shadow: inset 0 -1px 0 var(--linie); }
.spiel .halle a:hover { box-shadow: inset 0 -1px 0 var(--gold); }
.hz { font-size: .78rem; font-weight: 600; letter-spacing: .02em;
      text-align: right; color: var(--leise); padding-top: 2px; }
.hz.heim { color: var(--gold-tief); }
.spiel.vorbei { opacity: .34; }
.spiel.jetzt { border-top-color: var(--gold); box-shadow: inset 0 2px 0 var(--gold); }

/* ---------- Reiter ---------- */
.reiter {
  position: sticky; top: 0; z-index: 5;
  background: var(--grund); border-bottom: 1px solid var(--linie);
  display: flex; gap: 0; overflow-x: auto; -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.reiter::-webkit-scrollbar { display: none; }
.reiter a {
  flex: 0 0 auto; padding: 15px 18px 13px; font-size: .92rem; font-weight: 500;
  color: var(--leise); text-decoration: none; white-space: nowrap;
  border-bottom: 2px solid transparent; margin-bottom: -1px;
}
.reiter a:first-child { padding-left: 0; }
/* sonst verschwindet die Ueberschrift beim Ankersprung unter der Leiste */
section[id] { scroll-margin-top: 54px; }
.reiter a[aria-current="true"] { color: var(--tinte); border-bottom-color: var(--gold); }

/* ---------- Tabelle ---------- */
.tabellenhuelle { overflow-x: auto; }
table.tabelle { width: 100%; border-collapse: collapse; font-size: .92rem; }
table.tabelle th {
  text-align: right; font-size: .74rem; font-weight: 600; letter-spacing: .06em;
  text-transform: uppercase; color: var(--leise); padding: 0 0 10px;
  border-bottom: 1px solid var(--linie); white-space: nowrap;
}
table.tabelle th.platz { text-align: left; width: 26px; }
table.tabelle th.mann { text-align: left; width: auto; }
table.tabelle td {
  padding: 11px 0; border-bottom: 1px solid var(--linie-zart);
  text-align: right; white-space: nowrap;
}
table.tabelle td.platz { text-align: left; color: var(--leise); font-size: .86rem; }
table.tabelle td.mann {
  text-align: left; white-space: normal; overflow-wrap: anywhere;
  padding-right: 12px; line-height: 1.3;
}
table.tabelle td + td, table.tabelle th + th { padding-left: 12px; }
table.tabelle td.pkt { font-weight: 600; }
table.tabelle tr.wir td { background: var(--gold-schwach); font-weight: 600; }
table.tabelle tr.wir td.platz { box-shadow: inset 2px 0 0 var(--gold); }
.tabellenfuss { margin: 14px 0 0; font-size: .84rem; color: var(--leise); }
.nur-breit { display: none; }
@media (min-width: 560px) { .nur-breit { display: table-cell; } }

/* ---------- Fuß ---------- */
.fuss { margin: 52px 0 0; padding: 20px 0 46px;
        border-top: 1px solid var(--linie); font-size: .88rem;
        color: var(--leise); }
.fuss a { color: var(--leise); }

@media (min-width: 640px) {
  .kopf .huelle { padding: 34px 22px 44px; }
  .marke img { width: 56px; }
  .fakten dt { flex: 0 0 110px; }
  .knopf { display: inline-block; width: auto; min-width: 280px; }
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
    return f"""<div class="marker"><span data-anwurf="{wann.isoformat()}">{relativ}</span> &middot; {'Heimspiel' if heim else 'Auswärtsspiel'}</div>
<h2 class="paarung">{paarung}</h2>
<dl class="fakten">
<div><dt>Anwurf</dt><dd>{WOCHENTAGE[wann.weekday()]}, {wann:%d.%m.%Y}, {wann:%H:%M} Uhr</dd></div>
<div><dt>Halle</dt><dd>{sicher(spiel.get('halle'))}</dd></div>
<div><dt>Adresse</dt><dd><a href="{kartenlink(spiel)}" target="_blank" rel="noopener">{sicher(strasse(spiel))}</a></dd></div>
</dl>"""


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
<div class="hz {'heim' if heim else ''}">{'H' if heim else 'A'}</div>
</div>"""


def tabellenblock(tabelle: dict, eigenes_team: int | None) -> str:
    """Rendert den Tabellenstand. Vor dem ersten Spieltag steht ueberall 0 -
    die Reihenfolge ist dann ohne Aussage, darum der Hinweis darunter."""
    if not tabelle or not tabelle.get("eintraege"):
        return ""

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

    if tabelle.get("gespielt"):
        fuss = f'Stand nach Spieltag {tabelle["runde"]}.'
    else:
        fuss = ("Die Saison hat noch nicht begonnen – alle Mannschaften stehen "
                "bei null, die Reihenfolge hat noch keine Aussagekraft.")

    return f'''<div class="tabellenhuelle">
<table class="tabelle">
<thead><tr>
<th class="platz">Pl</th><th class="mann">Mannschaft</th><th>Sp</th>
<th class="nur-breit">Tore</th><th>Diff</th><th>Pkt</th>
</tr></thead>
<tbody>{"".join(zeilen)}</tbody>
</table>
</div>
<p class="tabellenfuss">{fuss}</p>'''


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

    tabelle_html = tabellenblock(daten.get("tabelle") or {}, daten.get("team_id"))
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
automatisch im Handykalender, Verlegungen inklusive.">
<meta name="theme-color" content="#14140f">
<link rel="icon" href="icon-32.png" sizes="32x32">
<link rel="apple-touch-icon" href="icon-180.png">
<style>{STIL}</style>
</head>
<body>

<header class="kopf">
  <div class="huelle">
    <div class="marke">
      <img src="logo.png" alt="Wappen der HSG Mutterstadt/Ruchheim" width="149" height="200">
      <div>
        <div class="zeile1">HSG Mutterstadt/Ruchheim</div>
        <div class="zeile2">Die Füchse</div>
      </div>
    </div>
    <h1>Herren&nbsp;I<br>Spielplan</h1>
    <p class="saison">{kopfzeile}</p>
  </div>
</header>

<nav class="reiter huelle" aria-label="Abschnitte">
  <a href="#kalender">In den Kalender</a>
  <a href="#spiele">Alle Spiele</a>
  {'<a href="#tabelle">Tabelle</a>' if tabelle_html else ''}
</nav>

<div class="huelle">

  <section class="teil">
    {hero(kommend[0][1], heute) if kommend else '<p>Keine kommenden Spiele.</p>'}
    {hinweis}
  </section>

  <section class="teil" id="kalender">
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
        <li>„Per URL“ wählen, Adresse einfügen, hinzufügen</li>
      </ol>
    </div>

    <div class="weg">
      <h3>Einmalig importieren</h3>
      <p>Ohne Abo. Spätere Verlegungen kommen dann nicht mehr an.</p>
      <a class="knopf stumm" href="{sicher(cfg.ics)}" download>Datei herunterladen</a>
    </div>
  </section>

  <section class="teil" id="spiele">
    <div class="rubrik">Alle Spiele der Saison</div>
    {''.join(tabelle)}
  </section>

  {f'<section class="teil" id="tabelle"><div class="rubrik">Tabelle</div>{tabelle_html}</section>' if tabelle_html else ''}

  <p class="fuss">
    Zuletzt abgeglichen am {stand_text}. Der Spielplan wird täglich automatisch
    mit <a href="https://www.handball.net" target="_blank" rel="noopener">handball.net</a>
    abgeglichen; Änderungen erscheinen hier und in abonnierten Kalendern.
  </p>
</div>

<script>
// Die Angabe "Morgen" wird beim naechtlichen Bauen gesetzt und waere sonst
// veraltet, sobald ein Lauf ausfaellt - darum hier nochmal aus dem echten
// Anwurfzeitpunkt berechnet.
(function () {{
  var el = document.querySelector('[data-anwurf]');
  if (!el) return;
  var anwurf = new Date(el.getAttribute('data-anwurf'));
  if (isNaN(anwurf)) return;
  var heute = new Date(); heute.setHours(0, 0, 0, 0);
  var tag = new Date(anwurf); tag.setHours(0, 0, 0, 0);
  var tage = Math.round((tag - heute) / 86400000);
  el.textContent = tage < 0 ? 'Läuft gerade'
    : tage === 0 ? 'Heute'
    : tage === 1 ? 'Morgen'
    : tage < 7 ? 'In ' + tage + ' Tagen'
    : 'Nächstes Spiel';
}})();

// Reiter markieren, sobald der zugehoerige Abschnitt sichtbar wird
(function () {{
  var reiter = [].slice.call(document.querySelectorAll('.reiter a'));
  if (!reiter.length || !window.IntersectionObserver) return;
  var zuOrdnung = {{}};
  reiter.forEach(function (a) {{
    var ziel = document.querySelector(a.getAttribute('href'));
    if (ziel) zuOrdnung[ziel.id] = a;
  }});
  var beobachter = new IntersectionObserver(function (eintraege) {{
    eintraege.forEach(function (e) {{
      if (!e.isIntersecting) return;
      reiter.forEach(function (a) {{ a.removeAttribute('aria-current'); }});
      if (zuOrdnung[e.target.id]) zuOrdnung[e.target.id].setAttribute('aria-current', 'true');
    }});
  }}, {{ rootMargin: '-20% 0px -70% 0px' }});
  Object.keys(zuOrdnung).forEach(function (id) {{
    beobachter.observe(document.getElementById(id));
  }});
}})();

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
