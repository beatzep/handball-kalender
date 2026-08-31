#!/usr/bin/env python3
"""Echte Strassenkilometer ueber die OpenRouteService-API.

statistik.py schaetzt Entfernungen per Luftlinie mal Umwegfaktor - das
reicht ohne Netzwerkzugriff, weicht aber je nach Strecke spuerbar vom
tatsaechlichen Weg ab. Hier wird pro Halle einmalig die echte Route
abgefragt und das Ergebnis dauerhaft in einer Cache-Datei gehalten: die
Koordinaten einer Halle aendern sich waehrend einer Saison nicht, und das
kostenlose ORS-Kontingent ist begrenzt (2000 Anfragen/Tag, 40/Minute).
Ohne Schluessel oder bei einem Fehlschlag bleibt eine Halle einfach im
Cache unbesetzt - statistik.py faellt dann automatisch auf die
Luftlinien-Schaetzung zurueck.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ORS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"
# Kostenloses Kontingent: 40 Anfragen/Minute. Etwas Luft nach unten, damit
# ein paralleler Lauf (z.B. lokal waehrend CI laeuft) nicht ueber das Limit
# stolpert.
PAUSE_SEKUNDEN = 1.6


def schluessel(lat: float, lon: float) -> str:
    return f"{lat:.5f},{lon:.5f}"


def lade_cache(pfad: Path) -> dict[str, float]:
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def speichere_cache(pfad: Path, cache: dict[str, float]) -> None:
    pfad.write_text(
        json.dumps(cache, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8")


def _route_km(api_key: str, start: tuple[float, float],
               ziel: tuple[float, float]) -> float | None:
    """Eine einzelne Fahrstrecke bei ORS abfragen (Lon/Lat-Reihenfolge, wie
    von der API verlangt - nicht Lat/Lon wie sonst im Projekt ueblich)."""
    url = (f"{ORS_URL}?api_key={api_key}"
           f"&start={start[1]},{start[0]}&end={ziel[1]},{ziel[0]}")
    # ORS lehnt einen schlichten "application/json"-Accept-Header mit 406 ab -
    # dieser Wert ist der aus der offiziellen Doku.
    req = urllib.request.Request(url, headers={
        "accept": "application/json, application/geo+json, "
                  "application/gpx+xml, img/png; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=20) as antwort:
            daten = json.load(antwort)
        meter = daten["features"][0]["properties"]["summary"]["distance"]
        return meter / 1000
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
            KeyError, IndexError, json.JSONDecodeError) as fehler:
        print(f"ORS-Abfrage fehlgeschlagen ({start} -> {ziel}): {fehler}",
              file=sys.stderr)
        return None


def aktualisiere(cache: dict[str, float], heimat: dict,
                  ziele: set[tuple[float, float]],
                  api_key: str | None, cache_pfad: Path | None = None) -> dict[str, float]:
    """Ergaenzt den Cache um alle noch fehlenden Hallen. Veraendert und
    liefert den uebergebenen Cache zurueck.

    Wird cache_pfad mitgegeben, landet jede einzelne Route sofort auf der
    Platte statt erst am Ende des Teams oder Laufs - sonst sind bei einem
    Abbruch mittendrin bereits verbrauchte Anfragen fuer die Katz."""
    if not api_key:
        return cache
    try:
        start = (float(heimat["lat"]), float(heimat["lon"]))
    except (TypeError, ValueError, KeyError):
        return cache

    fehlend = [z for z in ziele if schluessel(*z) not in cache]
    if not fehlend:
        return cache
    print(f"  hole {len(fehlend)} Route(n) bei OpenRouteService ...")
    for i, ziel in enumerate(fehlend):
        km = _route_km(api_key, start, ziel)
        if km is not None:
            cache[schluessel(*ziel)] = round(km, 1)
            print(f"    [{i + 1}/{len(fehlend)}] {km:.1f} km")
            if cache_pfad is not None:
                speichere_cache(cache_pfad, cache)
        if i < len(fehlend) - 1:
            time.sleep(PAUSE_SEKUNDEN)
    return cache
