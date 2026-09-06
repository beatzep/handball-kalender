# handball-kalender

Spielpläne der HSG Mutterstadt/Ruchheim als abonnierbare Kalender und als
Website. 23 Mannschaften, rund 340 Spiele, Daten von handball.net. Die
Hintergründe und alle Fallstricke der Verbandsdaten stehen im README, das
hier ist nur das Nötigste für die tägliche Arbeit.

## Das Wichtigste zuerst

**Die Daten müssen stimmen.** Leute verlassen sich auf diese Seite und
tragen ihre Termine danach ein. Lieber ein ehrlicher Hinweis („noch nicht
eingerechnet") als eine Zahl, die plausibel aussieht und falsch ist. Wo die
Quelle Unsinn liefert, wird das abgefangen und dokumentiert, nicht
weitergereicht.

## `docs/` ist erzeugt, nicht bearbeitet

Alles in `docs/` entsteht aus den Bau-Skripten. Nie von Hand ändern, auch
nicht „schnell". Wer einen Text ändern will, ändert ihn in `baue_seite.py`,
`baue_wochenende.py` oder `baue_admin.py` und baut neu.

**Beim Rebase-Konflikt in `docs/` niemals mergen.** Der Workflow pusht an
Spieltagen alle 30 Minuten dieselben Dateien, Konflikte sind der Normalfall:

```bash
git checkout --ours docs/ && git add docs/    # frische Daten übernehmen
# dann neu bauen (siehe unten), git add docs/, git rebase --continue
```

Bei einem Konflikt in `docs/daten.json` gilt: Spielpläne und Tabellen kommen
vom Workflow, eigene Ergänzungen (etwa `phase_id`) danach wieder eintragen.

## Bauen

```bash
W="https://muru-zaehler.edis-herrmann.workers.dev"
python3 baue_seite.py --daten docs/daten.json \
  --basis-url "https://beatzep.github.io/handball-kalender" \
  --worker-url "$W" --out docs/index.html
python3 baue_wochenende.py --daten docs/daten.json --out docs/wochenende.html
python3 baue_admin.py --worker-url "$W" --out docs/admin.html
```

`spielplan2ics.py` befragt handball.net und schreibt `daten.json` und die
`.ics`-Dateien. Nur laufen lassen, wenn es wirklich um frische Verbandsdaten
geht — der Workflow macht das ohnehin. **Rücksicht auf die Quelle:** ein Lauf
sind rund 23 Abfragen.

## Spielberichte

`spielberichte.py` holt zu jedem gelaufenen Spiel der Aktiven den Verlauf
(`/matches/<id>/events`) und legt ihn in `berichte_cache.json` ab. **Ein
Bericht ändert sich nach dem Spiel nicht mehr**, wird also genau einmal
geholt. Nicht jede Liga führt einen: bei mB und gD kommt eine leere Antwort,
das wird vermerkt und nicht erneut versucht.

Grundregel für alles, was daraus entsteht: **Fehlt etwas, liegt es an der
Quelle, und das gehört auch so dagesagt.** Nie eine Lücke zeigen, die
aussieht, als wäre die Seite unfertig — sondern benennen, dass handball.net
für dieses Spiel noch nichts veröffentlicht hat.

Spielernamen erscheinen voll nur bei den Aktiven. Bei der Jugend nur Vorname
und erster Buchstabe des Nachnamens (`Lisa M.`).

## Vor jedem Commit

```bash
python3 audit.py              # Daten und Seite
python3 pruefe_konflikte.py   # Datenblock von "Meine Mannschaften"
python3 pruefe_verweise.py    # Verweise zwischen den Seiten
python3 pruefe_tabelle.py     # Rückstand der Verbandstabelle
python3 pruefe_berichte.py    # Spielberichte gegen die Endstände
python3 pruefe_streng.py      # RFC-Prüfung der .ics-Dateien
for d in worker/test*.mjs; do node "$d"; done
```

Läuft alles auch im Workflow. Eine neue Prüfung gehört dort eingehängt.

## Wann muss der Worker deployt werden?

| geändert | nötig |
|---|---|
| `docs/`, `baue_*.py`, `seite_*.py` | nur `git push`, GitHub Pages baut selbst |
| `worker/index.js`, `wrangler.toml` | `npx wrangler deploy` |
| Secrets | `npx wrangler secret put NAME`, sofort aktiv |

Am Ende einer Änderung immer dazusagen, ob ein Deploy nötig ist. Deploys
macht Edis selbst.

## Fallen, die schon zugeschnappt sind

- **Python 3.12 im Workflow**, lokal ist 3.14 installiert. Nichts benutzen,
  was neuer ist (`Path.read_text(newline=)` etwa gibt es erst ab 3.13).
  Zum Prüfen: `/opt/homebrew/bin/python3.12`.
- **CSS-Escapes in Python-Strings.** `content: "\2039"` liest Python als
  Oktalzahl. Sonderzeichen direkt schreiben: `‹`, `☆`, `★`.
- **Teilstring-Prüfungen.** `if "hashchange" not in seite` trifft auch auf
  `hashchangeX` zu und schlägt dann nicht an. Auf den Aufruf prüfen, nicht
  auf den Namen.
- **Umlaute und `.upper()`.** `"ß".upper()` ist `"SS"`, ein Vergleich
  `text == text.upper()` scheitert daran.
- **`0:0` ist im Handball kein Ergebnis**, sondern „keine Wertung geführt".

## Ton

Edis schreibt die Texte der Seite mit, sein Ton hat Vorrang. Wenn dort etwas
geändert wurde, nicht zurückdrehen.

Locker und ehrlich, wie im Verein geredet wird. Keine Marketingsprache, keine
Gedankenstriche als Stilmittel, keine Aufzählungen, die klingen wie ein
Produktprospekt. Lieber „Der Verband trägt die Tabelle später nach" als
„Die Datensynchronisation erfolgt zeitversetzt".

Kommentare im Code erklären, **warum** etwas so ist, meist mit dem konkreten
Fall, der dazu geführt hat. Nicht was die Zeile tut.
