"""Nutzungszaehlung im Browser - aggregiert, ohne jede Wiedererkennung.

Gezaehlt werden Summen pro Tag: wie viele Aufrufe, welche Mannschaft, welcher
Bereich, welche Knoepfe. Keine Kennung, kein Zeitstempel je Besuch, kein
Zugriff auf die Geraetekennung der Tipprunde - die ist zweckgebunden.
"""

ZAEHLUNG = """
(function () {
  var huelle = document.querySelector('[data-worker]');
  var worker = huelle && huelle.getAttribute('data-worker');
  if (!worker) return;

  var offen = { ereignis: {}, mannschaft: {}, bereich: {} };
  var etwasOffen = false;

  function merke(gruppe, name) {
    if (!name) return;
    offen[gruppe][name] = (offen[gruppe][name] || 0) + 1;
    etwasOffen = true;
  }

  function sende(beimVerlassen) {
    if (!etwasOffen) return;
    var last = JSON.stringify(offen);
    offen = { ereignis: {}, mannschaft: {}, bereich: {} };
    etwasOffen = false;
    // Beim Verlassen wird ein laufendes fetch abgebrochen - sendBeacon nicht.
    if (beimVerlassen && navigator.sendBeacon) {
      navigator.sendBeacon(worker + '/zaehl',
        new Blob([last], { type: 'application/json' }));
      return;
    }
    fetch(worker + '/zaehl', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: last
    }).catch(function () {});
  }

  merke('ereignis', 'aufruf');
  var wahl = document.getElementById('teamwahl');
  if (wahl) merke('mannschaft', wahl.value);

  // Alles Weitere wird gesammelt und erst beim Verlassen gebuendelt
  // geschickt: Der Speicher vertraegt nur rund tausend Schreibvorgaenge
  // am Tag, ein Aufruf je Klick waere daran schnell vorbei.
  document.addEventListener('click', function (e) {
    var ziel = e.target.closest('button, a');
    if (!ziel) return;
    if (ziel.hasAttribute('data-ziel')) merke('bereich', ziel.getAttribute('data-ziel'));
    else if (ziel.classList.contains('knopf') && ziel.getAttribute('href'))
      merke('ereignis', ziel.getAttribute('href').indexOf('webcal') === 0 ? 'abo' : 'datei');
    else if (ziel.hasAttribute('data-grafik')) merke('ereignis', 'grafik');
    else if (ziel.hasAttribute('data-tippsenden')) merke('ereignis', 'tipp');
    else if (ziel.hasAttribute('data-emoji')) merke('ereignis', 'hype');
    else if (ziel.hasAttribute('data-dabei')) merke('ereignis', 'dabei');
    else if (ziel.hasAttribute('data-teile') || ziel.hasAttribute('data-kopiere'))
      merke('ereignis', 'teilen');
  }, true);

  if (wahl) wahl.addEventListener('change', function () { merke('mannschaft', wahl.value); });

  // Alles zusammen erst beim Verlassen - ein Schreibvorgang je Besuch statt
  // zwei. Der Speicher erlaubt im kostenlosen Tarif rund tausend am Tag, und
  // Seitenaufrufe sind der groesste Posten. sendBeacon wird vom Browser auch
  // beim Schliessen noch zugestellt.
  window.addEventListener('pagehide', function () { sende(true); });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') sende(true);
  });
})();
"""
