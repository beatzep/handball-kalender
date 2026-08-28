"""Stylesheet der Abo-Seite. Ausgelagert, damit baue_seite.py lesbar bleibt.

Farben vom Verein (#DD9933 Gold, Schwarz, Warmweiss), Formensprache nach
mckinsey.de: durchgaengig border-radius 0, keine umrandeten Karten,
Gliederung ueber Weissraum und 1px-Linien. Mobil zuerst.
"""

STIL = """
:root {
  --gold: #dd9933; --gold-tief: #b87a22; --gold-schwach: rgba(221,153,51,.10);
  --tinte: #14140f; --tinte-weich: #4a4a42; --leise: #7a776d;
  --linie: #dedbd3; --linie-zart: #ebe9e3;
  --grund: #ffffff; --schwarz: #14140f; --auf-schwarz: #f7f5f0;
  --sieg: #2f7d4f; --niederlage: #a4443a;
}
@media (prefers-color-scheme: dark) {
  :root {
    --gold: #e8ac52; --gold-tief: #dd9933; --gold-schwach: rgba(232,172,82,.12);
    --tinte: #f2efe8; --tinte-weich: #b8b4a9; --leise: #8c877c;
    --linie: #33312b; --linie-zart: #24221e;
    --grund: #0d0d0b; --schwarz: #000000; --auf-schwarz: #f2efe8;
    --sieg: #5cbf85; --niederlage: #e08076;
  }
}
*, *::before, *::after { box-sizing: border-box; border-radius: 0; }

/* Ohne touch-action deutet das Handy zwei schnelle Tipps auf denselben
   Knopf als Doppeltipp und zoomt - beim Hype-Zaehler klickt man aber
   absichtlich schnell hintereinander. */
button, .knopf, select, a.knopf {
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
  -webkit-user-select: none;
  user-select: none;
}
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; background: var(--grund); color: var(--tinte);
  font: 400 17px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        "Helvetica Neue", Arial, sans-serif;
  font-variant-numeric: tabular-nums; -webkit-font-smoothing: antialiased;
}
.huelle { max-width: 720px; margin: 0 auto; padding: 0 22px; }
a { color: inherit; }
[hidden] { display: none !important; }

/* ---------- Kopf ---------- */
.kopf { background: var(--schwarz); color: var(--auf-schwarz);
        border-bottom: 2px solid var(--gold); }
.kopf .huelle { padding: 26px 22px 30px; }
.marke { display: flex; align-items: center; gap: 14px; margin-bottom: 28px; }
.marke img { width: 54px; height: auto; display: block; }
.marke .zeile1 { font-size: .82rem; font-weight: 600; letter-spacing: .04em;
                 color: var(--gold); line-height: 1.3; }
.marke .zeile2 { font-size: .78rem; color: rgba(247,245,240,.55); line-height: 1.3; }
.kopf h1 { margin: 0; font-size: clamp(2.1rem, 11vw, 3.2rem); font-weight: 300;
           line-height: 1.04; letter-spacing: -.015em; }
.kopf .saison { margin: 12px 0 0; font-size: .92rem; color: rgba(247,245,240,.62); }

/* ---------- Mannschaftswahl ---------- */
.wahl { margin: 24px 0 0; }
.wahl label { display: block; font-size: .74rem; font-weight: 600;
              letter-spacing: .08em; text-transform: uppercase;
              color: rgba(247,245,240,.5); margin-bottom: 8px; }
.wahl select {
  appearance: none; -webkit-appearance: none; width: 100%;
  font: inherit; font-size: 1.05rem; font-weight: 600;
  color: var(--auf-schwarz); background: transparent;
  border: 1px solid rgba(247,245,240,.28); padding: 13px 44px 13px 14px;
  background-image: linear-gradient(45deg, transparent 50%, var(--gold) 50%),
                    linear-gradient(135deg, var(--gold) 50%, transparent 50%);
  background-position: calc(100% - 21px) 22px, calc(100% - 15px) 22px;
  background-size: 6px 6px, 6px 6px; background-repeat: no-repeat;
}
.wahl select:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }
.wahl select option { color: #14140f; background: #fff; }

/* ---------- Abschnitte ---------- */
.liga { margin: 28px 0 0; font-size: .88rem; font-weight: 600;
        letter-spacing: .04em; color: var(--gold-tief); }
.teil { padding: 34px 0 0; }
.rubrik { border-top: 1px solid var(--linie); padding-top: 14px; margin-bottom: 24px;
          font-size: .95rem; font-weight: 600; color: var(--leise); }

/* ---------- Nächstes Spiel ---------- */
.marker { font-size: .82rem; font-weight: 600; color: var(--gold-tief);
          letter-spacing: .04em; margin: 22px 0 10px; }
.paarung { font-size: clamp(1.5rem, 7vw, 2rem); font-weight: 400; line-height: 1.16;
           letter-spacing: -.01em; margin: 0 0 22px; overflow-wrap: anywhere; }
.fakten { margin: 0; }
.fakten > div { display: flex; gap: 18px; padding: 11px 0;
                border-top: 1px solid var(--linie-zart); font-size: .95rem; }
.fakten dt { flex: 0 0 78px; color: var(--leise); }
.fakten dd { margin: 0; flex: 1; }
.fakten a { color: inherit; text-decoration: none;
            box-shadow: inset 0 -1px 0 var(--gold); }

/* ---------- Reiter ---------- */
.reiter { position: sticky; top: 0; z-index: 5; background: var(--grund);
          border-bottom: 1px solid var(--linie); display: flex;
          overflow-x: auto; scrollbar-width: none; margin-top: 32px; }
.reiter::-webkit-scrollbar { display: none; }
.reiter button {
  flex: 0 0 auto; font: inherit; font-size: .92rem; font-weight: 500;
  background: none; border: 0; border-bottom: 2px solid transparent;
  color: var(--leise); padding: 15px 18px 13px; margin-bottom: -1px;
  white-space: nowrap; cursor: pointer;
}
.reiter button:first-child { padding-left: 0; }
.reiter button[aria-selected="true"] { color: var(--tinte); border-bottom-color: var(--gold); }
.reiter button:focus-visible { outline: 2px solid var(--gold-tief); outline-offset: -4px; }

/* ---------- Abo-Wege ---------- */
.weg { padding: 26px 0; border-top: 1px solid var(--linie-zart); }
.rubrik + .weg { border-top: 0; padding-top: 0; }
.weg h3 { margin: 0 0 6px; font-size: 1.12rem; font-weight: 600; }
.weg p { margin: 0 0 18px; font-size: .95rem; color: var(--tinte-weich); }
.knopf {
  display: block; width: 100%; text-align: center; text-decoration: none;
  font: inherit; font-size: 1rem; font-weight: 600; padding: 16px 20px;
  border: 1px solid var(--gold); background: var(--gold); color: #14140f;
  cursor: pointer; transition: background .15s ease;
}
.knopf:hover { background: var(--gold-tief); border-color: var(--gold-tief); }
.knopf.stumm { background: transparent; color: var(--tinte); border-color: var(--tinte); }
.knopf.stumm:hover { background: var(--gold-schwach); border-color: var(--gold); }
.knopf:focus-visible { outline: 2px solid var(--gold-tief); outline-offset: 3px; }
.schritte { margin: 18px 0 0; padding: 0; list-style: none; font-size: .92rem;
            color: var(--tinte-weich); counter-reset: schritt; }
.schritte li { counter-increment: schritt; position: relative;
               padding: 8px 0 8px 34px; border-top: 1px solid var(--linie-zart); }
.schritte li::before { content: counter(schritt); position: absolute; left: 0; top: 8px;
                       font-size: .82rem; font-weight: 600; color: var(--gold-tief); }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .88em; }

/* ---------- Änderungen ---------- */
.hinweis { border-left: 2px solid var(--gold); padding: 4px 0 4px 18px; margin: 26px 0 0; }
.hinweis h3 { margin: 0 0 8px; font-size: .82rem; font-weight: 600;
              letter-spacing: .04em; color: var(--gold-tief); }
.hinweis ul { margin: 0 0 14px; padding-left: 18px; font-size: .95rem; }
.hinweis li { margin: 5px 0; }
.hinweis button { font: inherit; font-size: .88rem; font-weight: 600;
                  background: none; border: 1px solid var(--linie);
                  color: var(--tinte); padding: 9px 16px; cursor: pointer; }
.hinweis button:hover { border-color: var(--gold); background: var(--gold-schwach); }

/* ---------- Spielplan ---------- */
.monat { font-size: .82rem; font-weight: 600; letter-spacing: .06em;
         text-transform: uppercase; color: var(--leise); padding: 28px 0 10px; }
.monat:first-child { padding-top: 4px; }
.spiel { display: grid; grid-template-columns: 58px 1fr auto; gap: 0 14px;
         align-items: start; padding: 15px 0; border-top: 1px solid var(--linie); }
.spiel .datum { font-size: .88rem; font-weight: 600; line-height: 1.3; }
.spiel .datum span { display: block; font-weight: 400; color: var(--leise); }
.spiel .gegner { font-size: 1.02rem; font-weight: 500; line-height: 1.3;
                 overflow-wrap: anywhere; }
.spiel .halle { font-size: .88rem; color: var(--leise); margin-top: 3px; }
.spiel .halle a { text-decoration: none; box-shadow: inset 0 -1px 0 var(--linie); }
.spiel .halle a:hover { box-shadow: inset 0 -1px 0 var(--gold); }
.rechts { text-align: right; min-width: 46px; }
.hz { font-size: .78rem; font-weight: 600; color: var(--leise); }
.hz.heim { color: var(--gold-tief); }
.stand { font-size: .95rem; font-weight: 700; margin-top: 2px; white-space: nowrap; }
.stand.S { color: var(--sieg); }
.stand.N { color: var(--niederlage); }
.spiel.vorbei { opacity: .55; }
.spiel.vorbei .gegner { font-weight: 400; }
.spiel.jetzt { border-top-color: var(--gold); box-shadow: inset 0 2px 0 var(--gold); }

/* ---------- Form und Verlauf ---------- */
.form { display: flex; align-items: baseline; gap: 10px; margin-bottom: 26px;
        flex-wrap: wrap; }
.form .titel { font-size: .74rem; font-weight: 600; letter-spacing: .06em;
               text-transform: uppercase; color: var(--leise); }
.form .kette { display: flex; gap: 5px; }
.form b { width: 25px; height: 25px; line-height: 25px; text-align: center;
          font-size: .76rem; font-weight: 700; border: 1px solid; }
.form b.S { color: var(--sieg); border-color: var(--sieg); }
.form b.N { color: var(--niederlage); border-color: var(--niederlage); }
.form b.U { color: var(--leise); border-color: var(--linie); }

.verlauf { margin: 0 0 30px; }
.verlauf .titel { font-size: .74rem; font-weight: 600; letter-spacing: .06em;
                  text-transform: uppercase; color: var(--leise);
                  margin-bottom: 12px; }
.verlauf svg { width: 100%; height: auto; display: block; overflow: visible; }
.verlauf .gitter { stroke: var(--linie-zart); stroke-width: 1; }
.verlauf .linie { fill: none; stroke: var(--gold); stroke-width: 2;
                  stroke-linejoin: round; stroke-linecap: round; }
.verlauf .punkt { fill: var(--gold); }
.verlauf text { fill: var(--leise); font-size: 11px;
                font-family: inherit; font-variant-numeric: tabular-nums; }
.verlauf .jetzt { fill: var(--tinte); font-weight: 700; }




/* ---------- Statistik ---------- */
.kennzahlen { display: grid; grid-template-columns: 1fr 1fr; gap: 22px 18px;
              margin: 0 0 8px; }
.kennzahlen > div { min-width: 0; }
.kennzahlen dt { font-size: .72rem; font-weight: 600; letter-spacing: .05em;
                 text-transform: uppercase; color: var(--leise); }
.kennzahlen dd { margin: 4px 0 0; font-size: 1.7rem; font-weight: 300;
                 line-height: 1.05; letter-spacing: -.02em; }
.kennzahlen dd .klein { font-size: .95rem; color: var(--leise); font-weight: 400; }
.kennzahlen .zusatz { display: block; margin-top: 4px; font-size: .82rem;
                      color: var(--leise); line-height: 1.35; }
.kennzahlen .breit { grid-column: 1 / -1; }

.verbrauch { margin: 26px 0 0; padding: 22px 0; border-top: 1px solid var(--linie);
             border-bottom: 1px solid var(--linie); }
.verbrauch .wert { font-size: 2.6rem; font-weight: 300; line-height: 1;
                   letter-spacing: -.03em; color: var(--gold-tief); }
.verbrauch .einheit { font-size: 1rem; color: var(--leise); margin-left: 6px; }
.verbrauch .rechnung { margin: 14px 0 0; font-size: .86rem; color: var(--tinte-weich);
                       line-height: 1.5; }
.verbrauch .pointe { margin: 8px 0 0; font-size: .86rem; color: var(--leise);
                     font-style: italic; }

.statfuss { margin: 18px 0 0; font-size: .8rem; color: var(--leise); line-height: 1.45; }

/* ---------- Countdown, Hinspiel, Gegner ---------- */
.countdown {
  font-size: 1.05rem; font-weight: 600; color: var(--tinte);
  margin: 0 0 20px; font-variant-numeric: tabular-nums;
}
.countdown .einheit { color: var(--leise); font-weight: 400; font-size: .92rem; }

.vorschau { margin: 26px 0 0; padding-top: 22px; border-top: 1px solid var(--linie-zart); }
.vorschau h3 {
  margin: 0 0 12px; font-size: .74rem; font-weight: 600; letter-spacing: .06em;
  text-transform: uppercase; color: var(--leise);
}
.hinspiel { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;
            margin-bottom: 18px; }
.hinspiel .stand { font-size: 1.15rem; font-weight: 700; }
.hinspiel .wo { font-size: .9rem; color: var(--leise); }
.hinspiel a { font-size: .88rem; color: var(--gold-tief); text-decoration: none;
              box-shadow: inset 0 -1px 0 var(--gold); }
.hinspiel a:hover { color: var(--tinte); }

.gegnerdaten { display: flex; gap: 24px; flex-wrap: wrap; margin: 0; }
.gegnerdaten div { margin: 0; }
.gegnerdaten dt { font-size: .74rem; color: var(--leise); letter-spacing: .04em;
                  text-transform: uppercase; }
.gegnerdaten dd { margin: 2px 0 0; font-size: 1.05rem; font-weight: 600; }

/* ---------- Hype und Zusagen ---------- */
.mitmachen { margin: 30px 0 0; padding: 22px 0 0; border-top: 1px solid var(--linie); }
.hype .titel, .dabei .titel {
  font-size: .74rem; font-weight: 600; letter-spacing: .06em;
  text-transform: uppercase; color: var(--leise); margin-bottom: 10px;
}
.hype .zahl {
  font-size: 2.4rem; font-weight: 300; line-height: 1; letter-spacing: -.02em;
  color: var(--gold-tief);
}
.hype .vergleich { font-size: .86rem; color: var(--leise); margin-left: 10px; }
.hype .knoepfe { display: flex; gap: 10px; margin-top: 16px; flex-wrap: wrap; }
.hype .knoepfe button {
  font-size: 1.5rem; line-height: 1; background: none; cursor: pointer;
  border: 1px solid var(--linie); padding: 10px 0; width: 58px; height: 52px;
  transition: border-color .12s ease, transform .08s ease;
}
.hype .knoepfe button:hover { border-color: var(--gold); }
.hype .knoepfe button:active { transform: scale(.92); border-color: var(--gold); }
.hype .knoepfe button:focus-visible { outline: 2px solid var(--gold-tief); outline-offset: 2px; }
.hype .bahn { position: relative; height: 0; }
.hype .flug {
  position: absolute; font-size: 1.5rem; pointer-events: none;
  animation: aufsteigen 1s ease-out forwards;
}
@keyframes aufsteigen {
  from { transform: translateY(0) scale(1); opacity: .9; }
  to   { transform: translateY(-70px) scale(1.5); opacity: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .hype .flug { animation-duration: .01ms; }
  .hype .knoepfe button:active { transform: none; }
}

.dabei { margin-top: 28px; }
.dabei .reihe { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.dabei button {
  font: inherit; font-size: .95rem; font-weight: 600; cursor: pointer;
  background: transparent; color: var(--tinte);
  border: 1px solid var(--tinte); padding: 12px 20px;
}
.dabei button:hover { border-color: var(--gold); background: var(--gold-schwach); }
.dabei button[aria-pressed="true"] {
  background: var(--gold); border-color: var(--gold); color: #14140f;
}
.dabei button:focus-visible { outline: 2px solid var(--gold-tief); outline-offset: 2px; }
.dabei .anzahl { font-size: .95rem; color: var(--tinte-weich); }
.dabei .fussnote { margin: 10px 0 0; font-size: .82rem; color: var(--leise); }

/* ---------- Tabelle ---------- */
.tabellenhuelle { overflow-x: auto; }
table.tabelle { width: 100%; border-collapse: collapse; font-size: .92rem; }
table.tabelle th { text-align: right; font-size: .74rem; font-weight: 600;
                   letter-spacing: .06em; text-transform: uppercase; color: var(--leise);
                   padding: 0 0 10px; border-bottom: 1px solid var(--linie);
                   white-space: nowrap; }
table.tabelle th.platz { text-align: left; width: 26px; }
table.tabelle th.mann { text-align: left; }
table.tabelle td { padding: 11px 0; border-bottom: 1px solid var(--linie-zart);
                   text-align: right; white-space: nowrap; }
table.tabelle td.platz { text-align: left; color: var(--leise); font-size: .86rem; }
table.tabelle td.mann { text-align: left; white-space: normal;
                        overflow-wrap: anywhere; padding-right: 12px; line-height: 1.3; }
table.tabelle td + td, table.tabelle th + th { padding-left: 12px; }
table.tabelle td.pkt { font-weight: 600; }
table.tabelle tr.wir td { background: var(--gold-schwach); font-weight: 600; }
table.tabelle tr.wir td.platz { box-shadow: inset 2px 0 0 var(--gold); }
.tabellenfuss { margin: 14px 0 0; font-size: .84rem; color: var(--leise); }
.nur-breit { display: none; }
@media (min-width: 560px) { .nur-breit { display: table-cell; } }

/* ---------- Tipp / Fuß ---------- */
.tipp { margin: 26px 0 0; padding: 16px 0 0; border-top: 1px solid var(--linie-zart);
        font-size: .9rem; color: var(--tinte-weich); }
.tipp b { font-weight: 600; color: var(--tinte); }
.fuss { margin: 46px 0 0; padding: 20px 0 46px; border-top: 1px solid var(--linie);
        font-size: .88rem; color: var(--leise); }
.fuss a { color: var(--leise); }

@media (min-width: 640px) {
  .kopf .huelle { padding: 34px 22px 40px; }
  .fakten dt { flex: 0 0 110px; }
  .knopf { display: inline-block; width: auto; min-width: 280px; }
  .wahl select { max-width: 320px; }
}
"""
