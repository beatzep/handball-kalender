#!/usr/bin/env python3
"""Wertet die Spielberichte aus: Schuetzen, Verlauf, Laeufe, Strafen.

Die Berichte liegen roh in `berichte_cache.json` (siehe spielberichte.py).
Hier entsteht daraus, was der Statistik-Reiter und die Torjaegerliste
zeigen. Gerechnet wird ausschliesslich aus vorhandenen Daten - kein
Netzzugriff.

Zwei Regeln durchziehen das ganze Modul:

**Nichts schaetzen.** Wo ein Bericht fehlt, steht das als solches in der
Ausgabe (`quelle`), damit die Seite es benennen kann. Eine Zahl, die auf
halben Daten beruht, waere schlimmer als keine.

**Namen nur so weit wie noetig.** Bei den Aktiven voll, bei der Jugend
Vorname und erster Buchstabe des Nachnamens - "Lisa M.". Die Spieler-ID
bleibt erhalten, damit sich ein Spieler ueber mehrere Mannschaften
zusammenfuehren laesst, ohne dass dafuer Namen verglichen werden muessen.
"""

from __future__ import annotations

# Ab dieser Serie ohne Gegentor lohnt es, von einem Lauf zu sprechen.
LAUF_AB = 3


def anzeigename(spieler: dict, jugend: bool) -> str:
    """Voller Name bei den Aktiven, sonst 'Lisa M.'."""
    vorname = (spieler.get("vorname") or "").strip()
    nachname = (spieler.get("nachname") or "").strip()
    if not jugend:
        return " ".join(x for x in (vorname, nachname) if x)
    if vorname and nachname:
        return f"{vorname} {nachname[0]}."
    return vorname or (f"{nachname[0]}." if nachname else "")


def ist_siebenmeter(ereignis: dict) -> bool:
    return "siebenmeter" in str(ereignis.get("art") or "").lower()


def ist_fehlwurf(ereignis: dict) -> bool:
    art = str(ereignis.get("art") or "").lower()
    return "siebenmeter" in art and not ereignis.get("ist_tor")


def schuetzen(berichte: list[dict], team_id: int, jugend: bool) -> list[dict]:
    """Wer hat wie oft getroffen, und wie sicher vom Siebenmeter?

    Gezaehlt wird je Spieler ueber alle vorliegenden Berichte. `spiele` ist
    die Zahl der Spiele, in denen der Spieler ueberhaupt vorkommt - nicht
    die Zahl der Spiele der Mannschaft. Wer zweimal fehlte, hat eine andere
    Grundlage fuer "Tore je Spiel" als wer immer dabei war.
    """
    gesammelt: dict[str, dict] = {}
    for bericht in berichte:
        gesehen: set[str] = set()
        for e in bericht.get("ereignisse") or []:
            if e.get("team_id") != team_id:
                continue
            spieler = e.get("spieler") or {}
            pid = spieler.get("id")
            if not pid:
                continue
            eintrag = gesammelt.setdefault(pid, {
                "id": pid, "name": anzeigename(spieler, jugend),
                "tore": 0, "siebenmeter_tore": 0, "siebenmeter_wuerfe": 0,
                "zwei_minuten": 0, "verwarnungen": 0, "spiele": 0,
            })
            if pid not in gesehen:
                eintrag["spiele"] += 1
                gesehen.add(pid)
            if e.get("ist_tor"):
                eintrag["tore"] += 1
                if ist_siebenmeter(e):
                    eintrag["siebenmeter_tore"] += 1
                    eintrag["siebenmeter_wuerfe"] += 1
            elif ist_fehlwurf(e):
                eintrag["siebenmeter_wuerfe"] += 1
            else:
                art = str(e.get("art") or "").lower()
                if "zwei" in art:
                    eintrag["zwei_minuten"] += 1
                elif "verwarnung" in art:
                    eintrag["verwarnungen"] += 1

    # Wer im Bericht steht, aber nicht getroffen hat (etwa nur mit einer
    # Zeitstrafe), gehoert nicht in eine Torschuetzenliste. Seine Strafen
    # sind in der Mannschaftsauswertung enthalten.
    liste = [e for e in gesammelt.values() if e["tore"] > 0]
    for e in liste:
        e["tore_je_spiel"] = round(e["tore"] / e["spiele"], 1) if e["spiele"] else 0.0
        e["siebenmeter_quote"] = (round(100 * e["siebenmeter_tore"]
                                        / e["siebenmeter_wuerfe"])
                                  if e["siebenmeter_wuerfe"] else None)
    liste.sort(key=lambda e: (-e["tore"], -e["tore_je_spiel"], e["name"]))
    return liste


def verlauf(bericht: dict) -> list[list[int]]:
    """Der Spielstand ueber die Zeit als [Minute, Heim, Gast].

    Grundlage des Spielfilms. Der Anfangsstand 0:0 steht bewusst mit drin,
    sonst begaenne die Kurve beim ersten Tor.
    """
    punkte = [[0, 0, 0]]
    for e in bericht.get("ereignisse") or []:
        stand = e.get("stand")
        if not stand or stand[0] is None or stand[1] is None:
            continue
        minute = e.get("spielminute")
        if minute is None:
            continue
        punkt = [int(minute), int(stand[0]), int(stand[1])]
        if punkt[1:] != punkte[-1][1:]:
            punkte.append(punkt)
    return punkte


