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

## Abgleich gegen die Quelle

`pruefe_gegen_quelle.py` ist das wichtigste Prüfwerkzeug: Es fragt handball.net
**frisch** ab und liest die **fertigen** `.ics`-Dateien – beide Seiten also
getrennt ermittelt. Ein Fehler in der Verarbeitung fällt hier auf, weil nichts
aus derselben Quelle im Speicher stammt.

Geprüft wird je Spiel: Vollständigkeit (keins fehlt, keins zu viel), Datum und
Uhrzeit auf die Sekunde, Gegner im Titel, Halle in der Ortsangabe, Endstand.

Der Lauf hängt im Workflow **hinter** dem Bauen. Schlägt er an, wird nicht
committet – die bisherigen, korrekten Dateien bleiben stehen. Lieber ein Tag
alte richtige Daten als neue falsche. Er läuft nur nachts; die stündlichen
Läufe am Wochenende würden die Abfragen sonst verdoppeln.

Gegen absichtlich beschädigte Kalender geprüft: verschobene Uhrzeit, fehlender
Termin, falscher Gegner und Tagestermin trotz Anwurfzeit werden alle gefunden.

**Ergebnisse stehen aus Sicht der jeweiligen Mannschaft** (`eigene:fremde`),
nicht als Heim:Gast. In der Zeile steht nur der Gegner – „30:20" rot neben
einem Auswärtsspiel läse sich sonst, als hätten wir 30 geworfen.

## Alle Mannschaften und die Wochenend-Übersicht

`teams.json` führt 23 Mannschaften: drei aktive und zwanzig Jugendteams.
Aufgenommen wird nur, wer in der laufenden Saison einen Spielplan hat – von
42 beim Verband gemeldeten Teams trifft das auf 23 zu.

`baue_wochenende.py` erzeugt `docs/wochenende.html`: alle Spiele aller
Mannschaften der nächsten zwei Wochen, nach Tag gruppiert, mit Filter auf
Heimspiele. Gedacht für Zuschauer und Eltern, nicht für Abonnenten.

Im Dropdown lassen sich Mannschaften **anheften** – sie rutschen dann in eine
eigene Gruppe nach oben. Bei 23 Einträgen sucht sich sonst jeder tot.

Drei Eigenheiten der Verbandsdaten, die dabei zutage traten:

- **Mannschaften spielen Liga *und* Pokal.** Die Phase des ersten Spiels zu
  nehmen liefert dann zufällig die Pokalgruppe – bei vier Jugendteams stand
  so die falsche Liga und eine Tabelle mit drei statt zehn Mannschaften.
  Maßgeblich ist die Phase mit den **meisten** Spielen.
- **Nicht jeder Wettbewerb wird gewertet.** Minis haben `has_standings=false`;
  die dortige Liste mit 50 Mannschaften ist eine Sammelliste, keine Tabelle.
- **Der Tabellenstand steht in jeder Runde.** Die API legt den aktuellen
  Stand nicht nur in die gespielte Runde, sondern in alle 18 (oder 22) der
  Saison. Wer die höchste Runde mit Einträgen nimmt, landet am ersten
  Spieltag bei „Stand nach Spieltag 18" und zeichnet einen Platzverlauf über
  eine halbe Saison, die nie stattgefunden hat. Maßgeblich ist deshalb die
  Zahl der tatsächlich absolvierten Spiele (`played`), nicht der Rundenindex.
- **0:0 ist kein Ergebnis.** In der F-Jugend und bei den Minis wird ohne
  Ergebniszählung gespielt; der Verband markiert die Partien trotzdem als
  beendet (`is_finished`) und lässt `0:0` stehen. Im Kalender wäre das ein
  torloses Remis, das es im Handball nicht gibt. Ein 0:20 (nicht angetreten)
  bleibt dagegen ein Ergebnis.
- **Turnierspiele haben keine Anwurfzeit** (00:00 beim Verband). Sie werden
  als ganztägige Termine geschrieben, ohne Erinnerung – ein Eintrag um
  Mitternacht wäre schlicht falsch. Betroffen sind 12 von 338 Spielen.

