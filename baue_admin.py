#!/usr/bin/env python3
"""Erzeugt docs/admin.html - die Auswertung der Nutzung.

Die Seite selbst ist oeffentlich und leer; die Zahlen liefert der Worker nur
gegen Anmeldung. Der Code darf also im offenen Verzeichnis liegen.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from seite_stil import STIL

SKRIPT = """
(function () {
  var worker = document.body.getAttribute('data-worker');
  var form = document.getElementById('anmeldung');
  var feldBenutzer = document.getElementById('benutzer');
  var feldPasswort = document.getElementById('passwort');
  var meldung = document.getElementById('meldung');
  var bereich = document.getElementById('auswertung');
  var abmelden = document.getElementById('abmelden');

  function zahl(n) { return (n || 0).toLocaleString('de-DE'); }

  function kennzahl(titel, wert, zusatz) {
    return '<div><dt>' + titel + '</dt><dd>' + wert +
      (zusatz ? '<span class="zusatz">' + zusatz + '</span>' : '') + '</dd></div>';
  }

  /** Balken je Tag - eine Kurve taeuscht bei laengeren Luecken Verlauf vor. */
  function verlaufsbild(tage) {
    if (!tage.length) return '';
    var hoechst = Math.max.apply(null, tage.map(function (t) { return t.aufrufe; })) || 1;
    var B = 320, H = 110, unten = 22, links = 26;
    var breite = (B - links) / tage.length;
    var balken = tage.map(function (t, i) {
      var h = Math.round((H - unten - 8) * t.aufrufe / hoechst);
      return '<rect x="' + (links + i * breite + 1).toFixed(1) + '" y="' +
        (H - unten - h) + '" width="' + Math.max(breite - 2, 1).toFixed(1) +
        '" height="' + Math.max(h, t.aufrufe ? 1 : 0) + '" class="balken"><title>' +
        t.tag + ': ' + t.aufrufe + '</title></rect>';
    }).join('');
    var erster = tage[0].tag.slice(8) + '.' + tage[0].tag.slice(5, 7) + '.';
    var letzter = tage[tage.length - 1].tag.slice(8) + '.' +
                  tage[tage.length - 1].tag.slice(5, 7) + '.';
    return '<div class="verlauf"><div class="titel">Aufrufe je Tag</div>' +
      '<svg viewBox="0 0 ' + B + ' ' + H + '" role="img" aria-label="Aufrufe je Tag">' +
      '<line class="gitter" x1="' + links + '" y1="' + (H - unten) + '" x2="' + B +
      '" y2="' + (H - unten) + '"/>' +
      '<text x="0" y="14">' + hoechst + '</text>' +
      '<text x="0" y="' + (H - unten + 4) + '">0</text>' + balken +
      '<text x="' + links + '" y="' + (H - 4) + '">' + erster + '</text>' +
      '<text x="' + B + '" y="' + (H - 4) + '" text-anchor="end">' + letzter + '</text>' +
      '</svg></div>';
  }

  function aufschluesselung(titel, werte, namen) {
    var eintraege = Object.keys(werte || {});
    if (!eintraege.length) return '';
    var summe = eintraege.reduce(function (s, k) { return s + werte[k]; }, 0) || 1;
    var zeilen = eintraege.sort(function (a, b) { return werte[b] - werte[a]; })
      .map(function (k) {
        var anteil = Math.round(100 * werte[k] / summe);
        return '<tr><td>' + (namen[k] || k) + '</td><td class="anteil">' +
          '<span style="width:' + anteil + '%"></span></td>' +
          '<td class="pkt">' + zahl(werte[k]) + '</td></tr>';
      }).join('');
    return '<div class="rubrik">' + titel + '</div><table class="verteilung"><tbody>' +
      zeilen + '</tbody></table>';
  }

  function zeige(d) {
    var e = d.gesamt.ereignis || {};
    var heute = d.verlauf.length ? d.verlauf[d.verlauf.length - 1].aufrufe : 0;
    var woche = d.verlauf.slice(-7).reduce(function (s, t) { return s + t.aufrufe; }, 0);

    bereich.innerHTML =
      '<dl class="kennzahlen">' +
        kennzahl('Aufrufe heute', zahl(heute)) +
        kennzahl('Letzte 7 Tage', zahl(woche)) +
        kennzahl('Kalender abonniert', zahl(e.abo), 'Klicks auf den Abo-Knopf') +
        kennzahl('Tipper', zahl(d.tipper), 'mit Namen eingetragen') +
      '</dl>' +
      verlaufsbild(d.verlauf) +
      aufschluesselung('Nach Mannschaft', d.gesamt.mannschaft,
        { herren1: 'Herren I', herren2: 'Herren II', damen: 'Damen' }) +
      aufschluesselung('Nach Bereich', d.gesamt.bereich,
        { kalender: 'Kalender', spiele: 'Spiele', tabelle: 'Tabelle',
          statistik: 'Statistik' }) +
      aufschluesselung('Aktionen', {
        abo: e.abo || 0, datei: e.datei || 0, grafik: e.grafik || 0,
        tipp: e.tipp || 0, hype: e.hype || 0, dabei: e.dabei || 0,
        teilen: e.teilen || 0 },
        { abo: 'Kalender abonniert', datei: 'Datei geladen', grafik: 'Bild erzeugt',
          tipp: 'Tipp abgegeben', hype: 'Angefeuert', dabei: 'Zusage',
          teilen: 'Geteilt oder kopiert' }) +
      '<p class="statfuss">Gezählt werden Summen je Tag – ohne Kennung, ohne ' +
      'Adresse, ohne Wiedererkennung. Ein Besuch meldet sich einmal beim Öffnen ' +
      'und einmal beim Verlassen.</p>';
    bereich.hidden = false;
    form.hidden = true;
    abmelden.hidden = false;
  }

  function hole(benutzer, passwort) {
    meldung.textContent = 'Wird geladen …';
    meldung.className = 'meldung';
    fetch(worker + '/auswertung', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ benutzer: benutzer, passwort: passwort, tage: 30 })
    })
      .then(function (r) {
        return r.json().then(function (d) {
          return r.ok ? d : Promise.reject(d.fehler || 'Fehler ' + r.status);
        });
      })
      .then(function (d) {
        meldung.textContent = '';
        try {
          sessionStorage.setItem('muru-admin', JSON.stringify([benutzer, passwort]));
        } catch (e) {}
        zeige(d);
      })
      .catch(function (f) {
        meldung.textContent = String(f);
        meldung.className = 'meldung schlecht';
      });
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    hole(feldBenutzer.value.trim(), feldPasswort.value);
  });

  abmelden.addEventListener('click', function () {
    try { sessionStorage.removeItem('muru-admin'); } catch (e) {}
    location.reload();
  });

  // Innerhalb einer Sitzung nicht jedes Mal neu anmelden
  try {
    var gemerkt = JSON.parse(sessionStorage.getItem('muru-admin') || 'null');
    if (gemerkt) hole(gemerkt[0], gemerkt[1]);
  } catch (e) {}
})();
"""

ZUSATZSTIL = """
.anmeldung { max-width: 380px; }
.anmeldung label { display: block; font-size: .82rem; color: var(--leise);
                   margin: 0 0 6px; }
