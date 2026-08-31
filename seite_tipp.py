"""Tipprunde im Browser: Tipp abgeben, Tabelle anzeigen, Kennung mitnehmen."""

TIPP = """
(function () {
  var bloecke = [].slice.call(document.querySelectorAll('[data-tipp]'));
  if (!bloecke.length || !window.muruGeraet) return;
  var geraet = window.muruGeraet();

  // Der eigene Stand ist fuer alle Bloecke derselbe. Frueher holte ihn
  // jeder einzeln - vierundzwanzig Mal dieselbe Adresse pro Seitenaufruf.
  var eigenerStand = null;
  function holeEigenenStand(worker) {
    if (!eigenerStand) {
      eigenerStand = fetch(worker + '/tipper?geraet=' + encodeURIComponent(geraet))
        .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); });
    }
    return eigenerStand;
  }

  bloecke.forEach(function (block) {
    var huelle = block.closest('.mitmachen');
    var worker = huelle && huelle.getAttribute('data-worker');
    if (!worker) { block.hidden = true; return; }

    var spiel = block.getAttribute('data-tipp');
    var mannschaft = block.getAttribute('data-mannschaft') || '';
    var heimFeld = block.querySelector('[data-tippfeld="heim"]');
    var gastFeld = block.querySelector('[data-tippfeld="gast"]');
    var nameFeld = block.querySelector('[data-tippname]');
    var senden = block.querySelector('[data-tippsenden]');
    var meldung = block.querySelector('[data-tippmeldung]');
    var tabelle = block.querySelector('[data-tipptabelle]');
    var umzug = block.querySelector('[data-tippumzug]');
    var getippt = false;   // hat dieses Geraet fuer irgendein Spiel getippt?

    function sage(text, art) {
      meldung.textContent = text || '';
      meldung.className = 'meldung' + (art ? ' ' + art : '');
    }

    function zeile(platz, name, punkte, ich) {
      return '<tr' + (ich ? ' class="ich"' : '') + '><td class="pl">' + platz +
        '</td><td>' + String(name).replace(/[<>&]/g, '') +
        '</td><td class="pkt">' + punkte + '</td></tr>';
    }

    var ZEIGE = 10;

    function zeigeTabelle(zeilen) {
      zeilen = zeilen || [];
      var reihen = zeilen.slice(0, ZEIGE).map(function (e) {
        return zeile(e.platz, e.name, e.punkte, e.id === geraet);
      });

      // Wer weiter hinten steht, sah sich bisher gar nicht - die Liste
      // brach nach zehn Zeilen ab. Den eigenen Platz anhaengen.
      var eigene = zeilen.findIndex
        ? zeilen.findIndex(function (e) { return e.id === geraet; })
        : -1;
      if (eigene >= ZEIGE) {
        var e = zeilen[eigene];
        reihen.push('<tr class="luecke"><td colspan="3">…</td></tr>');
        reihen.push(zeile(e.platz, e.name, e.punkte, true));
      }

      // Neu angelegte Eintraege erscheinen in der Auflistung des Speichers
      // erst mit Verzoegerung. Wer gerade getippt hat, saehe sich sonst
      // minutenlang nicht - darum vorlaeufig selbst eintragen.
      if (eigene < 0 && nameFeld.value.trim() && getippt) {
        reihen.push(zeile('–', nameFeld.value.trim(), 0, true));
      }

      if (!reihen.length) { tabelle.innerHTML = ''; return; }
      // Zehn Zeilen sahen aus wie die ganze Runde. Bei achtzehn Mitspielern
      // war das schlicht irrefuehrend.
      var rest = zeilen.length - ZEIGE;
      tabelle.innerHTML = '<table><tbody>' + reihen.join('') + '</tbody></table>'
        + (rest > 0 ? '<p class="tippfuss">' + zeilen.length + ' machen mit'
             + (eigene >= ZEIGE ? '' : ', ' + rest + ' weitere nicht gezeigt')
             + '.</p>' : '');
    }

    function ladeTabelle() {
      fetch(worker + '/tipptabelle?mannschaft=' + encodeURIComponent(mannschaft))
        .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
        .then(function (d) {
          zeigeTabelle(d.tabelle);
          if (d.unvollstaendig && tabelle.innerHTML) {
            var u = d.unvollstaendig;
            var n = (u.ausgelassen || 0) + (u.unlesbar || 0);
            var text = u.imAufbau
              ? 'Diese Wertung wird gerade neu aufgebaut, es fehlen noch '
                + 'Einträge. Kein Tipp geht dabei verloren.'
              : n + (n === 1 ? ' Eintrag fehlt' : ' Einträge fehlen') + ' in dieser Wertung.';
            tabelle.insertAdjacentHTML('beforeend',
              '<p class="tippfuss">' + text + '</p>');
          }
        })
        .catch(function () {
          // Frueher wurde hier stumm geleert. Die Tabelle war dadurch
          // monatelang kaputt, ohne dass es jemand sehen konnte.
          tabelle.innerHTML = '<p class="tippfuss">Die Tabelle lässt sich '
            + 'gerade nicht laden. Dein Tipp ist gespeichert.</p>';
        });
    }

    // Eigener Stand: Name und ein bereits abgegebener Tipp
    holeEigenenStand(worker)
      .then(function (d) {
        if (d.name) nameFeld.value = d.name;
        if (d.tipps && Object.keys(d.tipps).length) getippt = true;
        var vorhanden = d.tipps && d.tipps[spiel];
        if (vorhanden) {
          heimFeld.value = vorhanden[0];
          gastFeld.value = vorhanden[1];
          sage('Dein Tipp steht. Ändern geht bis zum Anwurf.');
        }
      })
      .catch(function () { block.hidden = true; });

    var wessen = block.closest('[data-team]');
    if (wessen && window.muruBeiAnzeige) {
      window.muruBeiAnzeige(wessen.getAttribute('data-team'), ladeTabelle);
    } else {
      ladeTabelle();
    }

    senden.addEventListener('click', function () {
      var h = parseInt(heimFeld.value, 10), g = parseInt(gastFeld.value, 10);
      if (!Number.isFinite(h) || !Number.isFinite(g) || h < 0 || g < 0) {
        sage('Bitte beide Felder ausfüllen.', 'schlecht');
        return;
      }
      if (!nameFeld.value.trim()) {
        sage('Ohne Namen taucht dein Tipp nicht in der Tabelle auf.', 'schlecht');
        nameFeld.focus();
        return;
      }
      senden.disabled = true;
      sage('Wird gesendet …');
      fetch(worker + '/tipp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ geraet: geraet, spiel: spiel, heim: h, gast: g,
                               name: nameFeld.value.trim() })
      })
        .then(function (r) {
          return r.json().then(function (d) {
            return r.ok ? d : Promise.reject(d.fehler || 'Fehler');
          });
        })
        .then(function () {
          getippt = true;
          sage('Tipp gespeichert. Ändern geht bis zum Anwurf.', 'gut');
          ladeTabelle();
        })
        .catch(function (f) { sage(String(f), 'schlecht'); })
        .then(function () { senden.disabled = false; });
    });

    if (umzug) {
      umzug.addEventListener('click', function () {
        var link = location.origin + location.pathname + '?tipper=' +
                   encodeURIComponent(geraet);
        var text = 'Damit tippe ich auf jedem Gerät weiter: ' + link;
        if (navigator.share) {
          navigator.share({ text: text }).catch(function () {});
          return;
        }
        navigator.clipboard.writeText(link).then(function () {
          sage('Link kopiert. Damit tippst du auf jedem Gerät weiter.', 'gut');
        });
      });
    }
  });
})();
"""
