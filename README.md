# Handball-Kalender

Holt den Spielplan der **HSG MuRu Herren I** von handball.net und veröffentlicht
ihn als abonnierbaren Kalender. Wer ihn abonniert hat, bekommt Verlegungen
automatisch — ohne etwas zu tun.

Nur Python-Standardbibliothek, keine Abhängigkeiten.

```
handball.net API  →  GitHub Action (täglich)  →  docs/*.ics auf GitHub Pages  →  Kalender der Mannschaft
```

## Die vier Teile

| Datei | Aufgabe |
|---|---|
| `spielplan2ics.py` | holt die Spiele, erzeugt die `.ics`, erkennt Änderungen gegenüber dem Vortag |
| `pruefe_ics.py` | validiert die erzeugte Datei (läuft im Workflow als Schutznetz) |
| `baue_seite.py` | baut `docs/index.html` — die Seite, die die Mannschaft zu sehen bekommt |
| `commit_text.py` | formuliert die Commit-Nachricht, damit Verlegungen in Benachrichtigungen auftauchen |

## Lokal ausführen

```bash
python3 spielplan2ics.py --team-id 80924 \
  --name "HSG MuRu - Herren I" --kurzname "HSG MuRu" --keine-schiris \
  --out docs/hsg-muru-herren1.ics --stand docs/stand.json

python3 pruefe_ics.py docs/hsg-muru-herren1.ics

python3 baue_seite.py --stand docs/stand.json --ics hsg-muru-herren1.ics \
  --basis-url "https://DEINNAME.github.io/handball-kalender" --out docs/index.html
```

### Optionen

| Option | Wirkung |
|---|---|
| `--vorlauf 60` | Termin beginnt 60 Min vor Anwurf (Treffpunkt), Anwurfzeit steht in der Beschreibung |
| `--dauer 105` | Termindauer in Minuten (Standard 120) |
| `--keine-alarme` | ohne Erinnerungen (Standard: 1 Tag und 3 Std vorher) |
| `--keine-emojis` | Titel ohne 🏠/🚗 |
| `--keine-schiris` | Schiedsrichternamen weglassen (im öffentlichen Feed sinnvoll) |
| `--suche "Mutterstadt"` | Team über den Namen suchen statt feste ID — überlebt den Saisonwechsel |

Bei `--suche` grenzen `--geschlecht M` und `--team-name "HSG Mutterstadt/Ruchheim"`
ein; ohne das bricht die Suche bei mehreren Treffern ab und listet die Kandidaten.

## Wie die Änderungserkennung funktioniert

`docs/stand.json` hält fest, wann und wo jedes Spiel zuletzt stattfand.
Beim nächsten Lauf wird verglichen:

- **Datum oder Halle geändert** → Meldung, und `SEQUENCE` des Termins wird um 1
  erhöht. Weil die `UID` (die Spielnummer) gleich bleibt, **verschieben**
  Kalender-Apps den vorhandenen Termin, statt einen zweiten anzulegen.
- **Spiel neu / entfallen** → Meldung.
- **Erstlauf** → keine Meldungen, nur Zustand anlegen.

Die Meldungen landen an drei Stellen: im gelben Kasten auf der Seite, in der
Commit-Nachricht und in der Zusammenfassung des Action-Laufs.

## Betrieb

Der Workflow läuft täglich um 03:17 UTC und committet das Ergebnis. Er committet
auch dann, wenn sich fachlich nichts geändert hat (`DTSTAMP` und der Prüfzeitpunkt
ändern sich immer). Das ist Absicht:

- Die Seite kann ehrlich anzeigen, wann zuletzt abgeglichen wurde.
- Das Repo bleibt aktiv — GitHub deaktiviert geplante Workflows in Repos, die
  60 Tage ruhen.

Die Commit-Nachricht unterscheidet trotzdem klar: `Abgleich 28.08.2026: keine
Aenderungen` gegenüber `Spieltag 7 verlegt` mit den Details im Rumpf.

## Fallstricke, die hier schon gelöst sind

1. **Die Zeitzone in den Rohdaten ist falsch deklariert.** Die API liefert
   `2026-08-29T20:00:00+00:00`, behauptet also UTC. Gegen die Anzeige auf
   handball.net geprüft: gemeint ist 20:00 Ortszeit. Naiv eingelesen geht der
   Kalender im Sommer zwei und im Winter eine Stunde falsch.
2. **Umlaute in Großschrift.** Adressen kommen als `HANS-BöCKLER-STRAßE`. Die
   naheliegende Prüfung `text == text.upper()` scheitert, weil `"ß".upper()`
   gleich `"SS"` ist — der Text gilt dann fälschlich als gemischt geschrieben.
3. **Zeilenumbruch nach 75 Byte** (RFC 5545) muss an Zeichen-, nicht an
   Bytegrenzen erfolgen, sonst zerschneidet man Umlaute.
4. **`Referer`-Pflicht:** ohne diesen Header antwortet die API mit 403.

## Die Datenquelle

Offene JSON-API, ohne Login und ohne Key:

| Zweck | Aufruf |
|---|---|
| Spielplan eines Teams | `GET https://www.handball.net/api/new/matches?team_id=80924` |
| Team suchen | `GET .../api/new/teams?name=Mutterstadt&per_page=50` |
| Spielseite im Web | `https://www.handball.net/match/<id>` |

`matches` akzeptiert außerdem `club_id`, `installation_id`, `date_from`,
`date_to`, `competition_id` und weitere Filter.

**Achtung bei Koordinaten:** `field.installation` (Halle) ist korrekt,
`club.latitude/longitude` (Verein) zeigt mitten in die USA.

**Team-IDs wechseln pro Saison.** Für 26/27 ist die Herren I die `80924`, in der
Vorsaison war es eine ID um 10500. Vor der Saison 27/28 also die ID im Workflow
prüfen — oder auf `--suche` umstellen.

## Rücksicht auf die Quelle

Die Daten gehören handball.net. Ein Abruf pro Tag reicht; häufigeres Pollen
bringt nichts und belastet die Seite nur.