Mehrere Spiele zur selben Zeit sind bei Spielfesten normal; der Audit meldet
sie nur, wenn sie in **verschiedenen Hallen** stattfinden sollen.

## Von einem Spiel zur Mannschaft

Auf der Wochenend-Übersicht steht ein Ergebnis, und man will mehr über die
Mannschaft wissen – bisher hieß das: zurück und aus 23 Einträgen neu wählen.
Jetzt führt jede Zeile direkt auf `index.html#<mannschaft>`.

Zwei Dinge waren dabei zu lösen:

- **Die Halle ist bereits ein Link** zur Karte, und Links lassen sich in HTML
  nicht ineinander schachteln. Deshalb liegt der Link im Mannschaftsnamen und
  wird per `::after { inset: 0 }` über die ganze Zeile gezogen; der Hallenlink
  bekommt `z-index: 1` und bleibt einzeln antippbar. Auf dem Handy will
  niemand einen kleinen Namen treffen müssen.
- **Die Seite las die Adresse nur beim Laden.** Ein Verweis auf `#mb` aus
  „Meine Mannschaften" heraus änderte nur den Anker und bewirkte nichts – der
  gleiche Fall wie bei einem geteilten Link, den der Empfänger in einem schon
  offenen Tab anklickt. Ein `hashchange`-Empfänger behebt beides.

`pruefe_verweise.py` stellt sicher, dass jeder Verweis bei einer Mannschaft
ankommt, dass keine Zeile ohne Weg dasteht und dass der Rückweg existiert.
Ein Tippfehler im Schlüssel fiele sonst niemandem auf: die Seite zeigt dann
stumm die erste Mannschaft, statt einen Fehler zu melden.

## Meine Mannschaften

Wer zwei Kinder im Verein hat oder selbst in zwei Altersklassen spielt, hält
sonst zwei Spielpläne nebeneinander. Ab **zwei angehefteten** Mannschaften
erscheint im Dropdown der Eintrag *Meine Mannschaften*: beide Spielpläne in
einer chronologischen Liste, jede Zeile mit dem Mannschaftskürzel.

Der interessante Teil sind die Terminkollisionen. Geprüft wird jedes Paar von
Spielen am selben Tag:

- **Überschneidung** – das zweite wirft an, bevor das erste abgepfiffen ist
  (gerechnet mit 105 Minuten Spieldauer inklusive Pause).
- **Fahrzeit reicht nicht** – zwischen Abpfiff und Anwurf liegen weniger
  Minuten, als die Strecke zwischen den Hallen braucht. Die Entfernung kommt
  aus denselben Koordinaten wie der Kilometerzähler (Luftlinie mal 1,3, 70
  km/h, plus 10 Minuten fürs Parken).
- **Knapp** – es geht aus, aber ohne Umweg (weniger als 30 Minuten Luft).

Zwei Fälle sind bewusst *keine* Kollision: zwei Spiele derselben Mannschaft an
einem Tag (Turniertag) und zwei Spiele **in derselben Halle** nacheinander –
das ist der normale Doppelspieltag, man bleibt einfach sitzen. Ohne diese
zweite Regel meldete die Ansicht für Herren I und II vierzehn Konflikte statt
sechs, und die Warnung wäre wertlos geworden.

Die Ansicht rechnet im Browser, aus einem eigenen kompakten Datenblock im
Dokument (`<script id="spieldaten">`, rund 70 kB für 338 Spiele). Weil dieser
Block von den Spielplänen abweichen könnte, ohne dass es jemandem auffällt,
prüft `pruefe_konflikte.py` ihn Feld für Feld gegen `docs/daten.json` und
rechnet die Konfliktlogik ein zweites Mal in Python nach. Beide
Implementierungen kamen über alle 253 Mannschaftspaare auf dasselbe Ergebnis
(193 Paare mit Konflikt, 571 Kollisionen).

