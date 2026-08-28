# Handball-Kalender

Holt die Spielpläne der **HSG Mutterstadt/Ruchheim** (Herren I, Herren II,
Damen) von handball.net und veröffentlicht sie als abonnierbare Kalender.
Wer abonniert hat, bekommt Verlegungen automatisch — ohne etwas zu tun.

Nur Python-Standardbibliothek, keine Abhängigkeiten.

```
handball.net API  →  GitHub Action (täglich)  →  docs/*.ics auf GitHub Pages  →  Kalender der Mannschaft
```

## Die vier Teile

| Datei | Aufgabe |
|---|---|
| `teams.json` | welche Mannschaften abgerufen werden (Team-ID, Name, Dateiname) |
| `spielplan2ics.py` | holt Spiele und Tabellen, erzeugt je Mannschaft eine `.ics`, erkennt Änderungen |
| `pruefe_ics.py` | validiert die erzeugten Dateien (läuft im Workflow als Schutznetz) |
| `baue_seite.py` | baut `docs/index.html` — eine Seite für alle Mannschaften |
| `seite_stil.py`, `seite_skript.py` | Stylesheet und Browser-Logik der Seite |
| `commit_text.py` | formuliert die Commit-Nachricht, damit Verlegungen in Benachrichtigungen auftauchen |

**Eine neue Mannschaft aufnehmen:** Eintrag in `teams.json` ergänzen, fertig —
Kalender, Seite, Tabelle und Änderungserkennung laufen dann automatisch mit.

**Dateinamen niemals stillschweigend ändern.** GitHub Pages kann nicht
umleiten; eine umbenannte `.ics` lässt bestehende Abos ins Leere laufen, ohne
dass es jemand merkt. Alte Namen gehören in das Feld `alias`, dann werden sie
weiter mitgeschrieben.

## Gestaltung

Farben vom Verein (`#DD9933` Gold, Schwarz, Warmweiß), Formensprache nach
mckinsey.de: durchgängig `border-radius: 0`, keine umrandeten Karten,
Gliederung über Weißraum und 1px-Linien, große Überschriften im leichten
Schnitt. Mobil zuerst — dort wird die Seite hauptsächlich genutzt.
Heller und dunkler Modus über `prefers-color-scheme`.

Bilder in `docs/` stammen von der Vereinsseite
(`hsg-muru-handball.de/wp-content/uploads/2023/05/`):

| Datei | Herkunft |
|---|---|
| `logo.png` | `logo_hsg_1.png` (149×200, vollständiges Wappen) – Seitenkopf |
| `icon-180.png` | aus `LOGO_2018.png` skaliert – Apple-Touch-Icon |
| `icon-32.png` | aus `LOGO_2018.png` skaliert – Favicon |

Alle mit Alphakanal, funktionieren also auf hellem wie dunklem Grund.

## Lokal ausführen

```bash
python3 spielplan2ics.py --teams teams.json --out-dir docs \
  --daten docs/daten.json --keine-schiris

for f in docs/*.ics; do python3 pruefe_ics.py "$f"; done

python3 baue_seite.py --daten docs/daten.json \
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

### Die Seite

Alle Mannschaften stehen in einer Datei; umgeschaltet wird im Browser.
Die Adresse merkt sich den Zustand: `#damen` oder `#damen/tabelle` lässt sich
teilen und öffnet direkt die richtige Ansicht. Die zuletzt gewählte Mannschaft
wird lokal gemerkt.

Gespielte Partien zeigen den Endstand — grün bei Sieg, rot bei Niederlage —
und tragen ihn auch im Kalendertitel. Die Seite ist als App installierbar
(`manifest.json`); auf iOS gibt es dafür keinen automatischen Hinweis, darum
blendet die Seite dort selbst einen Tipp ein.

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
| Tabellenstand | `GET .../api/new/standings?phase_id=12482` |
| Team suchen | `GET .../api/new/teams?name=Mutterstadt&per_page=50` |
| Spielseite im Web | `https://www.handball.net/match/<id>` |

`matches` akzeptiert außerdem `club_id`, `installation_id`, `date_from`,
`date_to`, `competition_id` und weitere Filter.

**Zur Tabelle:** `standings` liefert nicht einen Stand, sondern **einen pro
Spieltag** – 12 Mannschaften × 22 Runden = 264 Einträge. Gesucht ist die
höchste Runde, in der überhaupt gespielt wurde; vor dem ersten Anwurf also
Runde 1 mit lauter Nullen. Das Feld `position` bleibt 0, solange nichts
gespielt ist – dann bleibt die Reihenfolge der API erhalten, die der Anzeige
auf handball.net entspricht. Anders als `matches` sendet `standings` **kein
`success`-Feld**, eine Erfolgsprüfung darauf schlägt also fehl.

**Achtung bei Koordinaten:** `field.installation` (Halle) ist korrekt,
`club.latitude/longitude` (Verein) zeigt mitten in die USA.

**Team-IDs wechseln pro Saison.** Für 26/27 ist die Herren I die `80924`, in der
Vorsaison war es eine ID um 10500. Vor der Saison 27/28 also die ID im Workflow
prüfen — oder auf `--suche` umstellen.

## Rücksicht auf die Quelle

Die Daten gehören handball.net. Ein Abruf pro Tag reicht; häufigeres Pollen
bringt nichts und belastet die Seite nur.
