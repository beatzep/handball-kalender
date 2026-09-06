#!/usr/bin/env python3
"""Erzeugt docs/torjaeger.html - alle Schuetzen der Aktiven an einem Ort.

Bei handball.net muss man jede Mannschaft einzeln aufrufen und bekommt dort
nur die ersten zehn. Hier stehen alle zusammen, ueber die Mannschaften
hinweg zusammengefasst: Wer in Herren I und II spielt, taucht einmal auf,
mit beiden Mannschaften daneben.

Nur die Aktiven. Torschuetzenlisten von Jugendlichen mit vollem Namen auf
einer oeffentlichen Vereinsseite sind etwas anderes, auch wenn handball.net
sie fuehrt.
"""

from __future__ import annotations

import argparse
import html
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from seite_ansicht import ANSICHT
from seite_stil import STIL

TZ = ZoneInfo("Europe/Berlin")
AKTIVE = ("herren1", "herren2", "damen")


def sicher(text) -> str:
    return html.escape(str(text if text is not None else ""))


def komma(wert: float) -> str:
    return f"{wert:.1f}".replace(".", ",")


def sammle(daten: dict, nur: tuple[str, ...]) -> tuple[list[dict], dict]:
    """Alle Schuetzen der genannten Mannschaften, je Spieler zusammengefasst.

    Zusammengefuehrt wird ueber die Spieler-Kennung der Quelle, nicht ueber
    den Namen - zwei Leute koennen gleich heissen, und in dieser Runde ist
    das bereits der Fall.
    """
    spieler: dict[str, dict] = {}
    quelle = {"mannschaften": 0, "mit_bericht": 0, "offen": 0, "ohne_bericht": 0}

    for schluessel in nur:
        team = (daten.get("teams") or {}).get(schluessel)
        if not team:
            continue
        sp = team.get("spieler") or {}
        q = sp.get("quelle") or {}
        if not q.get("spiele_gelaufen"):
            continue
        quelle["mannschaften"] += 1
        for feld in ("mit_bericht", "offen", "ohne_bericht"):
            quelle[feld] += q.get(feld) or 0

        # Je Spiel, damit die persoenliche Bilanz danach aufgebaut werden kann
        for spiel in sp.get("spiele") or []:
            for e in spiel.get("schuetzen") or []:
                eintrag = spieler.setdefault(e["id"], {
                    "id": e["id"], "name": e["name"], "tore": 0,
                    "siebenmeter_tore": 0, "siebenmeter_wuerfe": 0,
                    "spiele": 0, "mannschaften": [], "einsaetze": [],
                })
                if team["name"] not in eintrag["mannschaften"]:
                    eintrag["mannschaften"].append(team["name"])
                eintrag["tore"] += e["tore"]
                eintrag["siebenmeter_tore"] += e["siebenmeter_tore"]
                eintrag["siebenmeter_wuerfe"] += e["siebenmeter_wuerfe"]
                eintrag["spiele"] += 1
                eintrag["einsaetze"].append({
                    "datum": spiel["datum"],
                    "gegner": spiel.get("gegner"),
                    "heim": spiel.get("heim"),
                    "mannschaft": team["kurzname"] or team["name"],
                    "tore": e["tore"],
                    "siebenmeter": [e["siebenmeter_tore"], e["siebenmeter_wuerfe"]],
                })

    liste = list(spieler.values())
    for e in liste:
        e["tore_je_spiel"] = round(e["tore"] / e["spiele"], 1) if e["spiele"] else 0.0
        e["einsaetze"].sort(key=lambda x: x["datum"], reverse=True)
    liste.sort(key=lambda e: (-e["tore"], -e["tore_je_spiel"], e["name"]))
    return liste, quelle