Bei weniger als zwei angehefteten Mannschaften steht unter der Auswahl ein
Hinweis – ohne ihn findet niemand die Funktion, denn *Anheften* klingt nach
Lesezeichen.

## Auswertung der Nutzung

`docs/admin.html` zeigt Aufrufe, Aktionen und Verteilung nach Mannschaft und
Bereich. Die Seite liegt offen im Verzeichnis und ist ohne Anmeldung leer –
die Zahlen gibt der Worker nur gegen Benutzer und Passwort heraus, die dort
als Secrets liegen (`wrangler secret put ADMIN_BENUTZER` / `ADMIN_PASSWORT`).

Ein Passwort, das die Seite selbst prüft, wäre wertlos: Auf GitHub Pages
steht jeder Prüfcode im Quelltext. Deshalb liegt die Prüfung im Worker.

**Gezählt wird aggregiert.** Summen je Tag: Aufrufe, gewählte Mannschaft,
geöffneter Bereich, geklickte Aktionen. Keine Kennung, keine Adresse, keine
Wiedererkennung, kein Zeitstempel je Besuch – damit braucht es weder Banner
noch Einwilligung. Die Gerätekennung aus Tipprunde und Zusagen wird dafür
bewusst **nicht** verwendet; sie ist zweckgebunden.

**Die Grenzen des kostenlosen Speichers bestimmen das Design.** Erlaubt sind
rund 1.000 Schreibvorgänge am Tag und nur einer je Sekunde auf denselben
Schlüssel. Daraus folgt:

- Ein Besuch meldet sich **einmal**, gebündelt beim Verlassen. Ein Aufruf je
  Klick wäre das Tageskontingent an einem Spieltag.
- Die Tageszähler liegen auf zehn Schlüsseln, zufällig gewählt, und werden
  beim Auswerten wieder zusammengezählt. Sonst gingen gleichzeitige Zugriffe
  verloren.
- Der Hype-Zähler bündelt Klicks über dreißig Sekunden. Die Anzeige läuft
  ohnehin sofort mit, nur der Abgleich hinkt nach.

Überschlag für einen großen Spieltag mit 23 Mannschaften: 300 Seitenaufrufe,
30 Hype-Klicker, 60 Zusagen, 50 Tipps ergeben rund **440 Schreibvorgänge** –
gut 44 % des Kontingents. Ohne die Bündelung wären es 770 gewesen.

Wird das Limit doch erreicht, fällt nichts aus: Die Seite funktioniert weiter,
Anzeigen laufen optimistisch mit, nur Zählungen gehen verloren. Sollte es
dauerhaft eng werden, hebt der kostenpflichtige Tarif (rund 5 $ im Monat) die
Grenze auf eine Million Schreibvorgänge – deutlich billiger, als Funktionen
wegzunehmen.

Gelesen wird nebenläufig: 30 Tage × 10 Schlüssel nacheinander brauchten
1,3 Sekunden, parallel sind es rund 0,5.

## Tipprunde

Vor jedem Spiel kann getippt werden, nach dem Abpfiff rechnet der Worker die
Punkte aus. Endpunkte: `/tipp`, `/tipper`, `/tipptabelle`.

| Treffer | Punkte |
|---|---|
| Exaktes Ergebnis | 10 |
| Richtige Tordifferenz | 5 |
| Richtige Tendenz | 3 |

**Jede Mannschaft hat ihre eigene Wertung.** Die Tabelle wird mit
`?mannschaft=<schluessel>` abgerufen; ohne Angabe wären es alle Spiele des
Vereins, und wer viele Mannschaften tippt, hätte automatisch mehr Punkte.

**Identität ohne Anmeldung.** Jedes Gerät bekommt eine zufällige Kennung im
Browser (dieselbe wie für die Zusagen). Punkte stapeln sich serverseitig
unter dieser Kennung. Wer das Gerät wechselt oder seine Browserdaten löscht,
nimmt sie über den Umzugslink `?tipper=<kennung>` mit – faktisch ein Login
ohne Konto und ohne Passwort. Ohne Namen taucht niemand in der Tabelle auf.

