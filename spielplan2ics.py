#!/usr/bin/env python3
"""Erzeugt aus einem handball.net-Spielplan eine iCalendar-Datei (.ics).

Datenquelle ist die offene JSON-API von handball.net:
    https://www.handball.net/api/new/matches?team_id=<id>

Ohne Abhaengigkeiten - nur Python-Standardbibliothek.

Beispiel:
    python3 spielplan2ics.py --team-id 80924 --out dist/hsg-muho-herren1.ics
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import statistik

API = "https://www.handball.net/api/new"
SPIEL_URL = "https://www.handball.net/match/{id}"
TZ = ZoneInfo("Europe/Berlin")
# handball.net lehnt Anfragen ohne Referer mit 403 ab (Hotlink-Schutz).
# Die Daten selbst sind oeffentlich und ohne Login abrufbar.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")

# Abkuerzungen, die beim Normalisieren von GROSSSCHRIFT gross bleiben muessen.
ABKUERZUNGEN = {
    "HSG", "TSG", "TSV", "TV", "TVR", "TG", "TUS", "SG", "SV", "SC", "FC",
    "VFL", "VFR", "IGS", "NH", "GW", "HSC", "HSV", "HC", "DJK", "ASV", "MTV",
    "JSG", "FSG", "MSG", "WSG", "SGH", "SSV", "PSV", "RSV", "VTV",
    "MZ", "SF", "VT", "TB", "TSF", "I", "II", "III", "IV", "V",
    "1", "2", "3", "A", "B", "C", "D", "E", "F",
}


# --------------------------------------------------------------------------
# API-Zugriff
# --------------------------------------------------------------------------

def hole_json(pfad: str, tolerant: bool = False) -> dict:
    req = urllib.request.Request(f"{API}/{pfad}", headers={
        "accept": "application/json",
        "accept-language": "de-DE,de;q=0.9",
        "user-agent": UA,
        "referer": "https://www.handball.net/",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as antwort:
            daten = json.load(antwort)
    except urllib.error.HTTPError as fehler:
        if tolerant:
            print(f"Warnung: {pfad} nicht abrufbar (HTTP {fehler.code})", file=sys.stderr)
            return {}
        raise SystemExit(f"API-Fehler {fehler.code} bei {pfad}: {fehler.read()[:200]!r}")
    except urllib.error.URLError as fehler:
        if tolerant:
            print(f"Warnung: {pfad} nicht abrufbar ({fehler.reason})", file=sys.stderr)
            return {}
        raise SystemExit(f"Keine Verbindung zu handball.net: {fehler.reason}")
    # Nicht jeder Endpunkt sendet ein success-Feld (standings etwa nicht),
    # darum nur ein ausdrueckliches success:false als Fehler werten.
    if daten.get("success") is False:
        if tolerant:
            print(f"Warnung: {pfad} meldet {daten.get('error')}", file=sys.stderr)
            return {}
        raise SystemExit(f"API meldet Fehler bei {pfad}: {daten.get('error')}")
    return daten


def hole_spiele(team_id: int) -> list[dict]:
    spiele = hole_json(f"matches?team_id={team_id}")["data"]
    return sorted(spiele, key=lambda s: s["date"])


def hole_tabelle(phase_id: int | None, team_id: int | None = None) -> dict:
    """Holt den Tabellenstand der Liga.

    Die API liefert fuer jeden der 22 Spieltage einen eigenen Stand
    (12 Teams x 22 Runden). Gesucht ist der letzte, in dem ueberhaupt
    gespielt wurde - vor dem ersten Anwurf also Runde 1 mit lauter Nullen.
    Faellt der Abruf aus, laeuft der Rest trotzdem durch."""
    if not phase_id:
        return {}
    daten = (hole_tabelle_roh(phase_id) or {}).get("data") or []
    if not daten:
        return {}

    runden: dict[int, list] = {}
    for eintrag in daten:
        runden.setdefault(eintrag.get("round") or 1, []).append(eintrag)

    mit_spielen = [r for r, e in runden.items() if any(x.get("played") for x in e)]
    runde = max(mit_spielen) if mit_spielen else min(runden)
    eintraege = runden[runde]

    # position ist 0, solange nichts gespielt wurde - dann bleibt die
    # Reihenfolge der API erhalten (sie entspricht der Anzeige auf handball.net)
    if any(e.get("position") for e in eintraege):
        eintraege.sort(key=lambda e: e.get("position") or 99)

    # Platzverlauf: die API liefert fuer jeden Spieltag einen eigenen Stand,
    # daraus laesst sich die eigene Platzierung ueber die Saison ablesen.
    verlauf = []
    for r in sorted(runden):
        eigener = next((e for e in runden[r]
                        if (e.get("team") or {}).get("id") == team_id), None)
        if eigener and eigener.get("played") and eigener.get("position"):
            verlauf.append({"runde": r, "platz": eigener["position"],
                            "punkte": eigener.get("points", 0)})

    return {
        "runde": runde,
        "gespielt": bool(mit_spielen),
        "mannschaften": len(eintraege),
        "verlauf": verlauf,
        "eintraege": [{
            "platz": e.get("position") or i + 1,
            "team": normalisiere((e.get("team") or {}).get("name")),
            "team_id": (e.get("team") or {}).get("id"),
            "spiele": e.get("played", 0),
            "punkte": e.get("points", 0),
            "siege": e.get("won", 0),
            "remis": e.get("drawn", 0),
            "niederlagen": e.get("lost", 0),
            "tore": e.get("goals_for", 0),
            "gegentore": e.get("goals_against", 0),
            "differenz": e.get("goals_diff", 0),
        } for i, e in enumerate(eintraege)],
    }


def form_aus_spielen(stand: dict, anzahl: int = 5) -> list[str]:
    """Die letzten Ausgaenge (S/U/N) aus den eigenen Ergebnissen, aeltestes zuerst."""
    gespielt = sorted(
        (s for s in stand.values() if s.get("ergebnis")),
        key=lambda s: s["datum"])
    return [s["ergebnis"]["ausgang"] for s in gespielt[-anzahl:]]


def hole_tabelle_roh(phase_id: int) -> dict:
    return hole_json(f"standings?phase_id={phase_id}", tolerant=True)


def finde_team(cfg: argparse.Namespace) -> int:
    """Sucht die Team-ID zum Namen. Team-IDs wechseln pro Saison, darum wird
    ueber die Spiele geprueft, welcher Kandidat in der gewuenschten Saison spielt.

    Ein Verein meldet viele gleichnamige Teams (Herren, Damen, Jugend, II., III.),
    darum wird bei Mehrdeutigkeit abgebrochen statt geraten - ein stillschweigend
    falscher Spielplan faellt sonst erst beim verpassten Spiel auf."""
    treffer = hole_json(f"teams?name={urllib.parse.quote(cfg.suche)}&per_page=50")["data"]

    kandidaten = [t for t in treffer
                  if (t.get("age_category") or {}).get("name") == cfg.altersklasse]
    if cfg.geschlecht:
        kandidaten = [t for t in kandidaten
                      if (t.get("gender") or {}).get("id") == cfg.geschlecht]
    if cfg.team_name:
        kandidaten = [t for t in kandidaten
                      if t["name"].strip().lower() == cfg.team_name.strip().lower()]

    passend = []
    for team in sorted(kandidaten, key=lambda t: t["id"], reverse=True):
        spiele = hole_json(f"matches?team_id={team['id']}")["data"]
        if not spiele:
            continue
        saison_id = str(hauptphase(spiele).get("season_id") or "")
        if cfg.saison in (None, "", saison_id):
            passend.append((team, saison_id, len(spiele)))

    if not passend:
        raise SystemExit(
            f"Kein Team fuer '{cfg.suche}' (Altersklasse {cfg.altersklasse}"
            f"{', Geschlecht ' + cfg.geschlecht if cfg.geschlecht else ''}) "
            f"in Saison {cfg.saison} gefunden.")

    if len(passend) > 1:
        print("Mehrere Teams passen - bitte mit --team-id, --geschlecht oder "
              "--team-name eingrenzen:", file=sys.stderr)
        for team, saison_id, anzahl in passend:
            geschlecht = (team.get("gender") or {}).get("name", "?")
            print(f"  ID {team['id']}  {team['name']}  ({geschlecht}, "
                  f"{anzahl} Spiele, Saison {saison_id})", file=sys.stderr)
        raise SystemExit(1)

    team, saison_id, _ = passend[0]
    print(f"  Team gefunden: {team['name']} (ID {team['id']}, "
          f"{(team.get('gender') or {}).get('name','?')}, Saison {saison_id})",
          file=sys.stderr)
    return team["id"]


# --------------------------------------------------------------------------
# Aufbereitung der Rohdaten
# --------------------------------------------------------------------------

# In GROSSSCHRIFT-Feldern bleiben Umlaute klein ('HANS-BöCKLER-STRAßE').
# Ein simpler Vergleich mit .upper() scheitert daran, weil 'ß'.upper() == 'SS'
# ist - darum werden die Umlaute vor dem Vergleich ersetzt.
UMLAUTE = str.maketrans({"ä": "Ä", "ö": "Ö", "ü": "Ü", "ß": "SS",
                         "é": "É", "è": "È", "á": "Á", "à": "À"})


# Fuellwoerter, die innerhalb eines Namens klein bleiben ("Sporthalle der IGS").
KLEINSCHREIBUNG = {"der", "die", "das", "des", "dem", "den", "am", "an", "im",
                   "in", "bei", "zur", "zum", "von", "vor", "und", "auf"}


def ist_grossschrift(text: str) -> bool:
    entschaerft = text.translate(UMLAUTE)
    return entschaerft == entschaerft.upper()


def normalisiere(text: str | None) -> str:
    """handball.net liefert vieles in GROSSSCHRIFT ('HANS-BöCKLER-STRAßE').
    Nur solche Strings werden umgebaut, gemischt geschriebene bleiben unberuehrt."""
    if not text:
        return ""
    text = text.strip()
    if not ist_grossschrift(text):    # schon gemischt geschrieben -> so lassen
        return text

    zaehler = 0

    def wort(treffer: re.Match) -> str:
        nonlocal zaehler
        zaehler += 1
        w = treffer.group(0)
        if w.upper() in ABKUERZUNGEN:
            return w.upper()
        if zaehler > 1 and w.lower() in KLEINSCHREIBUNG:
            return w.lower()
        return w[0].upper() + w[1:].lower()

    return re.sub(r"[^\W\d_]+|\d+", wort, text)


def anwurf(rohdatum: str) -> datetime:
    """Die API haengt an jede Zeit '+00:00', die Werte sind aber Ortszeit.
    Gegen die Anzeige auf handball.net geprueft: Rohwert 20:00 -> '20:00 Uhr'.
    Darum: Zeitzone ersetzen, nicht umrechnen."""
    return datetime.fromisoformat(rohdatum).replace(tzinfo=TZ)


def ohne_uhrzeit(zeitpunkt: datetime) -> bool:
    """Turnierspiele stehen beim Verband mit 00:00 - die Uhrzeit ist offen.

    Ungeprueft uebernommen erschiene im Kalender ein Termin um Mitternacht."""
    return zeitpunkt.hour == 0 and zeitpunkt.minute == 0


def ist_heimspiel(spiel: dict, team_id: int) -> bool:
    return (spiel.get("local") or {}).get("id") == team_id


def gegner(spiel: dict, team_id: int) -> str:
    seite = "visitor" if ist_heimspiel(spiel, team_id) else "local"
    return normalisiere((spiel.get(seite) or {}).get("name")) or "Unbekannt"


def gegner_id(spiel: dict, team_id: int) -> int | None:
    seite = "visitor" if ist_heimspiel(spiel, team_id) else "local"
    return (spiel.get(seite) or {}).get("id")


def halle(spiel: dict) -> dict:
    return ((spiel.get("field") or {}).get("installation")) or {}


def koordinaten(spiel: dict) -> tuple[float, float] | None:
    """Koordinaten der Halle, sofern sie in Deutschland liegen koennen.

    Der Verband traegt bei manchen Hallen 0/0 ein - das ist der Nullpunkt
    im Atlantik. Ungeprueft uebernommen schickt das die Navigation vor
    Afrika und macht jede Kilometerrechnung unbrauchbar."""
    ort = halle(spiel)
    try:
        lat, lon = float(ort.get("latitude")), float(ort.get("longitude"))
    except (TypeError, ValueError):
        return None
    if 47.0 <= lat <= 55.5 and 5.0 <= lon <= 16.0:
        return lat, lon
    return None


def adresse(spiel: dict) -> str:
    ort = halle(spiel)
    teile = [normalisiere(ort.get("name")), normalisiere(ort.get("address"))]
    return ", ".join(t for t in teile if t)


def ergebnis(spiel: dict) -> tuple[int, int] | None:
    """Endstand als (Heimtore, Gasttore), sofern das Spiel beendet ist."""
    if not (spiel.get("status") or {}).get("is_finished"):
        return None
    r = spiel.get("result") or {}
    if r.get("local") is None or r.get("visitor") is None:
        return None
    lokal, gast = int(r["local"]), int(r["visitor"])
    # 0:0 gibt es im Handball nicht. In der F-Jugend und bei den Minis wird
    # ohne Ergebniszaehlung gespielt - der Verband markiert die Partien
    # trotzdem als beendet und laesst 0:0 stehen. Als Endstand im Kalender
    # waere das ein torloses Remis, also schlicht falsch.
    if lokal == 0 and gast == 0:
        return None
    return lokal, gast


def hauptphase(spiele: list[dict]) -> dict:
    """Die Phase, in der die meisten Spiele stattfinden.

    Mannschaften spielen oft Liga *und* Pokal. Die Phase des ersten Spiels
    zu nehmen liefert dann zufaellig die Pokalgruppe - und damit eine
    Tabelle mit drei Mannschaften statt der Liga mit zehn."""
    haeufigkeit: dict[int, int] = {}
    phasen: dict[int, dict] = {}
    for spiel in spiele:
        p = spiel.get("phase") or {}
        if not p.get("id"):
            continue
        haeufigkeit[p["id"]] = haeufigkeit.get(p["id"], 0) + 1
        phasen[p["id"]] = p
    if not haeufigkeit:
        return {}
    return phasen[max(haeufigkeit, key=haeufigkeit.get)]


def liga(spiel: dict) -> str:
    return ((spiel.get("phase") or {}).get("competition") or {}).get("name", "")


def schiedsrichter(spiel: dict) -> str:
    namen = [f"{r.get('first_name','')} {r.get('last_name','')}".strip()
             for r in (spiel.get("referees") or [])]
    return ", ".join(n for n in namen if n)


# --------------------------------------------------------------------------
# Aenderungserkennung zwischen zwei Laeufen
# --------------------------------------------------------------------------

WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def kurzdatum(zeitpunkt: datetime) -> str:
    return f"{WOCHENTAGE[zeitpunkt.weekday()]} {zeitpunkt:%d.%m.} {zeitpunkt:%H:%M}"


def kurzort(volle_adresse: str) -> str:
    """Fuer Meldungen reicht der Hallenname, nicht die ganze Anschrift."""
    return volle_adresse.split(",")[0].strip() if volle_adresse else "unbekannt"


def lade_stand(pfad: Path) -> dict:
    if not pfad.exists():
        return {}
    try:
        return json.loads(pfad.read_text(encoding="utf-8")).get("spiele", {})
    except (json.JSONDecodeError, OSError) as fehler:
        print(f"Warnung: Zustandsdatei unlesbar ({fehler}) - starte neu", file=sys.stderr)
        return {}


def vergleiche(spiele: list[dict], team_id: int, alt: dict) -> tuple[dict, list[dict]]:
    """Vergleicht den frischen Spielplan mit dem letzten Lauf.

    Rueckgabe: neuer Zustand und die Liste der Aenderungen. SEQUENCE wird pro
    Spiel hochgezaehlt, sobald sich Datum oder Halle aendern - Kalender-Clients
    erkennen daran, dass es sich um eine Aktualisierung handelt und nicht um
    einen zweiten Termin."""
    neu: dict = {}
    aenderungen: list[dict] = []
    erstlauf = not alt

    for spiel in spiele:
        code = spiel.get("code") or str(spiel["id"])
        beginn = anwurf(spiel["date"])
        ort = adresse(spiel)
        vorher = alt.get(code)

        eintrag = {
            "datum": beginn.strftime("%Y-%m-%dT%H:%M:%S"),
            "ort": ort,
            "halle": normalisiere(halle(spiel).get("name")),
            "gegner": gegner(spiel, team_id),
            "gegner_id": gegner_id(spiel, team_id),
            "match_id": spiel.get("id"),
            "lat": (koordinaten(spiel) or (None, None))[0],
            "lon": (koordinaten(spiel) or (None, None))[1],
            "spieltag": spiel.get("round"),
            "heim": ist_heimspiel(spiel, team_id),
            "ohne_zeit": ohne_uhrzeit(beginn),
            "sequence": (vorher or {}).get("sequence", 0),
        }
        tore = ergebnis(spiel)
        if tore:
            eigene, fremde = (tore if eintrag["heim"] else tore[::-1])
            eintrag["ergebnis"] = {"heim": tore[0], "gast": tore[1],
                                   "eigene": eigene, "fremde": fremde,
                                   "ausgang": "S" if eigene > fremde
                                              else "N" if eigene < fremde else "U"}

        if vorher is None:
            if not erstlauf:
                aenderungen.append({
                    "art": "neu", "code": code, "spieltag": eintrag["spieltag"],
                    "text": f"Neues Spiel gegen {eintrag['gegner']}: "
                            f"{kurzdatum(beginn)} in "
                            f"{eintrag['halle'] or kurzort(ort)}",
                })
        else:
            datum_neu = vorher.get("datum") != eintrag["datum"]
            ort_neu = vorher.get("ort") != ort
            if datum_neu or ort_neu:
                eintrag["sequence"] = vorher.get("sequence", 0) + 1
                alt_zeit = datetime.fromisoformat(vorher["datum"])
                teile = []
                if datum_neu:
                    teile.append(f"{kurzdatum(alt_zeit)} → {kurzdatum(beginn)}")
                if ort_neu:
                    teile.append(f"{vorher.get('halle') or kurzort(vorher.get('ort',''))}"
                                 f" → {eintrag['halle'] or kurzort(ort)}")
                aenderungen.append({
                    "art": "verlegt" if datum_neu else "halle",
                    "code": code, "spieltag": eintrag["spieltag"],
                    "text": f"Spieltag {eintrag['spieltag']} gegen "
                            f"{eintrag['gegner']}: " + ", ".join(teile),
                })

        neu[code] = eintrag

    for code, vorher in alt.items():
        if code not in neu:
            aenderungen.append({
                "art": "entfallen", "code": code, "spieltag": vorher.get("spieltag"),
                "text": f"Spiel gegen {vorher.get('gegner','?')} am "
                        f"{kurzdatum(datetime.fromisoformat(vorher['datum']))} "
                        f"steht nicht mehr im Spielplan",
            })

    return neu, aenderungen


# --------------------------------------------------------------------------
# iCalendar-Ausgabe
# --------------------------------------------------------------------------

def escape(text: str) -> str:
    return (text.replace("\\", "\\\\").replace(";", "\\;")
                .replace(",", "\\,").replace("\n", "\\n"))


def falte(zeile: str) -> str:
    """RFC 5545: Zeilen auf 75 Oktett begrenzen, Fortsetzung mit Leerzeichen.
    Gefaltet wird byteweise, damit keine Umlaute zerschnitten werden."""
    if len(zeile.encode("utf-8")) <= 75:
        return zeile
    stuecke: list[str] = []
    aktuell: list[str] = []
    laenge = 0
    for zeichen in zeile:
        breite = len(zeichen.encode("utf-8"))
        if laenge + breite > 75:
            stuecke.append("".join(aktuell))
            aktuell, laenge = [" "], 1
        aktuell.append(zeichen)
        laenge += breite
    stuecke.append("".join(aktuell))
    return "\r\n".join(stuecke)


def lokal(zeitpunkt: datetime) -> str:
    return zeitpunkt.strftime("%Y%m%dT%H%M%S")


def utc(zeitpunkt: datetime) -> str:
    return zeitpunkt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


VTIMEZONE = """BEGIN:VTIMEZONE
TZID:Europe/Berlin
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
TZNAME:CEST
DTSTART:19700329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
TZNAME:CET
DTSTART:19701025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE""".split("\n")


def baue_kalender(spiele: list[dict], team_id: int, cfg: argparse.Namespace,
                  stand: dict | None = None) -> str:
    jetzt = datetime.now(timezone.utc)
    zeilen = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//handball-kalender//spielplan2ics//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape(cfg.name)}",
        "X-WR-TIMEZONE:Europe/Berlin",
        f"X-WR-CALDESC:{escape('Spielplan ' + cfg.name + ' - Quelle: handball.net')}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
        *VTIMEZONE,
    ]

    for spiel in spiele:
        beginn = anwurf(spiel["date"])
        start = beginn - timedelta(minutes=cfg.vorlauf)
        ende = beginn + timedelta(minutes=cfg.dauer)
        heim = ist_heimspiel(spiel, team_id)

        marke = "" if cfg.keine_emojis else ("\U0001F3E0 " if heim else "\U0001F697 ")
        gast = gegner(spiel, team_id)
        tore = ergebnis(spiel)
        # Gespielte Partien tragen den Endstand im Titel - so steht das
        # Ergebnis spaeter auch im Kalender und nicht nur auf der Seite.
        trenner = f" {tore[0]}:{tore[1]} " if tore else " - "
        titel = (f"{marke}{cfg.kurzname}{trenner}{gast}" if heim
                 else f"{marke}{gast}{trenner}{cfg.kurzname}")

        beschreibung = [
            f"{'Heimspiel' if heim else 'Auswärtsspiel'} gegen {gast}",
            ("Anwurf: noch nicht angesetzt" if ohne_uhrzeit(beginn)
             else f"Anwurf: {beginn.strftime('%H:%M')} Uhr"),
        ]
        if tore:
            eigene, fremde = (tore if heim else tore[::-1])
            ausgang = ("Sieg" if eigene > fremde else
                       "Niederlage" if eigene < fremde else "Unentschieden")
            beschreibung.insert(0, f"Endstand: {tore[0]}:{tore[1]} ({ausgang})")
        if cfg.vorlauf:
            beschreibung.append(f"Treffpunkt: {start.strftime('%H:%M')} Uhr")
        if normalisiere(liga(spiel)):
            beschreibung.append(f"Liga: {normalisiere(liga(spiel))}")
        if spiel.get("round"):
            beschreibung.append(f"Spieltag: {spiel['round']}")
        if not cfg.keine_schiris and schiedsrichter(spiel):
            beschreibung.append(f"Schiedsrichter: {schiedsrichter(spiel)}")
        beschreibung.append(f"Spielnummer: {spiel.get('code','')}")
        beschreibung.append(SPIEL_URL.format(id=spiel["id"]))

        code = spiel.get("code") or str(spiel["id"])
        folge = ((stand or {}).get(code) or {}).get("sequence", 0)

        # Ohne angesetzte Uhrzeit wird daraus ein ganztaegiger Termin -
        # ein Eintrag um Mitternacht waere schlicht falsch. DTEND ist bei
        # Tagesangaben ausschliessend, zeigt also auf den Folgetag.
        offen = ohne_uhrzeit(beginn)
        if offen:
            zeit_zeilen = [f"DTSTART;VALUE=DATE:{beginn:%Y%m%d}",
                           f"DTEND;VALUE=DATE:{(beginn + timedelta(days=1)):%Y%m%d}"]
        else:
            zeit_zeilen = [f"DTSTART;TZID=Europe/Berlin:{lokal(start)}",
                           f"DTEND;TZID=Europe/Berlin:{lokal(ende)}"]

        zeilen += [
            "BEGIN:VEVENT",
            f"UID:{code}@handball.net",
            f"DTSTAMP:{utc(jetzt)}",
            *zeit_zeilen,
            f"SUMMARY:{escape(titel)}",
            f"DESCRIPTION:{escape(chr(10).join(beschreibung))}",
            f"URL:{SPIEL_URL.format(id=spiel['id'])}",
            f"SEQUENCE:{folge}",
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            f"CATEGORIES:Handball,{'Heimspiel' if heim else 'Auswärtsspiel'}",
        ]

        if adresse(spiel):
            zeilen.append(f"LOCATION:{escape(adresse(spiel))}")
        punkt = koordinaten(spiel)
        if punkt:
            zeilen.append(f"GEO:{punkt[0]:.6f};{punkt[1]:.6f}")

        if not cfg.keine_alarme and not offen:
            for ausloeser, text in (("-P1D", "Morgen Spiel"), ("-PT3H", "Gleich Spiel")):
                zeilen += [
                    "BEGIN:VALARM",
                    "ACTION:DISPLAY",
                    f"TRIGGER:{ausloeser}",
                    f"DESCRIPTION:{escape(text + ': ' + titel.strip())}",
                    "END:VALARM",
                ]

        zeilen.append("END:VEVENT")

    zeilen.append("END:VCALENDAR")
    return "\r\n".join(falte(z) for z in zeilen) + "\r\n"


# --------------------------------------------------------------------------

def verarbeite_team(team: dict, cfg: argparse.Namespace, alt: dict) -> tuple[dict, list]:
    """Holt einen Spielplan, schreibt die .ics und liefert Zustand + Aenderungen."""
    team_id = team["team_id"]
    spiele = hole_spiele(team_id)
    if not spiele:
        raise SystemExit(f"Keine Spiele fuer Team {team_id} ({team['name']}).")

    neuer_stand, aenderungen = vergleiche(spiele, team_id, alt.get("spiele") or {})

    # Der Kalendername landet in der Kalender-App - dort muss der Verein
    # dranstehen, sonst heisst der Kalender bei allen nur "Herren I".
    einstellung = argparse.Namespace(**vars(cfg))
    einstellung.kurzname = team["kurzname"]
    einstellung.name = f"{cfg.verein} – {team['name']}"

    inhalt = baue_kalender(spiele, team_id, einstellung, neuer_stand).encode("utf-8")
    ziel = Path(cfg.out_dir) / team["datei"]
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_bytes(inhalt)

    # Frueher vergebene Dateinamen weiter bedienen - GitHub Pages kann nicht
    # umleiten, ein umbenannter Feed wuerde bestehende Abos stillschweigend
    # ins Leere laufen lassen.
    for alt_name in team.get("alias") or []:
        (Path(cfg.out_dir) / alt_name).write_bytes(inhalt)

    phase = hauptphase(spiele)
    saison_id = str(phase.get("season_id") or "")
    heim = sum(1 for x in spiele if ist_heimspiel(x, team_id))
    print(f"  {team['name']:<12} {len(spiele):2} Spiele "
          f"({heim} Heim / {len(spiele) - heim} Auswärts)  -> {ziel.name}")

    return {
        "team_id": team_id,
        "name": team["name"],
        "kurzname": team["kurzname"],
        "gruppe": team.get("gruppe", ""),
        "datei": team["datei"],
        "kalender": einstellung.name,
        "liga": normalisiere((phase.get("competition") or {}).get("name", "")),
        "saison": f"20{saison_id[:2]}/{saison_id[2:]}" if len(saison_id) == 4 else "",
        # Ohne Wertung (Minis etwa) gibt es keine Tabelle - die Sammelliste
        # aller gemeldeten Mannschaften waere keine.
        "tabelle": (hole_tabelle(phase.get("id"), team_id)
                    if phase.get("has_standings") else {}),
        "form": form_aus_spielen(neuer_stand),
        "statistik": statistik.alles(list(neuer_stand.values()),
                                     cfg.heimat, team.get("alltag")),
        "letzte_aenderungen": aenderungen,
        "spiele": neuer_stand,
    }, aenderungen


def main() -> None:
    p = argparse.ArgumentParser(description="handball.net-Spielplaene als .ics exportieren")
    p.add_argument("--teams", default="teams.json",
                   help="Konfigurationsdatei mit den Mannschaften")
    p.add_argument("--out-dir", default="docs", help="Zielverzeichnis")
    p.add_argument("--daten", default="docs/daten.json",
                   help="gemeinsame Datendatei fuer Seite und Aenderungserkennung")
    p.add_argument("--vorlauf", type=int, default=0,
                   help="Minuten vor Anwurf, zu denen der Termin beginnt (Treffpunkt)")
    p.add_argument("--dauer", type=int, default=120, help="Dauer des Termins in Minuten")
    p.add_argument("--keine-alarme", action="store_true", help="Keine Erinnerungen einbetten")
    p.add_argument("--keine-emojis", action="store_true", help="Titel ohne Heim/Auswaerts-Symbol")
    p.add_argument("--keine-schiris", action="store_true",
                   help="Schiedsrichternamen nicht in den Kalender schreiben")
    cfg = p.parse_args()

    konfig = json.loads(Path(cfg.teams).read_text(encoding="utf-8"))
    cfg.verein = konfig.get("verein", "")
    cfg.heimat = konfig.get("heimat") or {}

    datenpfad = Path(cfg.daten)
    bisher = {}
    if datenpfad.exists():
        try:
            bisher = json.loads(datenpfad.read_text(encoding="utf-8")).get("teams") or {}
        except (json.JSONDecodeError, OSError) as fehler:
            print(f"Warnung: {datenpfad} unlesbar ({fehler}) - starte neu", file=sys.stderr)

    teams, alle_aenderungen, ausgefallen = {}, [], []
    for team in konfig["teams"]:
        schluessel = team["schluessel"]
        try:
            stand, aenderungen = verarbeite_team(team, cfg, bisher.get(schluessel) or {})
        except SystemExit as fehler:
            # Eine Mannschaft ohne Spielplan (Saisonende, Rueckzug, API-Aussetzer)
            # darf die uebrigen nicht blockieren. Ihr letzter Stand bleibt stehen.
            print(f"  {team['name']:<12} FEHLGESCHLAGEN: {fehler}", file=sys.stderr)
            ausgefallen.append(team["name"])
            if bisher.get(schluessel):
                teams[schluessel] = bisher[schluessel]
                print(f"  {'':<12} letzter bekannter Stand bleibt erhalten", file=sys.stderr)
            continue
        teams[schluessel] = stand
        alle_aenderungen += [dict(a, mannschaft=team["name"]) for a in aenderungen]

    if ausgefallen and len(ausgefallen) == len(konfig["teams"]):
        raise SystemExit("Keine einzige Mannschaft konnte geladen werden - Abbruch.")

    datenpfad.parent.mkdir(parents=True, exist_ok=True)
    datenpfad.write_text(json.dumps({
        "aktualisiert": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "verein": cfg.verein,
        "teams": teams,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"geschrieben: {datenpfad}")
    if ausgefallen:
        print(f"\nWARNUNG: nicht aktualisiert: {', '.join(ausgefallen)}")

    if alle_aenderungen:
        print(f"\n{len(alle_aenderungen)} Änderung(en) seit dem letzten Lauf:")
        for a in alle_aenderungen:
            print(f"  [{a['art']}] {a['mannschaft']}: {a['text']}")
    elif bisher:
        print("keine Änderungen seit dem letzten Lauf")


if __name__ == "__main__":
    main()