def laeufe(bericht: dict, team_id: int) -> dict:
    """Die laengste Serie ohne Gegentor, auf beiden Seiten.

    Sagt mehr ueber ein Spiel als der Endstand: ein 31:23 kann ein
    durchgehend ruhiges Spiel gewesen sein oder eines, das ein Lauf von
    sechs Toren entschieden hat.
    """
    bester = {"eigene": 0, "fremde": 0, "eigene_ab": None, "fremde_ab": None}
    reihe_eigen = reihe_fremd = 0
    start_eigen = start_fremd = None
    for e in bericht.get("ereignisse") or []:
        if not e.get("ist_tor"):
            continue
        minute = e.get("spielminute")
        if e.get("team_id") == team_id:
            reihe_eigen += 1
            reihe_fremd = 0
            if start_eigen is None:
                start_eigen = minute
            if reihe_eigen > bester["eigene"]:
                bester["eigene"] = reihe_eigen
                bester["eigene_ab"] = start_eigen
            start_fremd = None
        else:
            reihe_fremd += 1
            reihe_eigen = 0
            if start_fremd is None:
                start_fremd = minute
            if reihe_fremd > bester["fremde"]:
                bester["fremde"] = reihe_fremd
                bester["fremde_ab"] = start_fremd
            start_eigen = None
    for seite in ("eigene", "fremde"):
        if bester[seite] < LAUF_AB:
            bester[seite] = 0
            bester[f"{seite}_ab"] = None
    return bester


def verteilung(berichte: list[dict], team_id: int) -> dict:
    """Auf wie viele Schuetzen verteilen sich die Tore - hier und drueben?

    Eine Mannschaft, die ueber neun Leute trifft, ist schwerer zu verteidigen
    als eine, deren Tore zu zwei Dritteln von einem kommen.
    """
    eigene: dict[str, int] = {}
    fremde: dict[str, int] = {}
    for bericht in berichte:
        for e in bericht.get("ereignisse") or []:
            if not e.get("ist_tor"):
                continue
            pid = (e.get("spieler") or {}).get("id")
            if not pid:
                continue
            ziel = eigene if e.get("team_id") == team_id else fremde
            ziel[pid] = ziel.get(pid, 0) + 1
    def groesster_anteil(werte: dict[str, int]) -> int | None:
        summe = sum(werte.values())
        return round(100 * max(werte.values()) / summe) if summe else None
    return {
        "eigene_schuetzen": len(eigene),
        "fremde_schuetzen": len(fremde),
        "eigene_tore": sum(eigene.values()),
        "fremde_tore": sum(fremde.values()),
        "groesster_anteil": groesster_anteil(eigene),
    }


def strafen_nach_abschnitt(berichte: list[dict], team_id: int) -> dict:
    """Zeitstrafen in Viertelstunden. Zeigt, wann es eng wird."""
    faecher = {"0-15": 0, "15-30": 0, "30-45": 0, "45-60": 0}
    gesamt = 0
    for bericht in berichte:
        for e in bericht.get("ereignisse") or []:
            if e.get("team_id") != team_id:
                continue
            if "zwei" not in str(e.get("art") or "").lower():
                continue
            gesamt += 1
            minute = e.get("spielminute")
            if minute is None:
                continue
            grenze = min(int(minute) // 15, 3)
            faecher[list(faecher)[grenze]] += 1
    return {"gesamt": gesamt, "abschnitte": faecher}


def alles(spiele: dict, cache: dict, team_id: int, jugend: bool) -> dict:
    """Sammelt die Auswertung einer Mannschaft.

    `spiele` sind die Spiele der Mannschaft aus daten.json, `cache` die
    rohen Berichte. In `quelle` steht, worauf die Zahlen beruhen - und wie
    viele Spiele dabei fehlen, weil die Quelle nichts geliefert hat.
    """
    gelaufen = [s for s in spiele.values() if s.get("ergebnis")]
    berichte, ohne_bericht, offen = [], 0, 0
    je_spiel = []
    for spiel in sorted(gelaufen, key=lambda s: s["datum"]):
        eintrag = cache.get(str(spiel.get("match_id")))
        if eintrag is None:
            offen += 1
            continue
        if eintrag.get("ohne_bericht") or not eintrag.get("ereignisse"):
            ohne_bericht += 1
            continue
        berichte.append(eintrag)
        je_spiel.append({
            "match_id": spiel.get("match_id"),
            "datum": spiel["datum"],
            "gegner": spiel.get("gegner"),
            "heim": bool(spiel.get("heim")),
            "verlauf": verlauf(eintrag),
            "laeufe": laeufe(eintrag, team_id),
            # Dieselbe Rechnung wie ueber die Saison, nur auf ein Spiel
            # angewandt - fuer die Detailansicht in der Spieleliste.
            "schuetzen": schuetzen([eintrag], team_id, jugend),
            "strafen": strafen_nach_abschnitt([eintrag], team_id)["gesamt"],
        })

    return {
        "quelle": {
            "spiele_gelaufen": len(gelaufen),
            "mit_bericht": len(berichte),
            "ohne_bericht": ohne_bericht,   # Liga fuehrt keinen
            "offen": offen,                 # noch nicht abgerufen
        },
        "schuetzen": schuetzen(berichte, team_id, jugend),
        "verteilung": verteilung(berichte, team_id),
        "strafen": strafen_nach_abschnitt(berichte, team_id),
        "spiele": je_spiel,
    }