Das verhindert **nicht**, dass sich jemand mit einem zweiten Browser eine
zweite Identität anlegt. Bei einer Mannschaft ist das dasselbe
Vertrauensverhältnis wie bei den Zusagen.

**Der Worker kennt Termine und Ergebnisse**, indem er `daten.json` von der
eigenen Seite liest (eine Stunde zwischengespeichert). Dadurch braucht es
kein Zugriffstoken und keine zweite Datenhaltung: Die Tippsperre ab Anwurf
und die Punkteberechnung stützen sich auf dieselbe Datei wie die Seite.

Zwei Fallstricke, die dabei gelöst sind:

- **Zeitzonen im Worker.** Anwurfzeiten stehen ohne Zeitzone in den Daten und
  sind als Ortszeit gemeint; Worker laufen in UTC. Der Versatz wird bei der
  Zeitzonendatenbank erfragt statt über Monatsgrenzen geraten – sonst wäre
  die Nacht der Zeitumstellung eine Stunde falsch.
- **Verzögerte Auflistung im Speicher.** Neu angelegte Einträge erscheinen in
  `list()` erst nach einiger Zeit. Wer gerade getippt hat, sähe sich sonst
  minutenlang nicht in der Tabelle – deshalb trägt die Seite die eigene Zeile
  vorläufig selbst ein, mit „–" als Platz.

## Bilder zum Teilen

`seite_grafik.py` enthält den Zeichner, der im Browser auf ein Canvas malt:
Wappen, Gegner, Anwurf, Halle, Countdown – beziehungsweise Endstand und
Ausgang. Zwei Formate (1080×1920 für Stories, 1080×1080 für Beiträge).

Alles entsteht **auf dem Gerät des Nutzers** aus den Spieldaten. Kein
Bildmaterial von außen, kein Upload, keine erzeugten Bilder – nur Text,
Wappen und Farbflächen.

Zwei Dinge, die beim Bauen schiefgingen und jetzt gelöst sind:

- **Textbaseline.** Mit der Voreinstellung `alphabetic` ragen große
  Schriften nach oben in die Zeile darüber; „Auswärts bei" überlappte den
  Gegnernamen. Alles hängt jetzt an `textBaseline: top`.
- **Senkrechte Lage.** Der Block wird erst unsichtbar ausgemessen und dann
  mittig gesetzt, sonst klebt der Inhalt oben und unten bleibt eine große
  Leerfläche.

Geteilt wird über die Web-Share-Schnittstelle, wenn das Gerät sie für
Dateien anbietet – sonst lädt die Datei herunter.

## Statistik

`statistik.py` leitet aus den Spieldaten Kennzahlen ab, die handball.net so
nicht ausweist – Fahrten, Bilanz nach Heim und Auswärts, Serien, Krimi-Quote,
Bilanz nach Anwurfzeit, Gegnerbilanzen.

Entfernungen sind **geschätzt**: Luftlinie zwischen den Hallenkoordinaten,
mal 1,3 für Umwege, Fahrzeit bei 70 km/h. Ausgangspunkt ist `heimat` in
`teams.json`.

**Koordinaten werden geprüft.** Der Verband trägt bei einzelnen Hallen `0/0`
ein – der Nullpunkt im Atlantik. Ungeprüft übernommen ergäbe das
Fahrtstrecken von 7.000 km und schickte die Navigation vor Afrika. Nur
Koordinaten innerhalb Deutschlands werden verwendet, betroffene Hallen
weist die Seite offen aus.

Der Verbrauchs-Gag für Herren I rechnet aus `alltag` in `teams.json`
(Trainings pro Woche, Bier je Training und Spiel, Zeiten vor und nach dem
Spiel). Alle Werte dort anpassbar – die Seite zeigt die Rechnung offen an,
damit niemand raten muss, wo die Zahl herkommt.

Gegnerbilanzen erscheinen erst, wenn gegen jemanden **zweimal** gespielt
wurde; nach einem einzelnen Spiel wäre „liebster Gegner" nur ein Ergebnis.

