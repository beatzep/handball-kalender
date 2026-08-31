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
    //
    // Der Inhaltstyp muss text/plain sein, obwohl JSON drinsteht: mit
    // application/json gilt die Anfrage nicht mehr als einfach, der Browser
    // schickt erst eine OPTIONS-Vorfrage - und die verbraucht die einzige
    // Zustellung, die er beim Schliessen der Seite noch zusagt. Im
    // Worker-Protokoll standen darum lauter OPTIONS ohne zugehoerigen POST,
    // und die Zaehlung blieb tagelang bei null. Der Worker liest den Koerper
    // ohnehin als JSON, unabhaengig vom angegebenen Typ.
    if (beimVerlassen && navigator.sendBeacon) {
      var zugestellt = navigator.sendBeacon(worker + '/zaehl',
        new Blob([last], { type: 'text/plain' }));
      if (zugestellt) return;
      // Nimmt der Browser den Beacon nicht an (Warteschlange voll), bleibt
      // fetch mit keepalive - das ueberlebt das Schliessen ebenfalls.
    }
    fetch(worker + '/zaehl', {
      method: 'POST', headers: { 'Content-Type': 'text/plain' }, body: last,
      keepalive: !!beimVerlassen
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
