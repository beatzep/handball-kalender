/**
 * Zaehler fuer Hype und Anwesenheit, pro Spiel.
 *
 * Ablage in KV:
 *   hype:<spielnummer>   Zahl als Text
 *   dabei:<spielnummer>  JSON-Liste anonymer Geraete-Kennungen
 *
 * Bewusst ohne Anmeldung: die Geraete-Kennung wird im Browser erzeugt und
 * bleibt dort. Der Zaehler ist damit ein Anhaltspunkt, keine Anwesenheitsliste.
 */

const ERLAUBTE_HERKUNFT = [
  "https://beatzep.github.io",
  "http://localhost:4173",
];

// Obergrenze je Anfrage. Klicks werden im Browser gebuendelt gesendet,
// eine hoehere Zahl kaeme nur von einem Skript.
const MAX_PRO_ANFRAGE = 25;

// Woher der Worker Spieltermine und Ergebnisse kennt. Dieselbe Datei, die
// auch die Seite speist - so gibt es keine zweite Wahrheit und kein Token.
const DATEN_URL = "https://beatzep.github.io/handball-kalender/daten.json";

// Punkte je Tipp. Im Handball sind exakte Ergebnisse selten, darum lohnt
// sich das Risiko deutlich; die blosse Tendenz gibt es fast geschenkt.
const PUNKTE_EXAKT = 10;
const PUNKTE_DIFFERENZ = 5;
const PUNKTE_TENDENZ = 3;

function kopf(request) {
  const herkunft = request.headers.get("Origin") || "";
  return {
    "Access-Control-Allow-Origin": ERLAUBTE_HERKUNFT.includes(herkunft) ? herkunft : "null",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Cache-Control": "no-store",
    "Content-Type": "application/json; charset=utf-8",
  };
}

function antwort(daten, request, status = 200) {
  return new Response(JSON.stringify(daten), { status, headers: kopf(request) });
}

/** Spielnummern sehen aus wie 2627RPBKROERMA0101 - alles andere wird abgewiesen. */
function gueltig(spiel) {
  return typeof spiel === "string" && /^[A-Za-z0-9_-]{4,40}$/.test(spiel);
}

async function zahl(env, schluessel) {
  const wert = await env.ZAEHLER.get(schluessel);
  const n = parseInt(wert || "0", 10);
  return Number.isFinite(n) && n >= 0 ? n : 0;
}

async function liste(env, schluessel) {
  try {
    const wert = JSON.parse((await env.ZAEHLER.get(schluessel)) || "[]");
    return Array.isArray(wert) ? wert : [];
  } catch {
    return [];
  }
}

async function stand(env, spiel) {
  const [hype, dabei] = await Promise.all([
    zahl(env, `hype:${spiel}`),
    liste(env, `dabei:${spiel}`),
  ]);
  return { spiel, hype, dabei: dabei.length };
}

/** Spieldaten holen, eine Stunde zwischengespeichert. */
async function spieldaten() {
  const antwort = await fetch(DATEN_URL, { cf: { cacheTtl: 3600, cacheEverything: true } });
  if (!antwort.ok) throw new Error("Spieldaten nicht erreichbar");
  const roh = await antwort.json();

  const spiele = {};
  for (const mannschaft of Object.values(roh.teams || {})) {
    for (const [code, spiel] of Object.entries(mannschaft.spiele || {})) {
      spiele[code] = {
        datum: spiel.datum,
        gegner: spiel.gegner,
        heim: spiel.heim,
        mannschaft: mannschaft.name,
        ergebnis: spiel.ergebnis || null,
      };
    }
  }
  return spiele;
}

/**
 * Rechnet eine Anwurfzeit ohne Zeitzonenangabe ("2026-08-29T20:00:00",
 * gemeint als Ortszeit) in einen echten Zeitpunkt um.
 *
 * Worker laufen in UTC, ein naiver Date()-Aufruf laege also zwei Stunden
 * daneben. Der Versatz wird nicht ueber Monatsgrenzen geraten, sondern bei
 * der Zeitzonendatenbank erfragt - sonst waere die Nacht der Zeitumstellung
 * eine Stunde falsch.
 */
function alsOrtszeit(naiv) {
  const alsWaereEsUTC = new Date(naiv + "Z").getTime();
  const inBerlin = new Date(alsWaereEsUTC)
    .toLocaleString("sv-SE", { timeZone: "Europe/Berlin" });
  const versatz = new Date(inBerlin.replace(" ", "T") + "Z").getTime() - alsWaereEsUTC;
  return alsWaereEsUTC - versatz;
}

/** Getippt werden kann bis zum Anwurf. */
function angepfiffen(datum) {
  return Date.now() >= alsOrtszeit(datum);
}

function punkte(tipp, ergebnis) {
  if (!tipp || !ergebnis) return 0;
  const [th, tg] = tipp;
  const eh = ergebnis.heim, eg = ergebnis.gast;
  if (th === eh && tg === eg) return PUNKTE_EXAKT;
  if (th - tg === eh - eg) return PUNKTE_DIFFERENZ;
  const richtung = (a, b) => (a > b ? 1 : a < b ? -1 : 0);
  if (richtung(th, tg) === richtung(eh, eg)) return PUNKTE_TENDENZ;
  return 0;
}

