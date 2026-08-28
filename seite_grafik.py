"""Zeichnet die Bilder zum Teilen im Browser auf ein Canvas.

Alles entsteht aus den Spieldaten: Wappen, Schrift, Flaechen. Kein
Bildmaterial von aussen, nichts wird hochgeladen.
"""

GRAFIK = """
(function () {
  var knoepfe = [].slice.call(document.querySelectorAll('[data-grafik]'));
  if (!knoepfe.length) return;

  var GOLD = '#dd9933';
  var SCHWARZ = '#14140f';
  var HELL = '#f7f5f0';
  var LEISE = 'rgba(247,245,240,.62)';
  var SCHRIFT = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif';

  var format = 'story';

  document.querySelectorAll('[data-format]').forEach(function (k) {
    k.addEventListener('click', function () {
      format = k.getAttribute('data-format');
      document.querySelectorAll('[data-format]').forEach(function (x) {
        x.setAttribute('aria-pressed', x === k ? 'true' : 'false');
      });
    });
  });

  function schrift(groesse, dicke) {
    return (dicke || 400) + ' ' + Math.round(groesse) + 'px ' + SCHRIFT;
  }

  /** Bricht Text auf mehrere Zeilen um und verkleinert notfalls. */
  function zeilen(ctx, text, breite, groesse, dicke) {
    var versuch = groesse;
    while (versuch > groesse * 0.55) {
      ctx.font = schrift(versuch, dicke);
      var worte = String(text).split(' ');
      var raus = [], zeile = '';
      for (var i = 0; i < worte.length; i++) {
        var neu = zeile ? zeile + ' ' + worte[i] : worte[i];
        if (ctx.measureText(neu).width > breite && zeile) {
          raus.push(zeile); zeile = worte[i];
        } else { zeile = neu; }
      }
      if (zeile) raus.push(zeile);
      var zulang = raus.some(function (z) { return ctx.measureText(z).width > breite; });
      if (!zulang && raus.length <= 3) return { zeilen: raus, groesse: versuch };
      versuch -= groesse * 0.06;
    }
    ctx.font = schrift(versuch, dicke);
    return { zeilen: [String(text)], groesse: versuch };
  }

  function restzeit(ziel) {
    var rest = Math.floor((new Date(ziel).getTime() - Date.now()) / 1000);
    if (rest <= 0) return null;
    var tage = Math.floor(rest / 86400);
    var std = Math.floor((rest % 86400) / 3600);
    if (tage > 0) return 'noch ' + tage + (tage === 1 ? ' Tag ' : ' Tage ') + std + ' Std';
    var min = Math.floor((rest % 3600) / 60);
    return 'noch ' + std + ' Std ' + min + ' Min';
  }

  function wappen() {
    return new Promise(function (fertig) {
      var bild = new Image();
      bild.onload = function () { fertig(bild); };
      bild.onerror = function () { fertig(null); };
      bild.src = 'logo.png';
    });
  }

  /**
   * Zeichnet den Inhalt ab startY und liefert die Endhoehe zurueck.
   * Mit messen=true wird nichts gemalt - so laesst sich der Block vorher
   * ausmessen und anschliessend senkrecht mittig setzen.
   *
   * Alle Texte haengen an textBaseline 'top': bei 'alphabetic' ragen grosse
   * Schriften nach oben in die Zeile darueber, was Ueberschneidungen gibt.
   */
  function inhalt(ctx, d, B, startY, innen, hoch, bild, messen) {
    var y = startY;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';

    function text(inhalt, groesse, dicke, farbe, abstand) {
      var block = zeilen(ctx, inhalt, innen, groesse, dicke);
      ctx.font = schrift(block.groesse, dicke);
      if (!messen) ctx.fillStyle = farbe;
      block.zeilen.forEach(function (z) {
        if (!messen) ctx.fillText(z, B / 2, y);
        y += block.groesse * 1.18;
      });
      y += abstand || 0;
    }

    if (bild) {
      var h = hoch ? 250 : 180;
      var w = h * (bild.width / bild.height);
      if (!messen) ctx.drawImage(bild, (B - w) / 2, y, w, h);
      y += h + (hoch ? 70 : 45);
    }

    var kopf = d.mannschaft + (d.liga ? '  \u00b7  ' + d.liga : '');
    text(kopf.toUpperCase(), hoch ? 34 : 28, 600, GOLD, hoch ? 46 : 32);
    text(d.heim ? 'Heimspiel gegen' : 'Ausw\u00e4rts bei',
         hoch ? 40 : 32, 400, HELL, hoch ? 20 : 14);
    text(d.gegner, hoch ? 104 : 80, 300, HELL, hoch ? 52 : 36);

    if (!messen) { ctx.fillStyle = GOLD; ctx.fillRect(B / 2 - 70, y, 140, 4); }
    y += (hoch ? 66 : 46);

    if (d.art === 'ergebnis') {
      text(d.stand, hoch ? 170 : 130, 300, HELL, hoch ? 16 : 10);
      text(d.ausgang.toUpperCase(), hoch ? 52 : 42, 600, GOLD, hoch ? 46 : 32);
      text(d.datum_text, hoch ? 36 : 30, 400, LEISE, 0);
      text(d.halle, hoch ? 36 : 30, 400, LEISE, 0);
    } else {
      text(d.datum_text, hoch ? 52 : 42, 600, HELL, hoch ? 14 : 10);
      text(d.uhrzeit + ' Uhr', hoch ? 92 : 72, 300, HELL, hoch ? 34 : 24);
      text(d.halle + (d.ort ? ', ' + d.ort : ''), hoch ? 38 : 31, 400, LEISE, 0);
      var rest = restzeit(d.datum);
      if (rest) {
        y += hoch ? 44 : 30;
        text(rest, hoch ? 56 : 46, 600, GOLD, 0);
      }
    }
    return y;
  }

  function zeichne(d, bild) {
    var hoch = format === 'story';
    var B = 1080, H = hoch ? 1920 : 1080;
    var c = document.createElement('canvas');
    c.width = B; c.height = H;
    var ctx = c.getContext('2d');
    var rand = 90, innen = B - rand * 2;
    var fussraum = hoch ? 150 : 120;

    ctx.fillStyle = SCHWARZ; ctx.fillRect(0, 0, B, H);
    ctx.fillStyle = GOLD; ctx.fillRect(0, 0, B, 12);
    ctx.fillRect(0, H - 12, B, 12);

    // erst ausmessen, dann mittig setzen
    var hoehe = inhalt(ctx, d, B, 0, innen, hoch, bild, true);
    var start = Math.max(hoch ? 120 : 70, (H - fussraum - hoehe) / 2);
    inhalt(ctx, d, B, start, innen, hoch, bild, false);

    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillStyle = LEISE;
    ctx.font = schrift(hoch ? 30 : 26, 400);
    ctx.fillText(d.verein, B / 2, H - (hoch ? 100 : 78));
    return c;
  }

  function dateiname(d) {
    var t = new Date(d.datum);
    var stueck = [d.art === 'ergebnis' ? 'ergebnis' : 'spiel',
                  t.getFullYear() + '-' + ('0' + (t.getMonth() + 1)).slice(-2) +
                  '-' + ('0' + t.getDate()).slice(-2),
                  d.gegner.toLowerCase().replace(/[^a-z0-9]+/g, '-')];
    return 'muru-' + stueck.join('-').replace(/-+/g, '-') + '.png';
  }

  knoepfe.forEach(function (knopf) {
    knopf.addEventListener('click', function () {
      var d;
      try { d = JSON.parse(knopf.getAttribute('data-grafik')); }
      catch (e) { return; }
      var alt = knopf.textContent;
      knopf.textContent = 'Bild wird erstellt …';

      wappen().then(function (bild) {
        var c = zeichne(d, bild);
        c.toBlob(function (blob) {
          if (!blob) { knopf.textContent = alt; return; }
          var datei = new File([blob], dateiname(d), { type: 'image/png' });
          knopf.textContent = alt;

          if (navigator.canShare && navigator.canShare({ files: [datei] })) {
            navigator.share({ files: [datei] }).catch(function () {});
            return;
          }
          var url = URL.createObjectURL(blob);
          var a = document.createElement('a');
          a.href = url; a.download = datei.name;
          document.body.appendChild(a); a.click(); a.remove();
          setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
        }, 'image/png');
      });
    });
  });
})();
"""
