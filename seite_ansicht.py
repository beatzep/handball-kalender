"""Umschalter zwischen heller und dunkler Ansicht.

Voreinstellung ist das, was das Geraet vorgibt. Erst wer tippt, legt sich
fest; die Wahl bleibt im Browser. Gezeigt wird immer das Ziel - im Hellen
der Mond, im Dunklen die Sonne.
"""

ANSICHT = """
(function () {
  var SCHLUESSEL = 'muru-ansicht';
  var wurzel = document.documentElement;
  var knopf = document.getElementById('ansicht');

  function gespeichert() {
    try { return localStorage.getItem(SCHLUESSEL) || ''; } catch (e) { return ''; }
  }

  function istDunkel() {
    var wahl = wurzel.getAttribute('data-ansicht');
    if (wahl) return wahl === 'dunkel';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  function beschrifte() {
    if (!knopf) return;
    knopf.setAttribute('aria-label',
      istDunkel() ? 'Zu heller Ansicht wechseln' : 'Zu dunkler Ansicht wechseln');
  }

  var wahl = gespeichert();
  if (wahl === 'hell' || wahl === 'dunkel') wurzel.setAttribute('data-ansicht', wahl);
  beschrifte();

  if (knopf) {
    knopf.addEventListener('click', function () {
      var neu = istDunkel() ? 'hell' : 'dunkel';
      wurzel.setAttribute('data-ansicht', neu);
      try { localStorage.setItem(SCHLUESSEL, neu); } catch (e) {}
      // Farbe der Systemleisten mitziehen
      var meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.setAttribute('content', neu === 'dunkel' ? '#000000' : '#14140f');
      beschrifte();
    });
  }

  // Ohne eigene Wahl der Systemeinstellung folgen, auch wenn sie sich aendert
  var beobachter = window.matchMedia('(prefers-color-scheme: dark)');
  if (beobachter.addEventListener) {
    beobachter.addEventListener('change', function () {
      if (!gespeichert()) beschrifte();
    });
  }
})();
"""
