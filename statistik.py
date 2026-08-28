#!/usr/bin/env python3
"""Kennzahlen einer Saison, die handball.net so nicht ausweist.

Alles wird aus den bereits vorhandenen Spieldaten abgeleitet - Ergebnisse,
Anwurfzeiten und den Koordinaten der Hallen. Nichts davon braucht eine
zusaetzliche Abfrage.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from math import asin, cos, radians, sin, sqrt

# Luftlinie mal Umwegfaktor - Strassen fahren keine Geraden. 1,3 ist der
# gaengige Naeherungswert fuer Mittelstrecken in Deutschland.
UMWEGFAKTOR = 1.3
SCHNITT_KMH = 70.0
GLAS_LITER = 0.5


def luftlinie(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Entfernung zweier Punkte in Kilometern (Haversine)."""
    r = 6371.0
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = (sin(dlat / 2) ** 2
         + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2)
    return 2 * r * asin(sqrt(a))


def entfernung(spiel: dict, heimat: dict) -> float | None:
    """Einfache Strecke von der Heimat zur Halle, auf Strasse geschaetzt."""
    try:
        km = luftlinie(float(heimat["lat"]), float(heimat["lon"]),
                       float(spiel["lat"]), float(spiel["lon"]))
    except (TypeError, ValueError, KeyError):
        return None
    return km * UMWEGFAKTOR


def _gespielt(spiele: list[dict]) -> list[dict]:
    return [s for s in spiele if s.get("ergebnis")]


def fahrten(spiele: list[dict], heimat: dict) -> dict:
    """Alle Fahrten der Saison - Heimspiele in fremder Halle zaehlen mit,
    denn dorthin faehrt man genauso."""
    strecken, ohne_punkt = [], []
    for s in spiele:
        km = entfernung(s, heimat)
        if km is None:
            # Ohne Koordinaten laesst sich die Strecke nicht schaetzen. Das
            # wird ausgewiesen, damit die Gesamtzahl nicht zu klein aussieht,
            # ohne dass jemand weiss warum.
            ohne_punkt.append(s.get("halle"))
            continue
        strecken.append({"km": km * 2, "gegner": s.get("gegner"),
                         "halle": s.get("halle"), "heim": s.get("heim")})

    auswaerts = [x for x in strecken if x["km"] > 6]   # alles in Mutterstadt faellt raus
    gesamt = sum(x["km"] for x in strecken)
    return {
        "gesamt_km": round(gesamt),
        "fahrten": len(auswaerts),
        "stunden": round(gesamt / SCHNITT_KMH, 1),
        "weiteste": max(auswaerts, key=lambda x: x["km"], default=None),
        "naechste": min(auswaerts, key=lambda x: x["km"], default=None),
        "ohne_koordinaten": sorted(set(h for h in ohne_punkt if h)),
    }


def bilanz(spiele: list[dict]) -> dict:
    """Siege, Unentschieden, Niederlagen - gesamt und nach Heim/Auswaerts."""
    def zaehle(auswahl):
        c = Counter(s["ergebnis"]["ausgang"] for s in auswahl)
        return {"s": c["S"], "u": c["U"], "n": c["N"], "spiele": len(auswahl)}

    fertig = _gespielt(spiele)
    return {
        "gesamt": zaehle(fertig),
        "heim": zaehle([s for s in fertig if s.get("heim")]),
        "auswaerts": zaehle([s for s in fertig if not s.get("heim")]),
    }


def serien(spiele: list[dict]) -> dict:
    """Laengste Serie ohne Niederlage und die aktuelle Serie."""
    fertig = sorted(_gespielt(spiele), key=lambda s: s["datum"])
    ausgaenge = [s["ergebnis"]["ausgang"] for s in fertig]

    laengste = lauf = 0
    for a in ausgaenge:
        lauf = lauf + 1 if a in ("S", "U") else 0
        laengste = max(laengste, lauf)

    aktuell, art = 0, None
    for a in reversed(ausgaenge):
        if art is None:
            art = a
        if a != art:
            break
        aktuell += 1

    return {"ohne_niederlage": laengste, "aktuell": aktuell, "aktuell_art": art}


def krimis(spiele: list[dict]) -> dict:
    """Spiele mit hoechstens zwei Toren Unterschied."""
    fertig = _gespielt(spiele)
    if not fertig:
        return {"anzahl": 0, "anteil": 0, "gesamt": 0}
    eng = [s for s in fertig if abs(s["ergebnis"]["eigene"] - s["ergebnis"]["fremde"]) <= 2]
    return {"anzahl": len(eng), "gesamt": len(fertig),
            "anteil": round(100 * len(eng) / len(fertig))}


