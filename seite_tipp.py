"""Tipprunde im Browser: Tipp abgeben, Tabelle anzeigen, Kennung mitnehmen."""

TIPP = """
(function () {
  var bloecke = [].slice.call(document.querySelectorAll('[data-tipp]'));
  if (!bloecke.length || !window.muruGeraet) return;
  var geraet = window.muruGeraet();

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

    function zeigeTabelle(zeilen) {
      zeilen = zeilen || [];
      var reihen = zeilen.slice(0, 10).map(function (e) {
        return zeile(e.platz, e.name, e.punkte, e.id === geraet);
      });

      // Neu angelegte Eintraege erscheinen in der Auflistung des Speichers
      // erst mit Verzoegerung. Wer gerade getippt hat, saehe sich sonst
      // minutenlang nicht - darum vorlaeufig selbst eintragen.
      var drin = zeilen.some(function (e) { return e.id === geraet; });
      if (!drin && nameFeld.value.trim() && getippt) {
        reihen.push(zeile('–', nameFeld.value.trim(), 0, true));
      }

      tabelle.innerHTML = reihen.length
        ? '<table><tbody>' + reihen.join('') + '</tbody></table>'
        : '';
    }

    function ladeTabelle() {
      fetch(worker + '/tipptabelle?mannschaft=' + encodeURIComponent(mannschaft))
        .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
        .then(function (d) {
          zeigeTabelle(d.tabelle);
          if (d.unvollstaendig && tabelle.innerHTML) {
            var n = (d.unvollstaendig.ausgelassen || 0) + (d.unvollstaendig.unlesbar || 0);
            tabelle.insertAdjacentHTML('beforeend',
              '<p class="tippfuss">' + n + (n === 1 ? ' Eintrag fehlt' : ' Einträge fehlen')
              + ' in dieser Wertung.</p>');
          }
        })
        .catch(function () {
          // Frueher wurde hier stumm geleert. Die Tabelle war dadurch
          // monatelang kaputt, ohne dass es jemand sehen konnte.
          tabelle.innerHTML = '<p class="tippfuss">Die Tabelle laesst sich '
            + 'gerade nicht laden. Dein Tipp ist gespeichert.</p>';
        });
    }

    // Eigener Stand: Name und ein bereits abgegebener Tipp
    fetch(worker + '/tipper?geraet=' + encodeURIComponent(geraet))
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
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

    ladeTabelle();

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