def zeile(platz: int, e: dict) -> str:
    """Eine Zeile der Liste, aufklappbar zur persoenlichen Bilanz."""
    sm = (f'<span class="klein">7m {e["siebenmeter_tore"]}/'
          f'{e["siebenmeter_wuerfe"]}</span>'
          if e["siebenmeter_wuerfe"] else "")
    teams = ", ".join(sicher(m) for m in e["mannschaften"])

    # Die Mannschaft steht nur dabei, wenn jemand in mehreren spielt - sonst
    # wiederholt sie in jeder Zeile, was schon in der Kopfzeile steht.
    mehrere = len(e["mannschaften"]) > 1
    einsaetze = "".join(
        f'<tr><td class="wann">{datetime.fromisoformat(x["datum"]):%d.%m.}</td>'
        f'<td>{"gegen" if x["heim"] else "bei"} {sicher(x["gegner"])}'
        + (f'<span class="klein"> · {sicher(x["mannschaft"])}</span>'
           if mehrere else "")
        + "</td>"
        f'<td class="pkt">{x["tore"]}'
        + (f'<span class="klein"> ({x["siebenmeter"][0]}/{x["siebenmeter"][1]} 7m)</span>'
           if x["siebenmeter"][1] else "")
        + "</td></tr>"
        for x in e["einsaetze"])

    return (
        f'<details class="jaeger" data-tore="{e["tore"]}" '
        f'data-schnitt="{e["tore_je_spiel"]}" data-name="{sicher(e["name"])}">'
        f'<summary>'
        f'<span class="platz">{platz}</span>'
        f'<span class="wer"><span class="name">{sicher(e["name"])}</span>'
        f'<span class="klein">{teams} · '
        f'{e["spiele"]} Spiel{"e" if e["spiele"] != 1 else ""}</span></span>'
        f'<span class="schnitt">{komma(e["tore_je_spiel"])}</span>'
        f'<span class="tore">{e["tore"]}</span>'
        f'</summary>'
        f'<div class="bilanz">{sm}'
        f'<table><tbody>{einsaetze}</tbody></table></div>'
        f'</details>')


def hinweis(quelle: dict, anzahl: int) -> str:
    """Worauf die Liste beruht - und was bei der Quelle noch fehlt."""
    if not anzahl:
        return ('<p class="statfuss">Sobald die ersten Spielberichte bei '
                'handball.net stehen, sammeln sich hier die Torschützen.</p>')
    teile = [f'{anzahl} Schützen aus {quelle["mit_bericht"]} Spielen '
             f'von {quelle["mannschaften"]} Mannschaften.']
    if quelle["offen"] == 1:
        teile.append("Für ein weiteres Spiel hat handball.net den Spielbericht "
                     "noch nicht veröffentlicht.")
    elif quelle["offen"] > 1:
        teile.append(f'Für {quelle["offen"]} weitere Spiele hat handball.net '
                     f'die Spielberichte noch nicht veröffentlicht.')
    if quelle["ohne_bericht"]:
        teile.append("Zu einzelnen Spielen wird kein Bericht geführt.")
    return f'<p class="statfuss">{" ".join(teile)}</p>'


def main() -> None:
    p = argparse.ArgumentParser(description="Torjaegerliste bauen")
    p.add_argument("--daten", default="docs/daten.json")
    p.add_argument("--out", default="docs/torjaeger.html")
    p.add_argument("--nur", default=",".join(AKTIVE),
                   help="Mannschaften, durch Komma getrennt")
    cfg = p.parse_args()

    daten = json.loads(Path(cfg.daten).read_bytes().decode("utf-8"))
    nur = tuple(x.strip() for x in cfg.nur.split(",") if x.strip())
    schuetzen, quelle = sammle(daten, nur)
    jetzt = datetime.now(TZ)

    zeilen = "".join(zeile(i, e) for i, e in enumerate(schuetzen, 1))
    inhalt = zeilen or ""
    tore_gesamt = sum(e["tore"] for e in schuetzen)

    seite = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Torjäger HSG Mutterstadt/Ruchheim</title>
<meta name="description" content="Alle Torschützen der Aktiven der HSG
      Mutterstadt/Ruchheim in einer Liste.">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta name="theme-color" content="#14140f">
<style>{STIL}
/* Wie auf der Wochenend-Uebersicht: die Filterknoepfe stehen dort im
   eigenen Stil der Seite, nicht im gemeinsamen. */
.filter {{ display: flex; margin: 30px 0 6px; }}
.filter button {{ font: inherit; font-size: .88rem; font-weight: 600;
  cursor: pointer; background: transparent; color: var(--leise);
  border: 1px solid var(--linie); padding: 10px 16px; margin-right: -1px; }}
.filter button[aria-pressed="true"] {{ color: var(--tinte);
  border-color: var(--tinte); position: relative; z-index: 1; }}
.jaeger {{ border-top: 1px solid var(--linie-zart); }}
.jaeger > summary {{ display: grid;
  grid-template-columns: 26px 1fr 46px 40px; gap: 0 10px; align-items: baseline;
  padding: 13px 0; cursor: pointer; list-style: none; }}
.jaeger > summary::-webkit-details-marker {{ display: none; }}
.jaeger > summary:focus-visible {{ outline: 2px solid var(--gold);
  outline-offset: 2px; }}
.jaeger .platz {{ color: var(--leise); font-size: .86rem;
  font-variant-numeric: tabular-nums; }}
.jaeger .wer {{ min-width: 0; }}
.jaeger .name {{ display: block; font-size: 1.02rem; font-weight: 500; }}
.jaeger .wer .klein {{ display: block; margin-top: 2px; }}
.jaeger .klein {{ font-size: .8rem; color: var(--leise); }}
.jaeger .schnitt {{ text-align: right; color: var(--tinte-weich);
  font-variant-numeric: tabular-nums; }}