async function tipperLesen(env, id) {
  try {
    const wert = JSON.parse((await env.ZAEHLER.get(`tipper:${id}`)) || "null");
    if (wert && typeof wert === "object") return { name: "", tipps: {}, ...wert };
  } catch { /* unbrauchbar gespeichert - wie neu behandeln */ }
  return { name: "", tipps: {} };
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: kopf(request) });
    }

    const url = new URL(request.url);
    const pfad = url.pathname.replace(/\/+$/, "") || "/";

    try {
      if (pfad === "/stand" && request.method === "GET") {
        const spiel = url.searchParams.get("spiel");
        const vergleich = url.searchParams.get("vergleich");
        if (!gueltig(spiel)) return antwort({ fehler: "spiel fehlt" }, request, 400);

        const daten = await stand(env, spiel);
        if (gueltig(vergleich)) {
          daten.vorher = { spiel: vergleich, hype: await zahl(env, `hype:${vergleich}`) };
        }
        return antwort(daten, request);
      }

      if (pfad === "/hype" && request.method === "POST") {
        const { spiel, anzahl } = await request.json();
        if (!gueltig(spiel)) return antwort({ fehler: "spiel fehlt" }, request, 400);

        const zu = Math.min(Math.max(parseInt(anzahl, 10) || 0, 0), MAX_PRO_ANFRAGE);
        const neu = (await zahl(env, `hype:${spiel}`)) + zu;
        await env.ZAEHLER.put(`hype:${spiel}`, String(neu));
        return antwort({ spiel, hype: neu }, request);
      }

      if (pfad === "/dabei" && request.method === "POST") {
        const { spiel, geraet, an } = await request.json();
        if (!gueltig(spiel) || !gueltig(geraet)) {
          return antwort({ fehler: "spiel oder geraet fehlt" }, request, 400);
        }
        const schluessel = `dabei:${spiel}`;
        const bisher = await liste(env, schluessel);
        const ohne = bisher.filter((g) => g !== geraet);
        const neu = an ? [...ohne, geraet] : ohne;
        // Deckel gegen versehentliches Vollschreiben
        await env.ZAEHLER.put(schluessel, JSON.stringify(neu.slice(-200)));
        return antwort({ spiel, dabei: neu.length, an: !!an }, request);
      }

      // ---- Tippspiel ----
      if (pfad === "/tipp" && request.method === "POST") {
        const { geraet, spiel, heim, gast, name } = await request.json();
        if (!gueltig(geraet) || !gueltig(spiel)) {
          return antwort({ fehler: "geraet oder spiel fehlt" }, request, 400);
        }
        const th = parseInt(heim, 10), tg = parseInt(gast, 10);
        if (!Number.isFinite(th) || !Number.isFinite(tg)
            || th < 0 || tg < 0 || th > 99 || tg > 99) {
          return antwort({ fehler: "unmoegliches Ergebnis" }, request, 400);
        }

        const spiele = await spieldaten();
        const partie = spiele[spiel];
        if (!partie) return antwort({ fehler: "unbekanntes Spiel" }, request, 404);
        if (angepfiffen(partie.datum)) {
          return antwort({ fehler: "Das Spiel läuft schon – Tippschluss ist der Anwurf" },
                         request, 409);
        }

        const tipper = await tipperLesen(env, geraet);
        if (typeof name === "string" && name.trim()) {
          tipper.name = name.trim().slice(0, 24);
        }
        tipper.tipps[spiel] = [th, tg];
        await env.ZAEHLER.put(`tipper:${geraet}`, JSON.stringify(tipper));
        return antwort({ spiel, tipp: [th, tg], name: tipper.name }, request);
      }

      if (pfad === "/tipper" && request.method === "GET") {
        const geraet = url.searchParams.get("geraet");
        if (!gueltig(geraet)) return antwort({ fehler: "geraet fehlt" }, request, 400);
        const tipper = await tipperLesen(env, geraet);
        return antwort({ name: tipper.name, tipps: tipper.tipps }, request);
      }

      if (pfad === "/tipptabelle" && request.method === "GET") {
        const spiele = await spieldaten();
        const liste = await env.ZAEHLER.list({ prefix: "tipper:" });

        const eintraege = [];
        for (const schluessel of liste.keys) {
          const id = schluessel.name.slice("tipper:".length);
          const tipper = await tipperLesen(env, id);
          if (!tipper.name) continue;          // ohne Namen nicht in der Tabelle

          let summe = 0, gewertet = 0, exakt = 0;
          for (const [code, tipp] of Object.entries(tipper.tipps)) {
            const partie = spiele[code];
            if (!partie || !partie.ergebnis) continue;
            const p = punkte(tipp, partie.ergebnis);
            summe += p; gewertet += 1;
            if (p === PUNKTE_EXAKT) exakt += 1;
          }
          eintraege.push({ id, name: tipper.name, punkte: summe,
                           spiele: gewertet, exakt,
                           tipps: Object.keys(tipper.tipps).length });
        }

        eintraege.sort((a, b) => b.punkte - a.punkte || b.exakt - a.exakt
                                 || a.name.localeCompare(b.name));
        return antwort({ tabelle: eintraege.map((e, i) => ({ platz: i + 1, ...e })) },
                       request);
      }

      return antwort({ fehler: "unbekannter Pfad" }, request, 404);
    } catch (e) {
      return antwort({ fehler: "Anfrage fehlerhaft" }, request, 400);
    }
  },
};