def tore(spiele: list[dict]) -> dict:
    fertig = _gespielt(spiele)
    if not fertig:
        return {}
    erzielt = sum(s["ergebnis"]["eigene"] for s in fertig)
    kassiert = sum(s["ergebnis"]["fremde"] for s in fertig)
    torreich = max(fertig, key=lambda s: s["ergebnis"]["eigene"] + s["ergebnis"]["fremde"])
    return {
        "erzielt": erzielt, "kassiert": kassiert,
        "schnitt": round(erzielt / len(fertig), 1),
        "torreichstes": {"gegner": torreich["gegner"],
                         "stand": f'{torreich["ergebnis"]["eigene"]}:{torreich["ergebnis"]["fremde"]}',
                         "summe": torreich["ergebnis"]["eigene"] + torreich["ergebnis"]["fremde"]},
    }


def anwurfzeiten(spiele: list[dict]) -> dict:
    """Bilanz bei spaeten Anwuerfen gegen den Rest - Handballer streiten
    gern darueber, ob 20 Uhr am Samstag eine Zumutung ist."""
    fertig = _gespielt(spiele)
    spaet = [s for s in fertig if datetime.fromisoformat(s["datum"]).hour >= 19]
    frueh = [s for s in fertig if datetime.fromisoformat(s["datum"]).hour < 19]

    def punkte(auswahl):
        c = Counter(s["ergebnis"]["ausgang"] for s in auswahl)
        return {"spiele": len(auswahl), "punkte": c["S"] * 2 + c["U"],
                "schnitt": round((c["S"] * 2 + c["U"]) / len(auswahl), 2) if auswahl else 0}

    return {"spaet": punkte(spaet), "frueh": punkte(frueh)}


def gegner_bilanz(spiele: list[dict]) -> dict:
    """Gegen wen es am besten und am schlechtesten laeuft."""
    nach_gegner = defaultdict(list)
    for s in _gespielt(spiele):
        nach_gegner[s["gegner"]].append(s["ergebnis"])

    bewertet = []
    for name, spiele_gegen in nach_gegner.items():
        punkte = sum(2 if e["ausgang"] == "S" else 1 if e["ausgang"] == "U" else 0
                     for e in spiele_gegen)
        diff = sum(e["eigene"] - e["fremde"] for e in spiele_gegen)
        bewertet.append({"gegner": name, "spiele": len(spiele_gegen),
                         "punkte": punkte, "differenz": diff})

    # Solange gegen jeden erst einmal gespielt wurde, ist "liebster Gegner"
    # nur ein einzelnes Ergebnis. Erst ab dem Rueckspiel hat das Aussage.
    mehrfach = [x for x in bewertet if x["spiele"] >= 2]
    if not mehrfach:
        return {}
    sortiert = sorted(mehrfach, key=lambda x: (x["punkte"], x["differenz"]))
    return {"schwerster": sortiert[0], "liebster": sortiert[-1]}


def alltag(spiele: list[dict], strecken: dict, werte: dict) -> dict:
    """Zeit und Verbrauch der Saison - der augenzwinkernde Teil.

    Trainings werden aus der Saisonlaenge geschaetzt: vom ersten bis zum
    letzten Spieltag, mal Trainingseinheiten pro Woche.
    """
    if not werte or not spiele:
        return {}

    termine = sorted(s["datum"] for s in spiele)
    wochen = max(1, round((datetime.fromisoformat(termine[-1])
                           - datetime.fromisoformat(termine[0])).days / 7))
    trainings = wochen * werte.get("trainings_pro_woche", 2)
    anzahl_spiele = len(spiele)

    biere = (trainings * werte.get("bier_pro_training", 0)
             + anzahl_spiele * werte.get("bier_pro_spiel", 0))
    liter = biere * GLAS_LITER
    km = strecken.get("gesamt_km") or 0
    verbrauch = round(liter / (km / 100), 1) if km else 0

    minuten = (anzahl_spiele * (werte.get("minuten_vor_spiel", 0)
                                + werte.get("minuten_nach_spiel", 0) + 120)
               + trainings * (90 + werte.get("minuten_nach_training", 0))
               + (strecken.get("stunden") or 0) * 60)

    return {
        "wochen": wochen, "trainings": trainings, "spiele": anzahl_spiele,
        "biere": biere, "liter": round(liter),
        "verbrauch": verbrauch,
        "stunden": round(minuten / 60),
        "tage": round(minuten / 60 / 24, 1),
    }


def alles(spiele: list[dict], heimat: dict, werte: dict | None = None) -> dict:
    """Sammelt sämtliche Kennzahlen einer Mannschaft."""
    strecken = fahrten(spiele, heimat)
    return {
        "fahrten": strecken,
        "bilanz": bilanz(spiele),
        "serien": serien(spiele),
        "krimis": krimis(spiele),
        "tore": tore(spiele),
        "anwurf": anwurfzeiten(spiele),
        "gegner": gegner_bilanz(spiele),
        "alltag": alltag(spiele, strecken, werte or {}),
    }