## Zähler (Hype und Zusagen)

Optional. Ein Cloudflare Worker mit KV-Speicher hält zwei Zahlen je Spiel:

| Schlüssel | Inhalt |
|---|---|
| `hype:<spielnummer>` | Klickzähler als Zahl |
| `dabei:<spielnummer>` | Liste anonymer Gerätekennungen, Länge = Zusagen |

Der Worker liegt in `worker/index.js`, die Konfiguration in `wrangler.toml`.

```bash
npx wrangler login     # einmalig
npx wrangler deploy    # bei jeder Änderung am Worker
node worker/test.mjs   # Logik gegen simuliertes KV prüfen
```

### Der Worker als Sicherheitsnetz für den Workflow

GitHub verschiebt geplante Läufe bei Last und lässt sie auch ganz ausfallen.
Am 29.08.2026 fielen die Läufe um 14:05 und 15:05 aus, der letzte war von
12:01 – Ergebnisse standen dadurch stundenlang nicht auf der Seite, obwohl
stündlich geprüft werden sollte. Ein Handstart über den Actions-Tab half,
aber darauf ist kein Verlass.

Cloudflare hält seine Cron-Zeiten dagegen ein. Der Worker schaut zu denselben
Zeiten nach und stößt den Workflow per `repository_dispatch` an, wenn drei
Dinge zusammenkommen:

1. `daten.json` ist älter als 25 Minuten – GitHub hat also nicht geliefert,
2. in den letzten sechs Stunden wurde gespielt – es gibt etwas zu holen,
3. oder die Daten sind älter als 25 Stunden – dann ist der nächtliche Lauf
   ausgefallen und Verlegungen müssen ankommen, auch ohne Spiel.

Nachgeschaut wird am Wochenende **alle 15 Minuten**; das Nachschauen selbst
ist ein Abruf von `daten.json` und kostet nichts. Angestoßen wird höchstens
alle 25 Minuten – diese Schwelle begrenzt, wie oft der Workflow überhaupt
laufen kann, egal wie eng der Cron getaktet ist. Sie ist die Rücksicht auf
handball.net, das bei jedem Lauf 23 Mannschaften beantworten muss: rund 1.100
Abfragen an einem Spieltag, an dem GitHub komplett ausfällt, statt 500.

Praktisch heißt das: Endet ein Spiel um 21:45 und der Verband trägt um 21:50
ein, steht das Ergebnis gegen 22:02 auf der Seite statt erst nach 23:00.

Läuft bei GitHub alles normal, passiert nichts – es gibt keine doppelten
Läufe. Die zweite Bedingung hält den Worker unter der Woche still, ohne dass
es auf den Cron-Ausdruck ankommt. Das ist kein Luxus: Cloudflare hat
`5 12-22 * * 6,0` als ungültig abgewiesen, weil sein Parser den Sonntag
anders als GitHub nicht als `0` zählt. Mit `SAT,SUN` läuft es, aber die
Entscheidung soll nicht an solchen Stolperstellen hängen.

Dafür braucht der Worker einen GitHub-Token:

```bash
npx wrangler secret put GITHUB_TOKEN
```

Ein **Fine-grained Token** genügt, beschränkt auf dieses eine Repository, mit
der einen Berechtigung **Contents: Read and write**. Mehr braucht er nicht, und
mehr sollte er nicht haben.

Nicht „Actions", auch wenn der Anstoß einen Workflow startet: `repository_dispatch`
hängt bei GitHub an den Repository-Inhalten. Mit einem Actions-Token antwortet
die API mit `403 Resource not accessible by personal access token` – der Worker
protokolliert das im Klartext, sichtbar über `npx wrangler tail`. Ohne Token protokolliert der Worker das und tut
nichts – die geplanten Läufe von GitHub greifen dann wie bisher.

`node worker/test_cron.mjs` prüft die Entscheidung: frische Daten lösen nichts
aus, alte schon, ein abgelehnter Anstoß bringt den Worker nicht um.

