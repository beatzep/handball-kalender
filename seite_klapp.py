"""Aufklappbare Abschnitte: Zustand merken und alles auf einmal umschalten.

Die Abschnitte selbst sind <details> und funktionieren ohne dieses Skript.
Hier kommt nur dazu, was HTML nicht mitbringt: sich zu merken, was jemand
aufgeklappt hatte, und ein Schalter fuer alle auf einmal.
"""

KLAPP = """
(function () {
  var SCHLUESSEL = 'muru-klapp';

  function lies() {
    try { return JSON.parse(localStorage.getItem(SCHLUESSEL) || '{}'); }
    catch (e) { return {}; }
  }
  function schreib(stand) {
    try { localStorage.setItem(SCHLUESSEL, JSON.stringify(stand)); } catch (e) {}
  }

  var stand = lies();

  // Gemerkten Zustand herstellen. Was noch nie angefasst wurde, bleibt so,
  // wie die Seite es vorgibt - "Wer trifft" ist dort offen.
  [].slice.call(document.querySelectorAll('details[data-klapp]')).forEach(
    function (d) {
      var name = d.getAttribute('data-klapp');
      if (Object.prototype.hasOwnProperty.call(stand, name)) {
        d.open = !!stand[name];
      }
      d.addEventListener('toggle', function () {
        stand = lies();
        stand[name] = d.open;
        schreib(stand);
        beschrifte(d.closest('[data-team]'));
      });
    });

  // Ein Schalter je Gruppe von Abschnitten. Die Beschriftung richtet sich
  // danach, was ueberwiegt: sind die meisten zu, klappt er auf.
  function beschrifte(bereich) {
    if (!bereich) return;
    [].slice.call(bereich.querySelectorAll('[data-alleklapp]')).forEach(
      function (knopf) {
        var ziel = knopf.getAttribute('data-alleklapp');
        var teile = teileVon(bereich, ziel);
        if (!teile.length) { knopf.hidden = true; return; }
        var offen = teile.filter(function (d) { return d.open; }).length;
        var aufklappen = offen * 2 <= teile.length;
        knopf.textContent = aufklappen ? 'Alle aufklappen' : 'Alle einklappen';
        knopf.setAttribute('data-richtung', aufklappen ? 'auf' : 'zu');
      });
  }

  function teileVon(bereich, ziel) {
    var alle = [].slice.call(bereich.querySelectorAll('details[data-klapp]'));
    if (ziel === 'spiele') {
      return alle.filter(function (d) {
        return d.getAttribute('data-klapp').indexOf('spiel-') === 0;
      });
    }
    // Die Abschnitte der Seite, nicht die einzelnen Spiele darin
    return alle.filter(function (d) {
      return d.getAttribute('data-klapp').indexOf('spiel-') !== 0;
    });
  }

  document.addEventListener('click', function (e) {
    var knopf = e.target.closest ? e.target.closest('[data-alleklapp]') : null;
    if (!knopf) return;
    var bereich = knopf.closest('[data-team]');
    var auf = knopf.getAttribute('data-richtung') !== 'zu';
    teileVon(bereich, knopf.getAttribute('data-alleklapp')).forEach(
      function (d) { d.open = auf; });
  });

  [].slice.call(document.querySelectorAll('[data-team]')).forEach(beschrifte);
})();
"""
