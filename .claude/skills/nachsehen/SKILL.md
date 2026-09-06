---
name: nachsehen
description: Den Zustand des Handball-Spielplans prüfen - Datenstand, Workflow-Läufe, Worker, Tipprunde, Zählung, Kalenderdateien. Verwenden, wenn etwas nicht stimmt ("die Tabelle ist alt", "es wird nichts gezählt", "das Ergebnis fehlt") oder wenn nach dem Zustand gefragt wird.
---

# Nachsehen, was los ist

Erst messen, dann urteilen. Die drei ernsten Fehler bisher waren alle
unsichtbar: ein HTTP 400 hinter „Anfrage fehlerhaft", eine Zählung, die
Erfolg meldete ohne anzukommen, ein Cache, der nie im Repository lag. Nichts
davon war zu erraten, alles war zu messen.

Nur ausführen, was zur Frage passt.

## Datenstand und Workflow

```bash
curl -s "https://beatzep.github.io/handball-kalender/daten.json" | python3 -c "
import json,sys
from datetime import datetime,timezone
d=json.load(sys.stdin); t=datetime.fromisoformat(d['aktualisiert'])
print(f'Stand {t.astimezone():%d.%m. %H:%M} lokal, {(datetime.now(timezone.utc)-t).total_seconds()/60:.0f} Min alt')"

curl -s "https://api.github.com/repos/beatzep/handball-kalender/actions/workflows/spielplan.yml/runs?per_page=5" | python3 -c "
import json,sys
from datetime import datetime
for r in json.load(sys.stdin)['workflow_runs'][:5]:
    t=datetime.fromisoformat(r['created_at'].replace('Z','+00:00')).astimezone()
    print(f\"  {t:%d.%m. %H:%M}  {r['event']:18s} {r['conclusion']}\")"
```

`event` sagt, wer ausgelöst hat: `schedule` ist GitHubs eigener Zeitplan
(unzuverlässig, verschiebt sich um Stunden), `repository_dispatch` kommt vom
Cloudflare-Worker, `workflow_dispatch` war ein Handstart.

**Zeitplan:** GitHub stündlich um :05 UTC an Wochenenden (14:05 bis 00:05
lokal) plus nachts um 03:17 UTC. Der Worker prüft samstags und sonntags alle
15 Minuten und stößt an, wenn die Daten über 25 Minuten alt sind. Also etwa
alle 30 Minuten ein Lauf, solange gespielt wird.

Ein Handstart geht über *Actions → Spielplan aktualisieren → Run workflow*.

## Worker: läuft er, was entscheidet er?

```bash
W="https://muru-zaehler.edis-herrmann.workers.dev"
curl -s -o /dev/null -w "/stand       %{http_code}\n" "$W/stand?spiel=2627RPBKROERMA0101"
curl -s "$W/tipptabelle?mannschaft=herren1" | head -c 300
```

Antwortet etwas mit 400, steht der Grund im Feld `grund` — der wird seit dem
`list()`-Vorfall im Klartext durchgereicht.

Live mitlesen (zeigt auch die Cron-Entscheidungen):

```bash
npx wrangler tail
```

## Zählung

Sie geht **erst beim Verlassen der Seite** raus, über `sendBeacon` mit
Inhaltstyp `text/plain`. Mit `application/json` käme sie nie an (CORS-
Vorfrage verbraucht die letzte Zustellung). Tageswerte liegen auf zehn
Schlüssel verteilt:

```bash
python3 - <<'EOF'
import subprocess, json, datetime
heute = datetime.date.today().isoformat()
gesamt = {"ereignis": {}, "mannschaft": {}, "bereich": {}}
for i in range(10):
    r = subprocess.run(["npx","wrangler","kv","key","get",f"stat:{heute}:{i}",
                        "--namespace-id=9cdf5b8b1e044059909e7af519b2802a","--remote"],
                       capture_output=True, text=True)
    try: d = json.loads(r.stdout.strip())
    except Exception: continue
    for g in gesamt:
        for k, v in (d.get(g) or {}).items():
            gesamt[g][k] = gesamt[g].get(k, 0) + v
for g, w in gesamt.items():
    if w: print(f"{g}: {json.dumps(w, ensure_ascii=False)}")
EOF
```

KV ist nicht sofort konsistent: nach einem Schreibvorgang bis zu einer Minute
warten, bevor man ihn lesen kann.

## Tipprunde

```bash
curl -s "$W/tipptabelle" | python3 -m json.tool | head -30
```

Steht `unvollstaendig` mit `imAufbau` dabei, wurde die Tipperliste noch nicht
gegen den Speicher abgeglichen — sie enthält dann nur, wer seitdem getippt
hat. Das löst sich beim nächsten möglichen `list()` von selbst.

Aufräumen (beanstandete Namen entfernen) geht über `/admin`.

## Tabelle hinkt hinterher

Normalfall, kein Fehler: Der Verband trägt Ergebnisse sofort ein, die Tabelle
ein bis zwei Tage später. Prüfen, ob der Hinweis dazu stimmt:

```bash
python3 pruefe_tabelle.py
```

Verglichen wird nur innerhalb desselben Wettbewerbs — Pokal- und
Qualifikationsspiele zählen nicht in die Ligatabelle.

## Kalenderdateien

```bash
for d in $(ls docs/*.ics | xargs -n1 basename); do
  c=$(curl -s -o /tmp/k.ics -w "%{http_code}" "https://beatzep.github.io/handball-kalender/$d")
  n=$(grep -c BEGIN:VEVENT /tmp/k.ics)
  [ "$c" = "200" ] && [ "$n" -gt 0 ] || echo "PROBLEM $d: HTTP $c, $n Termine"
done; echo "geprüft"
```

## Wenn nichts davon etwas zeigt

Dann ist der Fehler nicht im Betrieb, sondern in den Daten oder im Code.
`python3 pruefe_gegen_quelle.py` gleicht alle Spiele unabhängig vom Generator
gegen handball.net ab — das ist der ehrlichste Test, kostet aber 23 Abfragen
an der Quelle, also nicht beiläufig laufen lassen.
