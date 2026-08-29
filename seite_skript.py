"""Clientseitige Logik der Abo-Seite: Mannschaftswahl, Reiter, Zeitangaben, Teilen.

Bewusst ohne f-String gehalten, damit die geschweiften Klammern des
JavaScripts nicht verdoppelt werden muessen.

"""

SKRIPT = """
// ---------------------------------------------------------------------
// Geraetekennung - anonym, bleibt im Browser
// ---------------------------------------------------------------------
// Dient dazu, eine Zusage zurueckziehen und die eigenen Tipps wiederfinden
// zu koennen. Wer das Geraet wechselt, nimmt sie ueber den Umzugslink mit.
window.muruGeraet = (function () {
  var SCHLUESSEL = 'muru-geraet';
  var kennung = null;
  return function () {
    if (kennung) return kennung;
    try {
      // Eine Kennung aus dem Umzugslink hat Vorrang und wird uebernommen.
      var ausAdresse = new URLSearchParams(location.search).get('tipper');
      if (ausAdresse && /^[A-Za-z0-9_-]{4,40}$/.test(ausAdresse)) {
        localStorage.setItem(SCHLUESSEL, ausAdresse);
        history.replaceState(null, '', location.pathname + location.hash);
      }
      kennung = localStorage.getItem(SCHLUESSEL) || '';
      if (!kennung) {
        kennung = (crypto.randomUUID ? crypto.randomUUID()
                                     : String(Math.random()).slice(2))
                    .replace(/[^A-Za-z0-9_-]/g, '');
        localStorage.setItem(SCHLUESSEL, kennung);
      }
    } catch (e) {
      kennung = 'ohne-speicher';
    }
    return kennung;
  };
})();

(function () {
  var seite = document.documentElement;
  var wahl = document.getElementById('teamwahl');
  var mannschaften = [].slice.call(document.querySelectorAll('[data-team]'));
  if (!wahl || !mannschaften.length) return;

  var ANSICHTEN = ['kalender', 'spiele', 'tabelle', 'statistik'];
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

// ---------------------------------------------------------------------
// Hype-Zaehler und Zusagen
// ---------------------------------------------------------------------
(function () {
  var bloecke = [].slice.call(document.querySelectorAll('.mitmachen'));
  if (!bloecke.length) return;

  var geraet = window.muruGeraet();

  bloecke.forEach(function (block) {
    var worker = block.getAttribute('data-worker');
    var spiel = block.getAttribute('data-spiel');
    var vorher = block.getAttribute('data-vorher');
    var zahlEl = block.querySelector('[data-hype]');
    var vergleichEl = block.querySelector('[data-vergleich]');
    var bahn = block.querySelector('[data-bahn]');
    var anzahlEl = block.querySelector('[data-anzahl]');
    var dabeiKnopf = block.querySelector('[data-dabei]');

    var hype = 0;          // angezeigter Stand
    var offen = 0;         // noch nicht gesendete Klicks
    var sendet = false;

    function zeige() { zahlEl.textContent = hype.toLocaleString('de-DE'); }

    function melde(text) { if (vergleichEl) vergleichEl.textContent = text; }

    // Stand holen
    var adresse = worker + '/stand?spiel=' + encodeURIComponent(spiel) +
                  (vorher ? '&vergleich=' + encodeURIComponent(vorher) : '');
    fetch(adresse)
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (d) {
        hype = d.hype || 0;
        zeige();
        if (d.vorher && d.vorher.hype) melde('letztes Spiel: ' + d.vorher.hype);
        if (anzahlEl) {
          anzahlEl.textContent = d.dabei === 1 ? '1 Zusage' : d.dabei + ' Zusagen';
        }
      })
      .catch(function () {
        // Ist der Zaehler nicht erreichbar, verschwindet der Block ganz.
        // Ein sichtbarer, aber toter Knopf ist schlechter als keiner.
        block.hidden = true;
      });

    // Klicks buendeln: ein Aufruf je zwei Sekunden statt einer pro Klick
    function sende() {
      if (sendet || !offen) return;
      var menge = Math.min(offen, 25);
      offen -= menge;
      sendet = true;
      fetch(worker + '/hype', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ spiel: spiel, anzahl: menge })
      })
        .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
        .then(function (d) { if (typeof d.hype === 'number') { hype = d.hype; zeige(); } })
        .catch(function () {
          // Nicht angekommen: die Klicks zurueck in die Warteschlange, sonst
          // zaehlt ein kurzer Funkloch-Moment sie stillschweigend nicht mit.
          offen += menge;
        })
        .then(function () { sendet = false; });
    }
    // Alle dreissig Sekunden: Der Speicher erlaubt im kostenlosen Tarif rund
    // tausend Schreibvorgaenge am Tag. Die Anzeige laeuft sofort mit, nur der
    // Abgleich mit dem Server hinkt nach - das faellt beim Klicken nicht auf.
    setInterval(sende, 30000);

    // Beim Verlassen der Seite wird ein laufendes fetch abgebrochen -
    // sendBeacon wird vom Browser noch zu Ende gebracht.
    window.addEventListener('pagehide', function () {
      if (!offen) return;
      var nutzlast = JSON.stringify({ spiel: spiel, anzahl: Math.min(offen, 25) });
      if (navigator.sendBeacon) {
        navigator.sendBeacon(worker + '/hype',
          new Blob([nutzlast], { type: 'application/json' }));
        offen = 0;
      } else {
        sende();
      }
    });

    block.querySelectorAll('.knoepfe button').forEach(function (k) {
      k.addEventListener('click', function () {
        hype += 1; offen += 1; zeige();
        var flug = document.createElement('span');
        flug.className = 'flug';
        flug.textContent = k.getAttribute('data-emoji');
        flug.style.left = (k.offsetLeft + 14) + 'px';
        bahn.appendChild(flug);
        setTimeout(function () { flug.remove(); }, 1000);
      });
    });

    if (dabeiKnopf) {
      dabeiKnopf.addEventListener('click', function () {
        var an = dabeiKnopf.getAttribute('aria-pressed') !== 'true';
        dabeiKnopf.setAttribute('aria-pressed', an ? 'true' : 'false');
        dabeiKnopf.textContent = an ? 'Ich bin dabei ✓' : 'Ich bin dabei';
        fetch(worker + '/dabei', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ spiel: spiel, geraet: geraet, an: an })
        })
          .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
          .then(function (d) {
            anzahlEl.textContent = d.dabei === 1 ? '1 Zusage' : d.dabei + ' Zusagen';
          })
          .catch(function () { anzahlEl.textContent = 'gerade nicht erreichbar'; });
      });
    }
  });
})();

// ---------------------------------------------------------------------
// Countdown bis zum Anwurf
// ---------------------------------------------------------------------
(function () {
  var felder = [].slice.call(document.querySelectorAll('[data-countdown]'));
  if (!felder.length) return;

  function zweistellig(n) { return (n < 10 ? '0' : '') + n; }

  function schreibe() {
    var jetzt = Date.now();
    felder.forEach(function (el) {
      var ziel = new Date(el.getAttribute('data-countdown')).getTime();
      if (isNaN(ziel)) return;
      var rest = Math.floor((ziel - jetzt) / 1000);

      if (rest <= 0) {
        // Ein Handballspiel dauert rund zwei Stunden - so lange gilt es als laufend.
        el.textContent = rest > -7200 ? 'Läuft gerade' : 'Angepfiffen';
        return;
      }
      var tage = Math.floor(rest / 86400);
      var std = Math.floor((rest % 86400) / 3600);
      var min = Math.floor((rest % 3600) / 60);
      var sek = rest % 60;

      if (tage > 0) {
        el.innerHTML = 'noch <span>' + tage + '</span> <span class="einheit">' +
          (tage === 1 ? 'Tag' : 'Tage') + '</span> <span>' + std +
          '</span> <span class="einheit">Std</span> <span>' + min +
          '</span> <span class="einheit">Min</span>';
      } else {
        el.innerHTML = 'noch <span>' + zweistellig(std) + ':' + zweistellig(min) +
          ':' + zweistellig(sek) + '</span> <span class="einheit">Std</span>';
      }
    });
  }

  schreibe();
  setInterval(schreibe, 1000);
})();

// ---------------------------------------------------------------------
// Angeheftete Mannschaften
// ---------------------------------------------------------------------
// Bei 23 Einträgen sucht sich sonst jeder tot. Angeheftete stehen oben in
// einer eigenen Gruppe; gemerkt wird das im Browser.
(function () {
  var wahl = document.getElementById('teamwahl');
  var knopf = document.getElementById('anheften');
  if (!wahl || !knopf) return;

  var SCHLUESSEL = 'muru-angeheftet';

  function lies() {
    try { return JSON.parse(localStorage.getItem(SCHLUESSEL) || '[]'); }
    catch (e) { return []; }
  }
  function schreib(liste) {
    try { localStorage.setItem(SCHLUESSEL, JSON.stringify(liste)); } catch (e) {}
  }

  function ordne() {
    var liste = lies();
    var vorhanden = document.getElementById('angeheftet');
    if (vorhanden) {
      // Zurück an ihren Platz, sonst sammeln sich Doppelungen an
      [].slice.call(vorhanden.children).forEach(function (o) {
        var heimat = document.querySelector(
          'optgroup[data-gruppe="' + o.getAttribute('data-gruppe') + '"]');
        if (heimat) heimat.appendChild(o);
      });
      vorhanden.remove();
    }
    if (!liste.length) return;

    var gruppe = document.createElement('optgroup');
    gruppe.id = 'angeheftet';
    gruppe.label = 'Angeheftet';
    liste.forEach(function (schluessel) {
      var option = wahl.querySelector('option[value="' + schluessel + '"]');
      if (!option) return;
      if (!option.getAttribute('data-gruppe')) {
        option.setAttribute('data-gruppe',
          option.parentNode.getAttribute('data-gruppe') || '');
      }
      gruppe.appendChild(option);
    });
    if (gruppe.children.length) wahl.insertBefore(gruppe, wahl.firstChild);
  }

  function zeigeKnopf() {
    var an = lies().indexOf(wahl.value) >= 0;
    knopf.setAttribute('aria-pressed', an ? 'true' : 'false');
    knopf.textContent = an ? 'Angeheftet' : 'Anheften';
  }

  knopf.addEventListener('click', function () {
    var liste = lies();
    var stelle = liste.indexOf(wahl.value);
    if (stelle >= 0) liste.splice(stelle, 1); else liste.push(wahl.value);
    schreib(liste);
    var gemerkt = wahl.value;
    ordne();
    wahl.value = gemerkt;
    zeigeKnopf();
  });

  wahl.addEventListener('change', zeigeKnopf);
  ordne();
  zeigeKnopf();
})();
"""
