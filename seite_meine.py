"""Verschraenkter Blick ueber alle angehefteten Mannschaften.

Wer zwei Kinder im Verein hat oder selbst in zwei Altersklassen spielt,
haelt sonst zwei Spielplaene nebeneinander. Hier laufen sie in einer Liste
zusammen - und wo sich zwei Spiele in die Quere kommen, steht es dabei.
"""

MEINE = """
(function () {
  var quelle = document.getElementById('spieldaten');
  var kasten = document.getElementById('meine-inhalt');
  var wahl = document.getElementById('teamwahl');
  var option = wahl && wahl.querySelector('option[value="meine"]');
  if (!quelle || !kasten || !option) return;

  var ALLE = [];
  try { ALLE = JSON.parse(quelle.textContent); } catch (e) { return; }

  var SPIELDAUER = 105;      // Minuten Anwurf bis Abpfiff, Pause eingerechnet
  var RUESTZEIT  = 10;       // Parken, Halle finden, Umziehen
  var UMWEG      = 1.3;      // Luftlinie ist keine Strasse
  var KMH        = 70;
  var TAGE = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'];
  var MONATE = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli',
                'August', 'September', 'Oktober', 'November', 'Dezember'];

  function angeheftet() {
    try { return JSON.parse(localStorage.getItem('muru-angeheftet') || '[]'); }
    catch (e) { return []; }
  }

  function entfernung(a, b) {
    if (!a || !b) return null;
    var R = 6371, rad = Math.PI / 180;
    var dLat = (b[0] - a[0]) * rad, dLon = (b[1] - a[1]) * rad;
    var h = Math.sin(dLat / 2) * Math.sin(dLat / 2)
          + Math.cos(a[0] * rad) * Math.cos(b[0] * rad)
          * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return R * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h)) * UMWEG;
  }

  function fahrzeit(km) { return RUESTZEIT + Math.round(km / KMH * 60); }

  function dauerWort(min) {
    if (min < 60) return min + ' Minuten';
    var h = Math.floor(min / 60), m = min % 60;
    return h + (m ? ':' + zweistellig(m) : '') + (h === 1 && !m ? ' Stunde' : ' Stunden');
  }

  function zweistellig(n) { return (n < 10 ? '0' : '') + n; }
  function uhr(d) { return zweistellig(d.getHours()) + ':' + zweistellig(d.getMinutes()); }
  function tagStempel(d) {
    return d.getFullYear() + '-' + zweistellig(d.getMonth() + 1) + '-' + zweistellig(d.getDate());
  }
  function esc(t) {
    return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // Spiele der angehefteten Mannschaften, chronologisch, ab heute
  function kommende() {
    var meine = angeheftet();
    if (!meine.length) return [];
    var grenze = new Date(); grenze.setHours(0, 0, 0, 0);
    return ALLE.filter(function (s) {
      return meine.indexOf(s.m) >= 0 && new Date(s.d) >= grenze;
    }).map(function (s) {
      var an = new Date(s.d);
      return {
        roh: s, mannschaft: s.n, anwurf: an, tag: tagStempel(an),
        ohneZeit: !!s.k, gegner: s.g, halle: s.h, ort: s.o, heim: !!s.z,
        punkt: s.p || null
      };
    }).sort(function (a, b) { return a.anwurf - b.anwurf; });
  }

  // Zwei Spiele am selben Tag: passt das zeitlich, wenn man beide will?
  function pruefePaar(a, b) {
    if (a.ohneZeit || b.ohneZeit) {
      return { art: 'offen', a: a, b: b };
    }
    var ende = new Date(a.anwurf.getTime() + SPIELDAUER * 60000);
    var puffer = Math.round((b.anwurf - ende) / 60000);
    var km = entfernung(a.punkt, b.punkt);
    // Ohne Koordinaten koennen wir die Fahrt nicht schaetzen; gleiche Halle
    // erkennen wir dann wenigstens am Namen.
    var weg = km === null ? (a.halle && a.halle === b.halle ? 0 : null) : km;
    var brauche = weg === null ? RUESTZEIT : fahrzeit(weg);

    if (puffer < 0) return { art: 'hart', a: a, b: b, ueberschnitt: -puffer, km: weg,
                             gleichzeitig: a.anwurf.getTime() === b.anwurf.getTime() };
    // Dieselbe Halle nacheinander ist der normale Doppelspieltag, kein
    // Problem - man bleibt einfach sitzen.
    if (weg !== null && weg < 1) return null;
    if (puffer < brauche) return { art: 'hart', a: a, b: b, puffer: puffer, brauche: brauche, km: weg };
    if (puffer < brauche + 30) return { art: 'knapp', a: a, b: b, puffer: puffer, brauche: brauche, km: weg };
    return null;
  }

  function findeKonflikte(spiele) {
    var nachTag = {}, funde = [];
    spiele.forEach(function (s) {
      (nachTag[s.tag] = nachTag[s.tag] || []).push(s);
    });
    Object.keys(nachTag).sort().forEach(function (tag) {
      var liste = nachTag[tag];
      if (liste.length < 2) return;
      for (var i = 0; i < liste.length; i++) {
        for (var j = i + 1; j < liste.length; j++) {
          // Zwei Spiele derselben Mannschaft an einem Tag sind ein
          // Turniertag, kein Konflikt.
          if (liste[i].roh.m === liste[j].roh.m) continue;
          var fund = pruefePaar(liste[i], liste[j]);
          if (fund) funde.push(fund);
        }
      }
    });
    return funde;
  }

  function langesDatum(d) {
    return TAGE[d.getDay()] + ', ' + d.getDate() + '. ' + MONATE[d.getMonth()];
  }

  function konfliktText(k) {
    var a = k.a, b = k.b;
    var wo = a.halle && b.halle && a.halle !== b.halle;
    if (k.art === 'offen') {
      return '<strong>' + esc(langesDatum(a.anwurf)) + '</strong> spielen '
        + esc(a.mannschaft) + ' und ' + esc(b.mannschaft)
        + ' am selben Tag. Für eines der beiden steht die Anwurfzeit noch nicht fest.';
    }
    var kopf = '<strong>' + esc(langesDatum(a.anwurf)) + '</strong> '
      + esc(a.mannschaft) + ' um ' + uhr(a.anwurf)
      + (a.halle ? ' in ' + esc(a.halle) : '')
      + ', ' + esc(b.mannschaft) + ' um ' + uhr(b.anwurf)
      + (b.halle ? ' in ' + esc(b.halle) : '') + '.';
    var schluss;
    if (k.gleichzeitig) {
      schluss = ' Zeitgleich' + (wo ? ' und an verschiedenen Orten.' : '.');
    } else if (k.ueberschnitt !== undefined) {
      schluss = ' Die Spiele überschneiden sich um etwa '
        + k.ueberschnitt + ' Minuten.';
    } else {
      schluss = ' Zwischen Abpfiff und Anwurf ' + (k.puffer === 1 ? 'liegt' : 'liegen') + ' '
        + k.puffer + (k.puffer === 1 ? ' Minute' : ' Minuten');
      // Ohne die Fahrzeit daneben liest sich "135 Minuten Puffer" wie
      // reichlich Zeit, obwohl die Strecke 120 km lang ist.
      if (wo && k.km !== null && k.km !== undefined && k.km >= 2) {
        schluss += ', für die ' + Math.round(k.km) + ' km dazwischen braucht man '
          + 'etwa ' + dauerWort(k.brauche) + '.';
      } else {
        schluss += '.';
      }
      if (k.art === 'knapp') schluss += ' Machbar, aber ohne Umweg.';
    }
    return kopf + schluss;
  }

  function spielZeile(s) {
    var frage = encodeURIComponent(((s.halle || '') + ' ' + (s.ort || '')).trim());
    var halle = !s.halle ? '<div class="halle">Halle noch offen</div>'
      : '<div class="halle"><a href="https://www.google.com/maps/search/?api=1&query='
        + frage + '" target="_blank" rel="noopener">' + esc(s.halle) + '</a></div>';
    return '<div class="spiel' + (s.warnung ? ' stoerung' : '') + '">'
      + '<div class="datum">' + TAGE[s.anwurf.getDay()] + ' '
      + zweistellig(s.anwurf.getDate()) + '.' + zweistellig(s.anwurf.getMonth() + 1) + '.'
      + '<span>' + (s.ohneZeit ? 'offen' : uhr(s.anwurf)) + '</span></div>'
      + '<div><div class="wessen"><a class="zurmannschaft" href="#'
      + esc(s.roh.m) + '">' + esc(s.mannschaft) + '</a></div>'
      + '<div class="gegner">' + esc(s.gegner) + '</div>' + halle + '</div>'
      + '<div class="rechts"><div class="hz' + (s.heim ? ' heim' : '') + '">'
      + (s.heim ? 'H' : 'A') + '</div></div></div>';
  }

  function zeichne() {
    var meine = angeheftet();
    var spiele = kommende();
    var konflikte = findeKonflikte(spiele);
    konflikte.forEach(function (k) { k.a.warnung = true; k.b.warnung = true; });

    var kopf = document.getElementById('meine-kopf');
    if (kopf) {
      kopf.textContent = meine.length === 1 ? 'Eine angeheftete Mannschaft'
        : meine.length + ' angeheftete Mannschaften';
    }

    var teile = [];
    if (!spiele.length) {
      teile.push('<p class="leer">Für die angehefteten Mannschaften steht '
        + 'kein Spiel mehr an.</p>');
    } else {
      var naechstes = spiele[0];
      teile.push('<div class="naechstes"><p class="wann">Als Nächstes</p>'
        + '<p class="wer">' + esc(naechstes.mannschaft) + '</p>'
        + '<p class="gegen">' + (naechstes.heim ? 'gegen ' : 'bei ') + esc(naechstes.gegner)
        + '</p><p class="dann">' + esc(langesDatum(naechstes.anwurf))
        + (naechstes.ohneZeit ? ', Uhrzeit noch offen' : ', ' + uhr(naechstes.anwurf) + ' Uhr')
        + (naechstes.halle ? ' &middot; ' + esc(naechstes.halle) : '') + '</p></div>');

      if (konflikte.length) {
        // Bei zwei Mannschaften kommen ueber eine Saison schnell ein Dutzend
        // zusammen. Oben stehen die naechsten, der Rest ist in der Liste
        // markiert - sonst scrollt man am Spielplan vorbei.
        var ZEIGE = 4;
        var rest = konflikte.length - ZEIGE;
        teile.push('<div class="konflikte"><p class="konfliktkopf">'
          + (konflikte.length === 1 ? 'Ein Termin kollidiert'
             : konflikte.length + ' Termine kollidieren') + '</p>'
          + konflikte.slice(0, ZEIGE).map(function (k) {
              return '<p class="konflikt ' + k.art + '">' + konfliktText(k) + '</p>';
            }).join('')
          + (rest > 0 ? '<p class="weitere">' + rest + ' weitere später in der Saison, '
              + 'unten in der Liste markiert.</p>' : '')
          + '</div>');
      }

      var monat = '';
      spiele.forEach(function (s) {
        var m = MONATE[s.anwurf.getMonth()] + ' ' + s.anwurf.getFullYear();
        if (m !== monat) { teile.push('<div class="monat">' + m + '</div>'); monat = m; }
        teile.push(spielZeile(s));
      });
    }
    kasten.innerHTML = teile.join('');
  }

  // Der Eintrag im Auswahlfeld erscheint erst, wenn es etwas zu verschraenken
  // gibt. Bei einer einzigen Mannschaft waere die Liste eine Kopie.
  // Ohne Wink findet das hier niemand: der Eintrag im Auswahlfeld erklaert
  // sich nicht von selbst, und "Anheften" klingt nach Lesezeichen.
  function wink(anzahl) {
    var feld = document.getElementById('anheftwink');
    if (!feld) return;
    if (anzahl === 0) {
      feld.innerHTML = 'Mehrere im Verein? Mannschaften anheften, dann laufen '
        + 'ihre Spielpläne in einer Liste zusammen.';
      feld.hidden = false;
    } else if (anzahl === 1) {
      feld.innerHTML = 'Noch eine Mannschaft anheften, dann zeigt '
        + '<strong>Meine Mannschaften</strong> beide Spielpläne in einer Liste '
        + 'und warnt bei Terminen, die sich in die Quere kommen.';
      feld.hidden = false;
    } else {
      feld.hidden = true;
    }
  }

  window.muruMeineAktualisieren = function () {
    var anzahl = angeheftet().length;
    var genug = anzahl >= 2;
    option.hidden = !genug;
    wink(anzahl);
    if (genug) zeichne();
    return genug;
  };
  window.muruMeineAktualisieren();
})();
"""
