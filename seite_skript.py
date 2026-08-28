"""Clientseitige Logik der Abo-Seite: Mannschaftswahl, Reiter, Zeitangaben, Teilen.

Bewusst ohne f-String gehalten, damit die geschweiften Klammern des
JavaScripts nicht verdoppelt werden muessen.
"""

SKRIPT = """
(function () {
  var seite = document.documentElement;
  var wahl = document.getElementById('teamwahl');
  var mannschaften = [].slice.call(document.querySelectorAll('[data-team]'));
  if (!wahl || !mannschaften.length) return;

  var ANSICHTEN = ['kalender', 'spiele', 'tabelle'];
  var SPEICHER = 'muru-mannschaft';

  function zeigeMannschaft(schluessel) {
    var treffer = false;
    mannschaften.forEach(function (m) {
      var passt = m.getAttribute('data-team') === schluessel;
      m.hidden = !passt;
      if (passt) treffer = true;
    });
    if (!treffer) return false;
    wahl.value = schluessel;
    try { localStorage.setItem(SPEICHER, schluessel); } catch (e) {}
    return true;
  }

  function zeigeAnsicht(schluessel, ansicht) {
    var m = document.querySelector('[data-team="' + schluessel + '"]');
    if (!m) return;
    m.querySelectorAll('[data-ansicht]').forEach(function (b) {
      b.hidden = b.getAttribute('data-ansicht') !== ansicht;
    });
    m.querySelectorAll('.reiter button').forEach(function (k) {
      k.setAttribute('aria-selected', k.getAttribute('data-ziel') === ansicht ? 'true' : 'false');
    });
  }

  function ausAdresse() {
    var teile = (location.hash || '').replace(/^#/, '').split('/');
    return { team: teile[0] || '', ansicht: ANSICHTEN.indexOf(teile[1]) >= 0 ? teile[1] : 'kalender' };
  }

  function setzeAdresse(schluessel, ansicht) {
    var neu = '#' + schluessel + (ansicht !== 'kalender' ? '/' + ansicht : '');
    if (location.hash !== neu) history.replaceState(null, '', neu);
  }

  // Zeitangabe ("Morgen") im Browser berechnen - beim naechtlichen Bauen
  // gesetzt waere sie veraltet, sobald ein Lauf ausfaellt.
  function frischeZeitangaben() {
    document.querySelectorAll('[data-anwurf]').forEach(function (el) {
      var anwurf = new Date(el.getAttribute('data-anwurf'));
      if (isNaN(anwurf)) return;
      var heute = new Date(); heute.setHours(0, 0, 0, 0);
      var tag = new Date(anwurf); tag.setHours(0, 0, 0, 0);
      var tage = Math.round((tag - heute) / 86400000);
      el.textContent = tage < 0 ? 'Läuft gerade'
        : tage === 0 ? 'Heute' : tage === 1 ? 'Morgen'
        : tage < 7 ? 'In ' + tage + ' Tagen' : 'Nächstes Spiel';
    });
  }

  var start = ausAdresse();
  var gespeichert = '';
  try { gespeichert = localStorage.getItem(SPEICHER) || ''; } catch (e) {}
  var aktiv = start.team || gespeichert || mannschaften[0].getAttribute('data-team');
  if (!zeigeMannschaft(aktiv)) {
    aktiv = mannschaften[0].getAttribute('data-team');
    zeigeMannschaft(aktiv);
  }
  ANSICHTEN.forEach(function () {});
  mannschaften.forEach(function (m) {
    zeigeAnsicht(m.getAttribute('data-team'), 'kalender');
  });
  zeigeAnsicht(aktiv, start.ansicht);
  setzeAdresse(aktiv, start.ansicht);
  frischeZeitangaben();
  seite.setAttribute('data-bereit', 'ja');

  wahl.addEventListener('change', function () {
    aktiv = wahl.value;
    zeigeMannschaft(aktiv);
    zeigeAnsicht(aktiv, 'kalender');
    setzeAdresse(aktiv, 'kalender');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  document.querySelectorAll('.reiter button').forEach(function (k) {
    k.addEventListener('click', function () {
      var ansicht = k.getAttribute('data-ziel');
      zeigeAnsicht(aktiv, ansicht);
      setzeAdresse(aktiv, ansicht);
    });
  });

  // Adresse in die Zwischenablage (Google Kalender)
  document.querySelectorAll('[data-kopiere]').forEach(function (k) {
    k.addEventListener('click', function () {
      var text = k.getAttribute('data-kopiere');
      navigator.clipboard.writeText(text).then(function () {
        var alt = k.textContent;
        k.textContent = 'Adresse kopiert';
        setTimeout(function () { k.textContent = alt; }, 1800);
      });
    });
  });

  // Änderungen weitergeben: auf dem Handy direkt ins Teilen-Menue,
  // sonst in die Zwischenablage.
  document.querySelectorAll('[data-teile]').forEach(function (k) {
    k.addEventListener('click', function () {
      var text = k.getAttribute('data-teile');
      if (navigator.share) {
        navigator.share({ text: text }).catch(function () {});
        return;
      }
      navigator.clipboard.writeText(text).then(function () {
        var alt = k.textContent;
        k.textContent = 'Text kopiert';
        setTimeout(function () { k.textContent = alt; }, 1800);
      });
    });
  });

  // Hinweis zum Home-Bildschirm nur auf iOS, und nur solange die Seite
  // nicht ohnehin schon als App laeuft. Android bietet es von selbst an.
  var istIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
  var alsApp = window.navigator.standalone === true ||
               window.matchMedia('(display-mode: standalone)').matches;
  if (istIOS && !alsApp) {
    document.querySelectorAll('[data-ios-tipp]').forEach(function (el) { el.hidden = false; });
  }
})();
"""
