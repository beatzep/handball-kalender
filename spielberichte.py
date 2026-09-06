#!/usr/bin/env python3
"""Spielberichte von handball.net holen und dauerhaft aufbewahren.

Zu jedem Spiel gibt es unter `/matches/<id>/events` den Verlauf: jedes Tor
mit Minute, Schuetze und Zwischenstand, dazu Siebenmeter, Zeitstrafen und
Auszeiten. Daraus entsteht alles, was der Statistik-Reiter an Einzelzahlen
zeigt - handball.net selbst macht daraus nur drei Spalten.

Ein Bericht aendert sich nach dem Spiel nicht mehr. Er wird darum genau
einmal geholt und in `berichte_cache.json` abgelegt; spaetere Laeufe
ruehren ihn nicht mehr an. Das haelt die Last bei der Quelle bei rund zwei
Abfragen je Spieltag.

Nicht jede Liga fuehrt einen elektronischen Spielbericht: bei der mB- und
der gD-Jugend kommt eine leere Antwort zurueck. Das wird als "liegt nicht
vor" vermerkt, damit es nicht bei jedem Lauf erneut versucht wird - und
damit die Seite es sauber benennen kann, statt eine Luecke zu zeigen.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://www.handball.net/api/new"

# Die Quelle antwortet ohne Referer mit 403.
KOPF = {
    "referer": "https://www.handball.net/",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "accept": "application/json",
}

# Kurze Pause zwischen den Abfragen. Es sind wenige je Lauf, aber die
# Ruecksicht auf die Quelle gilt hier wie ueberall im Projekt.
PAUSE_SEKUNDEN = 0.5


def lade_cache(pfad: Path) -> dict:
    try:
        return json.loads(pfad.read_bytes().decode("utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def speichere_cache(pfad: Path, cache: dict) -> None:
    pfad.write_bytes(
        (json.dumps(cache, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
        .encode("utf-8"))


def hole_bericht(match_id: str | int) -> list | None:
    """Den Verlauf eines Spiels holen.

    Zurueck kommt die Ereignisliste, oder None wenn die Abfrage scheitert.
    Eine leere Liste ist etwas anderes als None: sie heisst, dass die Liga
    keinen elektronischen Bericht fuehrt.
    """
    url = f"{API}/matches/{match_id}/events"
    req = urllib.request.Request(url, headers=KOPF)
    try:
        with urllib.request.urlopen(req, timeout=30) as antwort:
            daten = json.load(antwort)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
            json.JSONDecodeError) as fehler:
        print(f"Spielbericht {match_id} nicht abrufbar: {fehler}", file=sys.stderr)
        return None
    roh = daten.get("data", daten)
    return roh if isinstance(roh, list) else []


def knapp(ereignis: dict) -> dict:
    """Nur behalten, was fuer die Auswertung gebraucht wird.

    Die Antwort der Quelle traegt Bildadressen, Vereinsanschriften und
    Zeitstempel mit sich. Das aufzubewahren waere unnoetiger Ballast - und
    Spielerfotos will hier ohnehin niemand veroeffentlichen.
    """
    art = ereignis.get("event_type") or {}
    spieler = ereignis.get("player") or {}
    mannschaft = ereignis.get("team") or {}
    stand = ereignis.get("score") or {}
    eintrag = {
        "minute": ereignis.get("minute"),
        "spielminute": ereignis.get("global_minute"),
        "abschnitt": (ereignis.get("block") or "").strip(),
        "art": art.get("name"),
        "art_id": art.get("id"),
        "ist_tor": bool(art.get("is_goal")),
        "ist_strafe": bool(art.get("is_sanction")),
        "team_id": mannschaft.get("id"),
        "heim": bool(ereignis.get("is_home")),
    }
    if spieler:
        eintrag["spieler"] = {
            "id": spieler.get("id"),
            "vorname": (spieler.get("first_name") or "").strip(),
            "nachname": (spieler.get("last_name") or "").strip(),
        }
    if stand:
        eintrag["stand"] = [stand.get("local"), stand.get("visitor")]
    return eintrag


def aktualisiere(cache: dict, spiele: list[dict], pfad: Path | None = None,
                 hoechstens: int = 40) -> dict:
    """Fehlende Berichte nachholen.

    `spiele` sind die Spiele, fuer die ein Bericht in Frage kommt - also
    gelaufene. Was schon im Cache steht, wird uebersprungen; ein Bericht
    aendert sich nicht mehr.

    `hoechstens` begrenzt, wie viele Berichte ein einzelner Lauf holt. Beim
    ersten Mal koennen es viele sein; die Grenze verhindert, dass ein Lauf
    minutenlang an der Quelle haengt.
    """
    geholt = leer = 0
    for spiel in spiele:
        mid = spiel.get("match_id")
        if not mid:
            continue
        key = str(mid)
        if key in cache:
            continue
        if geholt + leer >= hoechstens:
            print(f"Grenze von {hoechstens} Berichten erreicht - der Rest "
                  f"folgt beim naechsten Lauf.", file=sys.stderr)
            break
        ereignisse = hole_bericht(mid)
        if ereignisse is None:
            continue                      # Fehlschlag: beim naechsten Mal erneut
        if ereignisse:
            cache[key] = {"ereignisse": [knapp(e) for e in ereignisse]}
            geholt += 1
        else:
            # Die Liga fuehrt keinen Bericht. Vermerken, damit es nicht bei
            # jedem Lauf erneut versucht wird.
            cache[key] = {"ereignisse": [], "ohne_bericht": True}
            leer += 1
        time.sleep(PAUSE_SEKUNDEN)
        if pfad is not None and (geholt + leer) % 10 == 0:
            speichere_cache(pfad, cache)   # Zwischenstand sichern

    if pfad is not None and (geholt or leer):
        speichere_cache(pfad, cache)
    if geholt or leer:
        print(f"Spielberichte: {geholt} geholt, {leer} ohne Bericht bei der Quelle")
    return cache


def naechster_gegner(spiele: dict, jetzt=None) -> int | None:
    """Die Kennung der Mannschaft, gegen die als Naechstes gespielt wird."""
    from datetime import datetime
    jetzt = jetzt or datetime.now()
    kommend = sorted(
        (s for s in spiele.values()
         if not s.get("ergebnis") and s.get("gegner_id")
         and datetime.fromisoformat(s["datum"]) >= jetzt),
        key=lambda s: s["datum"])
    return kommend[0]["gegner_id"] if kommend else None


def gegnerspiele(team_id: int, hole=None) -> list[dict]:
    """Die gelaufenen Spiele einer fremden Mannschaft.

    Dieselbe Abfrage wie fuer die eigenen, nur mit fremder Kennung. Der
    Umweg ueber spielplan2ics waere hier zu viel: gebraucht werden nur
    match_id und Datum.
    """
    import spielplan2ics
    hole = hole or spielplan2ics.hole_spiele
    fertig = []
    for spiel in hole(team_id):
        status = spiel.get("status") or {}
        if not status.get("is_finished"):
            continue
        r = spiel.get("result") or {}
        if r.get("local") == 0 and r.get("visitor") == 0:
            continue          # keine Wertung, siehe spielplan2ics.ergebnis
        fertig.append({
            "match_id": spiel.get("id"),
            "datum": str(spiel.get("date") or "")[:19],
        })
    return fertig


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="Spielberichte holen und aufbewahren")
    p.add_argument("--daten", default="docs/daten.json")
    p.add_argument("--cache", default="berichte_cache.json")
    p.add_argument("--teams", default="teams.json")
    p.add_argument("--hoechstens", type=int, default=40,
                   help="wie viele Berichte dieser Lauf hoechstens holt")
    p.add_argument("--nur", default="",
                   help="Mannschaften, durch Komma getrennt; leer = alle mit Kader")
    p.add_argument("--gegner", action="store_true",
                   help="auch die Spiele des jeweils naechsten Gegners holen")
    cfg = p.parse_args()

    daten = json.loads(Path(cfg.daten).read_bytes().decode("utf-8"))
    pfad = Path(cfg.cache)
    cache = lade_cache(pfad)

    gewuenscht = [x.strip() for x in cfg.nur.split(",") if x.strip()]
    spiele = []
    for schluessel, team in (daten.get("teams") or {}).items():
        if gewuenscht and schluessel not in gewuenscht:
            continue
        for spiel in (team.get("spiele") or {}).values():
            if spiel.get("ergebnis"):
                spiele.append(spiel)

    # Fuer die Vorschau: die bisherigen Spiele des naechsten Gegners. Das
    # kostet je Mannschaft eine Spielplanabfrage plus die neuen Berichte -
    # deshalb nur auf Wunsch und nur fuer den einen kommenden Gegner.
    if cfg.gegner:
        import time as _zeit
        for schluessel, team in (daten.get("teams") or {}).items():
            if gewuenscht and schluessel not in gewuenscht:
                continue
            gid = naechster_gegner(team.get("spiele") or {})
            if not gid:
                continue
            try:
                weitere = gegnerspiele(gid)
            except Exception as fehler:      # eine Vorschau ist kein Grund
                print(f"Gegnerspiele zu {gid} nicht abrufbar: {fehler}",
                      file=sys.stderr)       # den ganzen Lauf abzubrechen
                continue
            neu = [s for s in weitere if str(s["match_id"]) not in cache]
            if neu:
                print(f"  {team.get('name', schluessel)}: naechster Gegner "
                      f"{gid}, {len(neu)} Berichte fehlen noch")
            spiele.extend(weitere)
            _zeit.sleep(PAUSE_SEKUNDEN)

    vorher = len(cache)
    aktualisiere(cache, spiele, pfad, cfg.hoechstens)
    print(f"{len(cache)} Berichte im Bestand ({len(cache) - vorher} neu), "
          f"{len(spiele)} gelaufene Spiele betrachtet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
