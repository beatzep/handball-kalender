"""Hinweis, wenn der Abgleich mit handball.net haengt.

Vom 24. bis 26.09.2026 ist jeder Lauf am Audit gescheitert. Die Seite blieb
drei Tage auf dem alten Stand, samt einem Spiel der gE-Jugend II, das
laengst auf Ende Oktober verlegt war. Zu sehen war davon nur die Zeile ganz
unten im Fuss. Schon am 10.09. war ein Lauf gescheitert, ohne dass es einer
gemerkt hat.

Gerechnet wird im Browser: Scheitert der Lauf, wird die Seite ja gerade
nicht neu gebaut. Und der Hinweis steht von Haus aus drin. Das Skript
blendet ihn nur aus, wenn es sicher weiss, dass der Stand frisch ist. Laeuft
es nicht oder kommt es ins Stolpern, bleibt er stehen. Ein Hinweis zu viel
ist hier besser als einer zu wenig.
"""

from __future__ import annotations

import html
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")

# Die Grenzen sind an den Laeufen vom 22.08. bis 23.09.2026 gemessen.
# Unter der Woche lagen zwischen zwei Laeufen hoechstens 25,0 Stunden
# (GitHub startet den Lauf von 03:17 meist erst gegen 08:00 UTC). Am
# Wochenende laeuft er ab 12:05 UTC stuendlich, ab 14 Uhr UTC war der Stand
# nie aelter als 2,7 Stunden. Mit diesen Grenzen haette es in den fuenf
# Wochen genau einmal angeschlagen: am 10./11.09., als der Lauf wirklich
# gescheitert war. Gerechnet wird in UTC, weil auch der Zeitplan in UTC
# steht; die Zeitumstellung verschiebt nichts.
PRUEFUNG = """
function muruVeraltet(standIso, jetzt) {
  var stand = Date.parse(standIso);
  if (!isFinite(stand)) return { grund: 'unbekannt' };
  var stunden = (jetzt - stand) / 3600000;
  // Ein Stand aus der Zukunft heisst: die Uhr des Geraets geht falsch.
  // Dann laesst sich nichts sagen, also auch nicht Entwarnung geben.
  if (stunden < -0.25) return { grund: 'uhr', stand: stand };
  var d = new Date(jetzt);
  var wochenende = d.getUTCDay() === 6 || d.getUTCDay() === 0;
  var grenze = (wochenende && d.getUTCHours() >= 14) ? 3 : 25.5;
  if (stunden <= grenze) return null;
  return { grund: 'alt', stand: stand, stunden: stunden };
}

function muruStandText(befund) {
  if (befund.grund === 'unbekannt') {
    return 'Wann der Spielplan zuletzt mit handball.net abgeglichen wurde, '
         + 'lässt sich gerade nicht sagen.';
  }
  var d = new Date(befund.stand);
  var wann = d.toLocaleDateString('de-DE', { timeZone: 'Europe/Berlin',
      weekday: 'long', day: '2-digit', month: '2-digit' })
    + ', um ' + d.toLocaleTimeString('de-DE', { timeZone: 'Europe/Berlin',
      hour: '2-digit', minute: '2-digit' });
  if (befund.grund === 'uhr') {
    return 'Der letzte Abgleich mit handball.net war am ' + wann + ' Uhr. '
         + 'Ob das aktuell ist, lässt sich nicht sagen, die Uhr dieses Geräts '
         + 'scheint falsch zu gehen.';
  }
  var h = Math.floor(befund.stunden);
  var vor = h < 48 ? 'vor ' + h + ' Stunden' : 'vor ' + Math.floor(h / 24) + ' Tagen';
  return 'Der letzte Abgleich mit handball.net war am ' + wann + ' Uhr, '
       + 'also ' + vor + '. Normalerweise passiert das jeden Tag, an '
       + 'Spieltagen jede Stunde. Verlegungen und Ergebnisse seitdem stehen '
       + 'hier und in den abonnierten Kalendern womöglich noch nicht drin.';
}
"""

# Direkt hinter dem Hinweis, nicht im grossen Skript am Seitenende: so
# laeuft es, bevor etwas zu sehen ist, und ein Fehler anderswo nimmt es
# nicht mit.
AUSFUEHREN = """
(function () {
  var el = document.getElementById('veraltet');
  try {
    var befund = muruVeraltet(el.getAttribute('data-stand'), Date.now());
    if (befund === null) { el.hidden = true; return; }
    el.querySelector('[data-stand-text]').textContent = muruStandText(befund);
  } catch (e) {
    el.hidden = false;
  }
})();
"""


def standhinweis(aktualisiert: str | None) -> str:
    """Der Block oben auf jeder Seite, die Spielplandaten zeigt."""
    if aktualisiert:
        w = datetime.fromisoformat(aktualisiert).astimezone(TZ)
        text = (f"Stand der Daten: {w:%d.%m.%Y} um {w:%H:%M} Uhr. Ob das noch "
                f"aktuell ist, lässt sich gerade nicht prüfen.")
    else:
        text = ("Wann der Spielplan zuletzt mit handball.net abgeglichen wurde, "
                "lässt sich gerade nicht sagen.")
    return f"""<div class="veraltet" id="veraltet" role="status"
     data-stand="{html.escape(aktualisiert or '')}">
  <h2>Spielplan womöglich nicht aktuell</h2>
  <p data-stand-text>{html.escape(text)}</p>
  <p>Im Zweifel bei <a href="https://www.handball.net" target="_blank"
     rel="noopener">handball.net</a> nachschauen.</p>
</div>
<script>{PRUEFUNG}{AUSFUEHREN}</script>"""

