---
name: freigeben
description: Eine Änderung am Handball-Spielplan fertigstellen und veröffentlichen - Seiten neu bauen, Prüfkette laufen lassen, committen, rebasen (mit der richtigen Konfliktbehandlung für die erzeugten Dateien in docs/) und pushen. Verwenden, wenn eine Änderung an baue_*.py, seite_*.py, worker/ oder den Prüfskripten fertig ist und raus soll.
---

# Änderung freigeben

Der Ablauf ist immer derselbe. Der Grund für dieses Skill ist Schritt 4: An
Spieltagen pusht der Workflow alle 30 Minuten dieselben erzeugten Dateien,
ein Konflikt in `docs/` ist der Normalfall und wird jedes Mal gleich gelöst.

## 1. Bauen, was von der Änderung betroffen ist

```bash
cd ~/Projects/handball-kalender
W="https://muru-zaehler.edis-herrmann.workers.dev"
python3 baue_seite.py --daten docs/daten.json \
  --basis-url "https://beatzep.github.io/handball-kalender" \
  --worker-url "$W" --out docs/index.html
python3 baue_wochenende.py --daten docs/daten.json --out docs/wochenende.html
python3 baue_admin.py --worker-url "$W" --out docs/admin.html
```

Nur bauen, was betroffen ist. `seite_*.py` und `baue_seite.py` wirken auf
`index.html`, `baue_wochenende.py` auf `wochenende.html`, `baue_admin.py` auf
`admin.html`. Änderungen an `worker/` brauchen keinen Seitenbau.

**Nicht** `spielplan2ics.py` laufen lassen, nur um die Seite zu bauen — das
sind 23 Abfragen an handball.net. Der Workflow holt die Daten ohnehin.

## 2. Prüfkette

```bash
python3 audit.py
python3 pruefe_konflikte.py
python3 pruefe_verweise.py
python3 pruefe_tabelle.py
python3 pruefe_streng.py
for d in worker/test*.mjs; do node "$d"; done
```

Alles muss grün sein. Hinweise (`HINWEIS`) sind in Ordnung, `FEHLER` nicht.
Schlägt etwas fehl: erst beheben, nicht committen.

Wenn die Änderung eine neue Prüfung mitbringt, gehört sie in
`.github/workflows/spielplan.yml` eingehängt.

## 3. Committen

Commit-Nachricht auf Deutsch, ohne Umlaute im Betreff (der Workflow-Bot
schreibt auch so). Sie erklärt **warum**, nicht was: welcher Fall dazu
geführt hat, was die Folge war, was jetzt anders ist. Am Ende:

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

## 4. Rebasen — hier ist der Konflikt eingeplant

```bash
git fetch -q origin && git rebase origin/main
```

Kommt es zu einem Konflikt in `docs/`, **niemals mergen**. Diese Dateien sind
erzeugt, ein zusammengeführter Stand ist immer falsch:

```bash
git checkout --ours docs/ && git add docs/
```

`--ours` ist im Rebase der Stand vom Server, also die frischen Verbandsdaten.
Danach die Seiten aus Schritt 1 **neu bauen**, damit die eigene Änderung
wieder darin steckt, dann:

```bash
git add docs/ && git rebase --continue
```

Prüfen, dass keine Konfliktmarker übrig sind:

```bash
grep -l "<<<<<<<" docs/* 2>/dev/null
```

Steckt in `docs/daten.json` eine eigene Ergänzung (etwa `phase_id` oder eine
neu gerechnete Statistik), geht sie durch `--ours` verloren und muss danach
wieder eingetragen werden. Die Spielpläne selbst kommen immer vom Workflow.

## 5. Prüfkette wiederholen und pushen

Nach dem Neubau in Schritt 4 sind die Dateien andere als in Schritt 2, also
noch einmal prüfen:

```bash
python3 audit.py && python3 pruefe_verweise.py && python3 pruefe_tabelle.py
git push origin main
```

## 6. Sagen, ob ein Deploy nötig ist

| geändert | nötig |
|---|---|
| `docs/`, `baue_*.py`, `seite_*.py` | nichts, GitHub Pages baut selbst |
| `worker/index.js`, `wrangler.toml` | `npx wrangler deploy` |

Den Deploy macht Edis selbst. Wenn er nötig ist, den Befehl in einem eigenen
Codeblock dazuschreiben und sagen, was daran hängt.
