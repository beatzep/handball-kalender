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
    "JSG", "MZ", "SF", "VT", "TB", "TSF", "I", "II", "III", "IV", "V",
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


def hole_tabelle(phase_id: int | None) -> dict:
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

    return {
        "runde": runde,
        "gespielt": bool(mit_spielen),
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
        saison_id = str(((spiele[0].get("phase") or {}).get("season_id")) or "")
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


def ist_heimspiel(spiel: dict, team_id: int) -> bool:
    return (spiel.get("local") or {}).get("id") == team_id


def gegner(spiel: dict, team_id: int) -> str:
    seite = "visitor" if ist_heimspiel(spiel, team_id) else "local"
    return normalisiere((spiel.get(seite) or {}).get("name")) or "Unbekannt"


def halle(spiel: dict) -> dict:
    return ((spiel.get("field") or {}).get("installation")) or {}


def adresse(spiel: dict) -> str:
    ort = halle(spiel)
    teile = [normalisiere(ort.get("name")), normalisiere(ort.get("address"))]
    return ", ".join(t for t in teile if t)


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
            "spieltag": spiel.get("round"),
            "heim": ist_heimspiel(spiel, team_id),
            "sequence": (vorher or {}).get("sequence", 0),
        }

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
        titel = f"{marke}{cfg.kurzname} - {gast}" if heim else f"{marke}{gast} - {cfg.kurzname}"

        beschreibung = [
            f"{'Heimspiel' if heim else 'Auswärtsspiel'} gegen {gast}",
            f"Anwurf: {beginn.strftime('%H:%M')} Uhr",
        ]
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

        zeilen += [
            "BEGIN:VEVENT",
            f"UID:{code}@handball.net",
            f"DTSTAMP:{utc(jetzt)}",
            f"DTSTART;TZID=Europe/Berlin:{lokal(start)}",
            f"DTEND;TZID=Europe/Berlin:{lokal(ende)}",
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
        ort = halle(spiel)
        if ort.get("latitude") and ort.get("longitude"):
            try:
                zeilen.append(f"GEO:{float(ort['latitude']):.6f};{float(ort['longitude']):.6f}")
            except (TypeError, ValueError):
                pass

        if not cfg.keine_alarme:
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

def main() -> None:
    p = argparse.ArgumentParser(description="handball.net-Spielplan als .ics exportieren")
    quelle = p.add_mutually_exclusive_group(required=True)
    quelle.add_argument("--team-id", type=int, help="Team-ID von handball.net")
    quelle.add_argument("--suche", help="Teamname suchen statt fester ID (saisonfest)")
    p.add_argument("--saison", default="2627", help="Saison-ID zur Pruefung bei --suche")
    p.add_argument("--geschlecht", choices=["M", "F", "X"],
                   help="bei --suche: M=Maenner, F=Frauen, X=Mixed")
    p.add_argument("--altersklasse", default="ERWACHSENE",
                   help="bei --suche: ERWACHSENE, A-JUGEND, B-JUGEND, ... MINIS")
    p.add_argument("--team-name", help="bei --suche: exakter Teamname zur Unterscheidung "
                                       "von I. und II. Mannschaft")
    p.add_argument("--name", default="Handball Spielplan", help="Name des Kalenders")
    p.add_argument("--kurzname", default="Wir", help="Kurzname des eigenen Teams im Titel")
    p.add_argument("--vorlauf", type=int, default=0,
                   help="Minuten vor Anwurf, zu denen der Termin beginnt (Treffpunkt)")
    p.add_argument("--dauer", type=int, default=120, help="Dauer des Termins in Minuten")
    p.add_argument("--out", default="docs/spielplan.ics", help="Zieldatei")
    p.add_argument("--stand", help="Zustandsdatei fuer die Aenderungserkennung "
                                   "(z.B. docs/stand.json)")
    p.add_argument("--keine-alarme", action="store_true", help="Keine Erinnerungen einbetten")
    p.add_argument("--keine-emojis", action="store_true", help="Titel ohne Heim/Auswaerts-Symbol")
    p.add_argument("--keine-schiris", action="store_true",
                   help="Schiedsrichternamen nicht in den Kalender schreiben")
    cfg = p.parse_args()

    team_id = cfg.team_id or finde_team(cfg)
    spiele = hole_spiele(team_id)
    if not spiele:
        raise SystemExit(f"Keine Spiele fuer Team {team_id} gefunden.")

    # Zustand vergleichen, bevor die neue Datei geschrieben wird - daraus
    # ergeben sich die SEQUENCE-Nummern und die Meldung an die Mannschaft.
    standpfad = Path(cfg.stand) if cfg.stand else None
    alt = lade_stand(standpfad) if standpfad else {}
    neuer_stand, aenderungen = vergleiche(spiele, team_id, alt)

    ziel = Path(cfg.out)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    # write_bytes statt write_text: keine Newline-Uebersetzung, unabhaengig
    # von Plattform und Python-Version - die CRLF stehen schon im Text.
    ziel.write_bytes(baue_kalender(spiele, team_id, cfg, neuer_stand).encode("utf-8"))

    if standpfad:
        standpfad.parent.mkdir(parents=True, exist_ok=True)
        saison_id = str(((spiele[0].get("phase") or {}).get("season_id")) or "")
        standpfad.write_text(json.dumps({
            "aktualisiert": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "team_id": team_id,
            "kalender": cfg.name,
            "liga": normalisiere(liga(spiele[0])),
            "tabelle": hole_tabelle((spiele[0].get("phase") or {}).get("id")),
            "saison": f"20{saison_id[:2]}/{saison_id[2:]}" if len(saison_id) == 4 else "",
            "letzte_aenderungen": aenderungen,
            "spiele": neuer_stand,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    heim = sum(1 for s in spiele if ist_heimspiel(s, team_id))
    erstes, letztes = anwurf(spiele[0]["date"]), anwurf(spiele[-1]["date"])
    print(f"{len(spiele)} Spiele ({heim} Heim / {len(spiele)-heim} Auswärts) "
          f"von {erstes:%d.%m.%Y} bis {letztes:%d.%m.%Y}")
    print(f"geschrieben: {ziel}")

    if aenderungen:
        print(f"\n{len(aenderungen)} Änderung(en) seit dem letzten Lauf:")
        for a in aenderungen:
            print(f"  [{a['art']}] {a['text']}")
    elif alt:
        print("keine Änderungen seit dem letzten Lauf")


if __name__ == "__main__":
    main()