.anmeldung input { font: inherit; width: 100%; padding: 13px 14px; margin-bottom: 16px;
                   background: transparent; color: var(--tinte);
                   border: 1px solid var(--linie); }
.anmeldung input:focus-visible { outline: 2px solid var(--gold-tief); outline-offset: 1px; }
.verlauf { margin-top: 30px; }
.verlauf .balken { fill: var(--gold); }
table.verteilung { width: 100%; border-collapse: collapse; font-size: .92rem;
                   margin-bottom: 8px; }
table.verteilung td { padding: 10px 0; border-bottom: 1px solid var(--linie-zart); }
table.verteilung td.anteil { width: 45%; padding: 10px 14px; }
table.verteilung td.anteil span { display: block; height: 8px; background: var(--gold);
                                  min-width: 1px; }
table.verteilung td.pkt { text-align: right; font-weight: 600; white-space: nowrap; }
.meldung { font-size: .9rem; color: var(--tinte-weich); }
.meldung.schlecht { color: var(--niederlage); }
#abmelden { font: inherit; font-size: .84rem; background: none; border: 0; padding: 0;
            color: var(--leise); text-decoration: underline; cursor: pointer;
            margin-top: 30px; }
"""


def main() -> None:
    p = argparse.ArgumentParser(description="Auswertungsseite bauen")
    p.add_argument("--worker-url", required=True)
    p.add_argument("--out", default="docs/admin.html")
    cfg = p.parse_args()

    seite = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Auswertung – HSG MuRu Spielplan</title>
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#14140f">
<link rel="icon" href="icon-32.png" sizes="32x32">
<style>{STIL}{ZUSATZSTIL}</style>
</head>
<body data-worker="{cfg.worker_url}">

<header class="kopf">
  <div class="huelle">
    <div class="marke">
      <img src="logo.png" alt="" width="149" height="200">
      <div>
        <div class="zeile1">HSG Mutterstadt/Ruchheim</div>
        <div class="zeile2">Auswertung</div>
      </div>
    </div>
    <h1>Nutzung</h1>
    <p class="saison">Letzte 30 Tage</p>
  </div>
</header>

<main class="huelle">
  <form id="anmeldung" class="anmeldung teil">
    <label for="benutzer">Benutzer</label>
    <input id="benutzer" type="email" autocomplete="username" required>
    <label for="passwort">Passwort</label>
    <input id="passwort" type="password" autocomplete="current-password" required>
    <button class="knopf" type="submit">Anmelden</button>
    <p id="meldung" class="meldung"></p>
  </form>

  <section id="auswertung" class="teil" hidden></section>
  <button id="abmelden" type="button" hidden>Abmelden</button>

  <p class="fuss">
    Die Zahlen gibt es nur nach Anmeldung.
    <a href="./">Zurück zum Spielplan</a>
  </p>
</main>

<script>{SKRIPT}</script>
</body>
</html>
"""
    ziel = Path(cfg.out)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(seite, encoding="utf-8")
    print(f"Auswertungsseite geschrieben: {ziel}")


if __name__ == "__main__":
    main()