Die Seite bekommt die Adresse über `--worker-url`. **Ohne diese Angabe
entfällt der Block ersatzlos** — und ist der Worker nicht erreichbar,
blendet die Seite ihn aus, statt einen toten Knopf zu zeigen.

Weil die Zähler an die Spielnummer hängen, fangen sie vor jedem Spiel bei
null an; der Stand des letzten Spiels bleibt als Vergleich stehen.

### Was am 29.08.2026 die Tipptabelle lahmgelegt hat

Die Tabelle war tot und niemand konnte es sehen. Drei Fehler übereinander:

1. **Die Seite lud 24 Tabellen auf einmal.** Alle 23 Mannschaften stehen im
   Dokument, sichtbar ist immer nur eine – trotzdem holte jeder Block beim
   Laden seine Daten. Jeder Abruf brauchte ein `list()`, und davon erlaubt
   der kostenlose Tarif **1.000 am Tag**. Nach gut vierzig Besuchern war die
   Tipprunde bis Mitternacht UTC tot, jeden Tag aufs Neue.
2. **Der Worker verschluckte den Grund.** Jede Ausnahme wurde zu
   `"Anfrage fehlerhaft"` ohne weitere Angabe. Erst als der `catch` die
   Meldung durchreichte, stand da `KV list() limit exceeded for the day.`
3. **Die Seite verschluckte den Fehler.** Bei einem Fehlschlag setzte sie
   `tabelle.innerHTML = ''` – keine Tabelle, kein Hinweis. Es sah aus, als
   hätte einfach noch niemand getippt.

Behoben ohne jede Änderung am Speicherschema:

- Blöcke melden sich über `window.muruBeiAnzeige` an und laden erst, wenn
  ihre Mannschaft angezeigt wird. Von 46 Abrufen pro Seitenaufruf auf 2.
- Der eigene Tippstand wird einmal für die ganze Seite geholt statt 24-mal
  unter derselben Adresse.
- Wer getippt hat, steht zusätzlich in `tipper-index`. Der Lesepfad braucht
  damit **kein** `list()` mehr; die Liste wird alle sechs Stunden aus dem
  Speicher aufgefrischt und wächst bei jedem neuen Tipp mit. Maßgeblich
  bleiben die Einträge `tipper:<id>` – die Liste ist nur eine Abkürzung.
- Schlägt das Auffrischen fehl, wird eine Stunde lang nicht erneut
  angerannt und die ältere Liste weiterverwendet.
- Ein einzelner unbrauchbarer Eintrag kippt nicht mehr die Wertung aller
  anderen, und abweichend gespeicherte Tipps werden gedeutet statt
  verworfen (`alsTipp`).

`worker/test_tipp.mjs` deckt das ab, einschließlich der Lage vom 29.08.:
kein Index und kein `list()` möglich – wer dann tippt, muss trotzdem in der
Tabelle erscheinen, und sobald das Kontingent wieder da ist, kommen die
Älteren dazu. Ein Test belegt, dass die Tabelle keinen gespeicherten Tipp
verändert.

**Bekannte Grenzen, bewusst in Kauf genommen:**

- Klicks werden im Browser gesammelt und alle zwei Sekunden gebündelt
  gesendet. Ohne das wäre das Tageskontingent an einem Spieltag aufgebraucht.
- KV verträgt rund einen Schreibvorgang pro Sekunde und Schlüssel. Klicken
  zwanzig Leute gleichzeitig, können einzelne Zählungen verlorengehen. Für
  einen Stimmungszähler ist das verschmerzbar.
- Gegen ein Skript, das gezielt hochzählt, schützt nur die Obergrenze von 25
  pro Anfrage. Vollständig verhindern lässt es sich ohne Anmeldung nicht.
- Die Zusagen zählen **Geräte**, nicht Personen: zwei Geräte sind zwei
  Stimmen, gelöschte Browserdaten kosten eine. Als Anhaltspunkt gedacht,
  nicht als Anwesenheitsliste.

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