.jaeger .tore {{ text-align: right; font-weight: 600; font-size: 1.05rem;
  font-variant-numeric: tabular-nums; }}
.jaeger:first-of-type .tore {{ color: var(--gold-tief); }}
.jaeger .bilanz {{ padding: 0 0 16px 36px; }}
.jaeger .bilanz table {{ width: 100%; border-collapse: collapse;
  font-size: .88rem; margin-top: 6px; }}
.jaeger .bilanz td {{ padding: 7px 0; border-bottom: 1px solid var(--linie-zart);
  color: var(--tinte-weich); }}
.jaeger .bilanz td.wann {{ width: 58px; color: var(--leise);
  font-variant-numeric: tabular-nums; }}
.jaeger .bilanz td.pkt {{ text-align: right; width: 76px; font-weight: 600;
  color: var(--tinte); }}
.kopfzeile {{ display: grid; grid-template-columns: 26px 1fr 46px 40px;
  gap: 0 10px; font-size: .72rem; font-weight: 600; letter-spacing: .05em;
  text-transform: uppercase; color: var(--leise); padding-bottom: 9px;
  border-bottom: 1px solid var(--linie); }}
.kopfzeile .r {{ text-align: right; }}
</style>
</head>
<body>
<header class="kopf">
  <div class="huelle">
    <button id="ansicht" type="button" aria-label="Ansicht wechseln">
      <svg class="mond" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="1.6" aria-hidden="true">
        <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>
      </svg>
      <svg class="sonne" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="1.6" aria-hidden="true">
        <circle cx="12" cy="12" r="4"/>
        <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>
      </svg>
    </button>
    <div class="marke">
      <img src="logo.png" alt="Wappen der HSG Mutterstadt/Ruchheim" width="149" height="200">
      <div>
        <div class="zeile1">HSG Mutterstadt/Ruchheim</div>
        <div class="zeile2">Aktive</div>
      </div>
    </div>
    <h1>Wer<br>trifft</h1>
    <p class="saison">{len(schuetzen)} Schützen, {tore_gesamt} Tore in dieser Saison</p>
    <p class="uebersichtlink"><a href="./">Zum Spielplan einer Mannschaft &rsaquo;</a></p>
  </div>
</header>

<main class="huelle">
  <div class="filter" role="group" aria-label="Sortierung">
    <button type="button" data-sortier="tore" aria-pressed="true">Nach Toren</button>
    <button type="button" data-sortier="schnitt" aria-pressed="false">Pro Spiel</button>
  </div>

  <div class="kopfzeile"><span>Pl</span><span>Spieler</span>
    <span class="r">/Sp</span><span class="r">Tore</span></div>
  <div id="liste">{inhalt}</div>
  {hinweis(quelle, len(schuetzen))}

  <p class="fuss">
    Stand: {jetzt:%d.%m.%Y, %H:%M} Uhr. Aus den Spielberichten von
    <a href="https://www.handball.net" target="_blank" rel="noopener">handball.net</a>.
    <a href="wochenende.html">Wer spielt wann</a>
  </p>
</main>

<script>{ANSICHT}
(function () {{
  var liste = document.getElementById('liste');
  var knoepfe = [].slice.call(document.querySelectorAll('[data-sortier]'));
  if (!liste || !knoepfe.length) return;

  function sortiere(art) {{
    var zeilen = [].slice.call(liste.querySelectorAll('.jaeger'));
    zeilen.sort(function (a, b) {{
      var wa = parseFloat(a.getAttribute('data-' + art));
      var wb = parseFloat(b.getAttribute('data-' + art));
      if (wb !== wa) return wb - wa;
      return a.getAttribute('data-name').localeCompare(b.getAttribute('data-name'));
    }});
    zeilen.forEach(function (z, i) {{
      z.querySelector('.platz').textContent = i + 1;
      liste.appendChild(z);
    }});
    knoepfe.forEach(function (k) {{
      k.setAttribute('aria-pressed',
        k.getAttribute('data-sortier') === art ? 'true' : 'false');
    }});
  }}

  knoepfe.forEach(function (k) {{
    k.addEventListener('click', function () {{
      sortiere(k.getAttribute('data-sortier'));
    }});
  }});
}})();
</script>
</body>
</html>
"""
    ziel = Path(cfg.out)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_bytes(seite.encode("utf-8"))
    print(f"Torjägerliste geschrieben: {ziel} ({len(schuetzen)} Schützen, "
          f"{tore_gesamt} Tore)")


if __name__ == "__main__":
    main()
