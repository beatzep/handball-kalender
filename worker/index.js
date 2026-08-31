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

// Der Speicher vertraegt im kostenlosen Tarif rund 1.000 Schreibvorgaenge
// am Tag und nur einen je Sekunde auf denselben Schluessel. Die Tageszaehler
// werden darum auf mehrere Schluessel verteilt; beim Auswerten wieder
// zusammengezaehlt. Lesen ist praktisch unbegrenzt.
const STAT_TEILE = 10;

// Was gezaehlt wird - alles andere wird verworfen. Es gibt keine Kennung,
// keine Adresse, keinen Zeitstempel je Besuch: nur Summen pro Tag.
const STAT_EREIGNISSE = ["aufruf", "abo", "datei", "grafik", "tipp",
                         "hype", "dabei", "teilen"];
// Frueher eine feste Liste aus drei Namen. Seit der Verein mit allen 23
// Mannschaften auf der Seite steht, fiel damit jeder Jugend-Aufruf still aus
// der Zaehlung. Statt die Liste zu pflegen wird die Form geprueft; die
// Anzahl je Anfrage ist gedeckelt, damit niemand den Speicher vollschreibt.
const MANNSCHAFT_FORM = /^[a-z][a-z0-9-]{1,14}$/;
const MANNSCHAFTEN_JE_ANFRAGE = 8;
const STAT_BEREICHE = ["kalender", "spiele", "tabelle", "statistik"];

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
// Namen fuer die Tipptabelle
// ---------------------------------------------------------------------
// Es gibt keine Freigabe vor der Veroeffentlichung: wer tippt, steht sofort
// fuer alle sichtbar in der Wertung. Am ersten Spieltag hat das prompt
// jemand ausgenutzt.
//
// Der Filter ist bewusst grob. Er haelt die uebliche Ladung ab, nicht jeden
// Einfall - wer will, findet einen Weg daran vorbei. Dafuer gibt es die
// Loeschmoeglichkeit im Adminbereich. Umgekehrt gilt: lieber einmal zu viel
// abgelehnt als ein Schimpfwort auf der Vereinsseite; abgelehnt wird mit
// klarer Ansage, ein anderer Name ist schnell getippt.
const SCHIMPFWOERTER = [
  // deutsch
  "arschloch", "arsch", "wichser", "wichsen", "hurensohn", "hure", "nutte",
  "fotze", "fick", "ficken", "schlampe", "missgeburt", "spast", "spasti",
  "behindert", "mongo", "kanake", "neger", "schwuchtel", "schwanz", "penis",
  "muschi", "titten", "scheisse", "scheiss", "kacke", "pisser", "bastard",
  "hodensack", "sackgesicht", "vollpfosten", "hitler", "nazi", "heilhitler",
  // englisch
  // "dick" fehlt bewusst: Dick, Dickmann und Dickel sind haeufige deutsche
  // Nachnamen, das englische Schimpfwort waere hier selten. Umgekehrt sind
  // "fick" und "kacke" drin, obwohl es die Nachnamen Fick und Kackert gibt -
  // die sind so selten, dass die Abwaegung andersherum ausfaellt.
  "fuck", "shit", "bitch", "cunt", "cock", "pussy", "asshole",
  "bastard", "whore", "slut", "nigger", "nigga", "faggot", "retard",
  "porn", "sex", "boob", "tits", "anal", "blowjob", "wank",
];

/**
 * Vergleichsform eines Namens: Kleinschreibung, Umlaute aufgeloest,
 * Ziffern und Zeichen zurueckuebersetzt, alles Uebrige entfernt.
 *
 * Ohne diesen Schritt genuegt "W1chs3r" oder "f.u.c.k", um vorbeizukommen.
 */
function vergleichsform(text) {
  return String(text)
    .toLowerCase()
    .replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss")
    .replace(/[013457@$!|]/g, (z) => ({
      "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t",
      "@": "a", "$": "s", "!": "i", "|": "i",
    }[z]))
    .replace(/[^a-z]/g, "")
    // Verdoppelte Buchstaben zusammenziehen: sonst genuegt "Wichsser" oder
    // "fuuuck". Harmlose Namen leiden nicht darunter - aus Bußer wird
    // "buser", aus Assmann "asman".
    .replace(/(.)\1+/g, "$1");
}

/** Faellt der Name durch, kommt der Grund zurueck - sonst null. */
function anstoessig(name) {
  const form = vergleichsform(name);
  if (!form) return null;
  for (const wort of SCHIMPFWOERTER) {
    // Die Liste durchlaeuft dieselbe Form, sonst fiele "titten" (doppeltes t)
    // durch das eigene Raster.
    if (form.includes(vergleichsform(wort))) return wort;
  }
  return null;
}

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
  for (const [schluessel, mannschaft] of Object.entries(roh.teams || {})) {
    for (const [code, spiel] of Object.entries(mannschaft.spiele || {})) {
      spiele[code] = {
        datum: spiel.datum,
        gegner: spiel.gegner,
        heim: spiel.heim,
        mannschaft: mannschaft.name,
        schluessel: schluessel,
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

/**
 * Liest einen gespeicherten Tipp als [heim, gast].
 *
 * Erwartet wird ein Array, aber im Speicher liegen Eintraege, die anders
 * aussehen. Ein einziger davon hat frueher die ganze Tabelle mit HTTP 400
 * lahmgelegt, weil das Destructuring warf. Was sich deuten laesst, wird
 * gedeutet - lieber die Punkte eines Tippers retten als ihn wegzuwerfen.
 * Was sich nicht deuten laesst, gibt null und wird uebersprungen.
 */
function alsTipp(wert) {
  const zahl = (x) => {
    const n = typeof x === "string" ? parseInt(x, 10) : x;
    return Number.isFinite(n) ? n : null;
  };
  if (Array.isArray(wert) && wert.length >= 2) {
    const h = zahl(wert[0]), g = zahl(wert[1]);
    return h === null || g === null ? null : [h, g];
  }
  if (wert && typeof wert === "object") {
    const h = zahl(wert.heim ?? wert.h), g = zahl(wert.gast ?? wert.g);
    return h === null || g === null ? null : [h, g];
  }
  if (typeof wert === "string") {
    const teile = wert.split(/[:\-]/);
    if (teile.length === 2) {
      const h = zahl(teile[0]), g = zahl(teile[1]);
      return h === null || g === null ? null : [h, g];
    }
  }
  return null;
}

function punkte(rohTipp, ergebnis) {
  const tipp = alsTipp(rohTipp);
  if (!tipp || !ergebnis) return 0;
  const [th, tg] = tipp;
  const eh = ergebnis.heim, eg = ergebnis.gast;
  if (!Number.isFinite(eh) || !Number.isFinite(eg)) return 0;
  if (th === eh && tg === eg) return PUNKTE_EXAKT;
  if (th - tg === eh - eg) return PUNKTE_DIFFERENZ;
  const richtung = (a, b) => (a > b ? 1 : a < b ? -1 : 0);
  if (richtung(th, tg) === richtung(eh, eg)) return PUNKTE_TENDENZ;
  return 0;
}

// Wer getippt hat, steht zusaetzlich in einer Liste. Ohne sie braucht
// jeder Abruf der Tabelle ein list() - davon erlaubt der kostenlose Tarif
// 1.000 am Tag, und die Seite kam auf 24 pro Seitenaufruf. Nach gut vierzig
// Besuchern war die Tipptabelle bis Mitternacht tot.
//
// Die Liste ist nur eine Abkuerzung, nicht die Wahrheit: massgeblich
// bleiben die Eintraege "tipper:<id>". Faellt sie aus oder ist sie
// veraltet, wird sie aus dem Speicher neu aufgebaut.
const INDEX_SCHLUESSEL = "tipper-index";     // ohne "tipper:", sonst listet er sich selbst
const INDEX_FRISCH_MS = 6 * 60 * 60 * 1000;

const INDEX_SPERRE_MS = 60 * 60 * 1000;      // nach einem Fehlschlag Ruhe geben

async function indexLesen(env) {
  try {
    const roh = JSON.parse((await env.ZAEHLER.get(INDEX_SCHLUESSEL)) || "null");
    if (roh && Array.isArray(roh.ids)) {
      return {
        stand: Number(roh.stand) || 0,
        gesperrtBis: Number(roh.gesperrtBis) || 0,
        ids: roh.ids.filter(x => typeof x === "string"),
      };
    }
  } catch { /* neu aufbauen */ }
  return null;
}

async function indexSchreiben(env, index) {
  await env.ZAEHLER.put(INDEX_SCHLUESSEL, JSON.stringify(index));
}

/** Liefert alle Tipper-Kennungen und haelt die Liste nebenbei frisch. */
async function tipperKennungen(env) {
  const index = await indexLesen(env);
  const jetzt = Date.now();
  // stand 0 heisst: die Liste ist erst beim Tippen entstanden und wurde nie
  // gegen den Speicher abgeglichen. Sie enthaelt dann nur, wer seitdem
  // getippt hat - als vollstaendige Tabelle waere das eine Falschaussage.
  if (index && index.stand > 0 && jetzt - index.stand < INDEX_FRISCH_MS) {
    return { ids: index.ids, vollstaendig: true };
  }
  // Ist das Tageskontingent gerade erschoepft, rennt nicht jeder Abruf
  // erneut dagegen - eine Stunde Ruhe, dann der naechste Versuch.
  if (index && jetzt < index.gesperrtBis) {
    return { ids: index.ids, vollstaendig: index.stand > 0 };
  }
  try {
    const liste = await env.ZAEHLER.list({ prefix: "tipper:" });
    const ids = liste.keys.map(k => k.name.slice("tipper:".length));
    // Wer inzwischen ueber /tipp dazugekommen ist, aber noch nicht im
    // Speicher gelistet war, geht dabei nicht verloren.
    for (const id of (index ? index.ids : [])) {
      if (!ids.includes(id)) ids.push(id);
    }
    await indexSchreiben(env, { stand: jetzt, gesperrtBis: 0, ids });
    return { ids, vollstaendig: true };
  } catch (e) {
    if (index) {
      try { await indexSchreiben(env, { ...index, gesperrtBis: jetzt + INDEX_SPERRE_MS }); }
      catch { /* dann eben beim naechsten Mal */ }
      return { ids: index.ids, vollstaendig: index.stand > 0 };
    }
    throw e;
  }
}

/**
 * Nimmt eine Kennung in die Liste auf. Legt sie noetigenfalls an - mit
 * stand 0, damit sie beim naechsten moeglichen Zugriff aus dem Speicher
 * vervollstaendigt wird. So waechst die Tabelle auch dann weiter, wenn
 * gerade kein list() moeglich ist.
 */
async function indexErgaenzen(env, id) {
  try {
    const index = (await indexLesen(env)) || { stand: 0, gesperrtBis: 0, ids: [] };
    if (index.ids.includes(id)) return;
    index.ids.push(id);
    await indexSchreiben(env, index);
  } catch { /* die Liste wird ohnehin regelmaessig neu aufgebaut */ }
}

async function tipperLesen(env, id) {
  const wert = JSON.parse((await env.ZAEHLER.get(`tipper:${id}`)) || "null");
  if (wert && typeof wert === "object" && !Array.isArray(wert)) {
    // Die Felder werden erzwungen, nicht nur vorbelegt: ein gespeichertes
    // name:null oder tipps:null hat den Vorgabewert sonst ueberschrieben.
    return {
      ...wert,
      name: typeof wert.name === "string" ? wert.name
            : typeof wert.name === "number" ? String(wert.name) : "",
      tipps: wert.tipps && typeof wert.tipps === "object" && !Array.isArray(wert.tipps)
        ? wert.tipps : {},
    };
  }
  return { name: "", tipps: {} };
}

/** Wie tipperLesen, aber ein unlesbarer Eintrag wirft nicht. */
async function tipperLesenWeich(env, id) {
  try {
    return await tipperLesen(env, id);
  } catch {
    return { name: "", tipps: {}, unlesbar: true };
  }
}

/** Datum in Deutschland, damit "heute" nicht um 1 Uhr nachts umspringt. */
function heute() {
  return new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Berlin" });
}

function leererStand() {
  return { ereignis: {}, mannschaft: {}, bereich: {} };
}

function addiere(ziel, quelle) {
  for (const gruppe of ["ereignis", "mannschaft", "bereich"]) {
    for (const [name, zahl] of Object.entries(quelle[gruppe] || {})) {
      ziel[gruppe][name] = (ziel[gruppe][name] || 0) + zahl;
    }
  }
  return ziel;
}

/** Nur bekannte Namen und ganze Zahlen uebernehmen. */
function saeubere(roh) {
  const rein = leererStand();
  const uebernimm = (gruppe, passt, hoechstens = Infinity) => {
    let genommen = 0;
    for (const [name, wert] of Object.entries(roh[gruppe] || {})) {
      if (genommen >= hoechstens) break;
      if (!passt(name)) continue;
      const n = parseInt(wert, 10);
      if (Number.isFinite(n) && n > 0) {
        rein[gruppe][name] = Math.min(n, 500);
        genommen += 1;
      }
    }
  };
  uebernimm("ereignis", (n) => STAT_EREIGNISSE.includes(n));
  uebernimm("mannschaft", (n) => MANNSCHAFT_FORM.test(n), MANNSCHAFTEN_JE_ANFRAGE);
  uebernimm("bereich", (n) => STAT_BEREICHE.includes(n));
  return rein;
}

async function tagLesen(env, datum) {
  // Nebenlaeufig: nacheinander waeren es bei 30 Tagen 300 Abrufe hintereinander
  // und die Auswertung braeuchte spuerbar lange.
  const teile = await Promise.all(
    Array.from({ length: STAT_TEILE }, (_, i) =>
      env.ZAEHLER.get(`stat:${datum}:${i}`).catch(() => null)));
  const gesamt = leererStand();
  for (const roh of teile) {
    if (!roh) continue;
    try { addiere(gesamt, JSON.parse(roh)); } catch { /* unbrauchbar */ }
  }
  return gesamt;
}

function angemeldet(env, benutzer, passwort) {
  const sollBenutzer = env.ADMIN_BENUTZER || "";
  const sollPasswort = env.ADMIN_PASSWORT || "";
  if (!sollPasswort) return false;
  // Vergleich in gleichbleibender Zeit, damit sich das Passwort nicht
  // zeichenweise erraten laesst.
  const gleich = (a, b) => {
    if (a.length !== b.length) return false;
    let abweichung = 0;
    for (let i = 0; i < a.length; i++) abweichung |= a.charCodeAt(i) ^ b.charCodeAt(i);
    return abweichung === 0;
  };
  return gleich(String(benutzer || ""), sollBenutzer)
      && gleich(String(passwort || ""), sollPasswort);
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

      // ---- Nutzung zaehlen ----
      if (pfad === "/zaehl" && request.method === "POST") {
        const rein = saeubere(await request.json());
        const datum = heute();
        // Zufaelliger Teil: verteilt gleichzeitige Zugriffe, sonst geht bei
        // mehr als einem Schreibvorgang je Sekunde eine Zaehlung verloren.
        const teil = Math.floor(Math.random() * STAT_TEILE);
        const schluessel = `stat:${datum}:${teil}`;
        let stand = leererStand();
        try {
          const roh = await env.ZAEHLER.get(schluessel);
          if (roh) stand = addiere(leererStand(), JSON.parse(roh));
        } catch { /* neu anfangen */ }
        await env.ZAEHLER.put(schluessel, JSON.stringify(addiere(stand, rein)));
        return antwort({ gezaehlt: true }, request);
      }

      if (pfad === "/auswertung" && request.method === "POST") {
        const { benutzer, passwort, tage } = await request.json();
        if (!angemeldet(env, benutzer, passwort)) {
          return antwort({ fehler: "Anmeldung fehlgeschlagen" }, request, 401);
        }
        const anzahl = Math.min(Math.max(parseInt(tage, 10) || 30, 1), 90);
        const jetzt = new Date();
        const tage_liste = Array.from({ length: anzahl }, (_, i) =>
          new Date(jetzt.getTime() - (anzahl - 1 - i) * 86400000)
            .toLocaleDateString("sv-SE", { timeZone: "Europe/Berlin" }));
        const staende = await Promise.all(tage_liste.map(t => tagLesen(env, t)));

        const verlauf = [];
        const gesamt = leererStand();
        tage_liste.forEach((tag, i) => {
          verlauf.push({ tag, aufrufe: staende[i].ereignis.aufruf || 0 });
          addiere(gesamt, staende[i]);
        });
        // Zaehler aus Hype, Zusagen und Tipps zum Vergleich danebenstellen
        const kennungen = await tipperKennungen(env);
        return antwort({ verlauf, gesamt, tipper: kennungen.ids.length }, request);
      }

      // Wer in der Tipprunde steht, mit Kennung - Grundlage fuers Aufraeumen.
      if (pfad === "/tipper-liste" && request.method === "POST") {
        const { benutzer, passwort } = await request.json();
        if (!angemeldet(env, benutzer, passwort)) {
          return antwort({ fehler: "Anmeldung fehlgeschlagen" }, request, 401);
        }
        const kennungen = await tipperKennungen(env);
        const liste = [];
        for (const id of kennungen.ids.slice(0, 200)) {
          const tipper = await tipperLesenWeich(env, id);
          if (tipper.unlesbar) {
            liste.push({ id, name: "", tipps: 0, unlesbar: true });
            continue;
          }
          liste.push({
            id,
            name: tipper.name,
            tipps: Object.keys(tipper.tipps || {}).length,
            // Was der Filter beanstandet, steht oben - auch wenn es vor
            // seiner Einfuehrung gespeichert wurde.
            beanstandet: tipper.name ? !!anstoessig(tipper.name) : false,
          });
        }
        liste.sort((a, b) => (b.beanstandet ? 1 : 0) - (a.beanstandet ? 1 : 0)
                          || String(a.name).localeCompare(String(b.name)));
        return antwort({ tipper: liste, vollstaendig: !!kennungen.vollstaendig },
                       request);
      }

      // Aufraeumen. Zwei Stufen, weil sie sich deutlich unterscheiden:
      // "name" nimmt nur den Namen (der Tipp bleibt gewertet, der Eintrag
      // verschwindet aus der Tabelle, die Person kann sich neu benennen),
      // "ganz" loescht den Eintrag mitsamt Tipps.
      if (pfad === "/tipper-entfernen" && request.method === "POST") {
        const { benutzer, passwort, geraet, art } = await request.json();
        if (!angemeldet(env, benutzer, passwort)) {
          return antwort({ fehler: "Anmeldung fehlgeschlagen" }, request, 401);
        }
        if (!gueltig(geraet)) {
          return antwort({ fehler: "geraet fehlt" }, request, 400);
        }
        if (art !== "name" && art !== "ganz") {
          return antwort({ fehler: "art muss 'name' oder 'ganz' sein" },
                         request, 400);
        }
        const vorher = await tipperLesenWeich(env, geraet);
        // Erst merken, dann aendern: das Objekt unten ist dasselbe, sonst
        // meldet die Antwort den leeren Namen statt des entfernten.
        const alterName = vorher.name || "";
        if (art === "name") {
          const tipper = vorher.unlesbar ? { name: "", tipps: {} } : vorher;
          delete tipper.unlesbar;
          tipper.name = "";
          await env.ZAEHLER.put(`tipper:${geraet}`, JSON.stringify(tipper));
          return antwort({ erledigt: "name", geraet, war: alterName }, request);
        }
        await env.ZAEHLER.delete(`tipper:${geraet}`);
        // Auch aus der Liste nehmen, sonst wird der Eintrag bei jedem Abruf
        // vergeblich gesucht, bis sie das naechste Mal neu aufgebaut wird.
        try {
          const index = await indexLesen(env);
          if (index) {
            index.ids = index.ids.filter((x) => x !== geraet);
            await indexSchreiben(env, index);
          }
        } catch { /* die Liste wird ohnehin regelmaessig erneuert */ }
        return antwort({ erledigt: "ganz", geraet, war: alterName }, request);
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
          return antwort({ fehler: "Zu spät, das Spiel läuft schon." },
                         request, 409);
        }

        const tipper = await tipperLesen(env, geraet);
        if (typeof name === "string" && name.trim()) {
          const gewaehlt = name.trim().slice(0, 24);
          if (anstoessig(gewaehlt)) {
            return antwort({ fehler: "Bitte einen anderen Namen wählen." },
                           request, 400);
          }
          tipper.name = gewaehlt;
        }
        tipper.tipps[spiel] = [th, tg];
        await env.ZAEHLER.put(`tipper:${geraet}`, JSON.stringify(tipper));
        await indexErgaenzen(env, geraet);
        return antwort({ spiel, tipp: [th, tg], name: tipper.name }, request);
      }

      if (pfad === "/tipper" && request.method === "GET") {
        const geraet = url.searchParams.get("geraet");
        if (!gueltig(geraet)) return antwort({ fehler: "geraet fehlt" }, request, 400);
        const tipper = await tipperLesen(env, geraet);
        // Vereinheitlicht ausliefern: die Seite liest tipps[spiel][0] und
        // [1] und stuende sonst vor einem abweichend gespeicherten Eintrag.
        // Geschrieben wird dabei nichts.
        const tipps = {};
        for (const [code, wert] of Object.entries(tipper.tipps)) {
          const t = alsTipp(wert);
          if (t) tipps[code] = t;
        }
        return antwort({ name: tipper.name, tipps }, request);
      }

      if (pfad === "/tipptabelle" && request.method === "GET") {
        const spiele = await spieldaten();
        // Jede Mannschaft hat ihre eigene Wertung. Ohne Angabe waeren es
        // alle Spiele des Vereins - wer viele Mannschaften tippt, haette
        // dann automatisch mehr Punkte.
        const nurMannschaft = url.searchParams.get("mannschaft") || "";
        const kennungen = await tipperKennungen(env);

        // Jeder Speicherzugriff zaehlt gegen das Subrequest-Limit der Anfrage
        // (50 im kostenlosen Tarif), und list() sowie das Laden der Spieldaten
        // sind schon zwei davon. Frueher lief die Schleife blind darueber
        // hinaus: die Lesefehler wurden verschluckt und die Betroffenen
        // fielen still aus der Tabelle. Jetzt wird die Grenze eingehalten und
        // eine unvollstaendige Tabelle als solche gemeldet.
        const LESE_HOECHSTENS = 45;
        const zuLesen = kennungen.ids.slice(0, LESE_HOECHSTENS);
        const ausgelassen = kennungen.ids.length - zuLesen.length;
        let unlesbar = 0;

        const eintraege = [];
        for (const id of zuLesen) {
          const tipper = await tipperLesenWeich(env, id);
          if (tipper.unlesbar) { unlesbar += 1; continue; }
          if (!tipper.name) continue;          // ohne Namen nicht in der Tabelle
          // Der Filter kam erst nach dem ersten Spieltag dazu. Was vorher
          // durchgerutscht ist, verschwindet damit ebenfalls aus der Wertung -
          // der Tipp bleibt gespeichert, nur der Name wird nicht gezeigt.
          if (anstoessig(tipper.name)) continue;

          try {
            let summe = 0, gewertet = 0, exakt = 0;
            for (const [code, tipp] of Object.entries(tipper.tipps)) {
              const partie = spiele[code];
              if (!partie || !partie.ergebnis) continue;
              if (nurMannschaft && partie.schluessel !== nurMannschaft) continue;
              const p = punkte(tipp, partie.ergebnis);
              summe += p; gewertet += 1;
              if (p === PUNKTE_EXAKT) exakt += 1;
            }
            const eigeneTipps = Object.keys(tipper.tipps).filter(
              (c) => !nurMannschaft
                  || (spiele[c] && spiele[c].schluessel === nurMannschaft));
            if (nurMannschaft && !eigeneTipps.length) continue;

            eintraege.push({ id, name: tipper.name, punkte: summe,
                             spiele: gewertet, exakt,
                             tipps: eigeneTipps.length });
          } catch {
            // Ein einzelner unbrauchbarer Eintrag darf nicht die Tabelle
            // aller anderen mitnehmen. Der Eintrag bleibt im Speicher stehen.
            unlesbar += 1;
          }
        }

        eintraege.sort((a, b) => b.punkte - a.punkte || b.exakt - a.exakt
                                 || String(a.name).localeCompare(String(b.name)));
        return antwort({
          tabelle: eintraege.map((e, i) => ({ platz: i + 1, ...e })),
          ...(ausgelassen || unlesbar || !kennungen.vollstaendig
              ? { unvollstaendig: { ausgelassen, unlesbar,
                                    ...(kennungen.vollstaendig ? {} : { imAufbau: true }) } }
              : {}),
        }, request);
      }

      return antwort({ fehler: "unbekannter Pfad" }, request, 404);
    } catch (e) {
      // Frueher stand hier nur "Anfrage fehlerhaft". Ein defekter Eintrag
      // legte damit die Tipptabelle lahm, ohne dass irgendwo stand, warum.
      console.error("Fehler bei", pfad, e && e.stack ? e.stack : e);
      return antwort({ fehler: "Anfrage fehlerhaft",
                       grund: String((e && e.message) || e) }, request, 400);
    }
  },

  /**
   * Sicherheitsnetz fuer den Spielplan-Workflow.
   *
   * GitHub verschiebt geplante Laeufe bei Last, manchmal um Stunden, und
   * laesst sie auch ganz ausfallen: am 29.08.2026 fielen die Laeufe um
   * 14:05 und 15:05 aus, der letzte war von 12:01. Ergebnisse standen
   * dadurch stundenlang nicht auf der Seite.
   *
   * Cloudflare haelt seine Cron-Zeiten dagegen ein. Dieser Aufruf schaut
   * nach, wie alt die veroeffentlichten Daten sind, und stoesst den
   * Workflow nur an, wenn GitHub selbst nicht geliefert hat. Laeuft dort
   * alles normal, passiert hier nichts.
   */
  async scheduled(event, env, ctx) {
    ctx.waitUntil(nachschauen(env));
  },
};

// Wie alt die veroeffentlichten Daten sein duerfen, bevor nachgelegt wird.
// Der Wert begrenzt zugleich, wie oft der Workflow hoechstens laeuft: bei 25
// Minuten also hoechstens gut zweimal die Stunde, egal wie eng der Cron
// getaktet ist. Das schont handball.net, das bei jedem Lauf 23 Mannschaften
// beantworten muss.
const HOECHSTALTER_MIN = 25;
const TAGESFRIST_MIN = 25 * 60;        // der naechtliche Lauf darf nicht ausfallen
const NACHSPIELZEIT_MS = 6 * 60 * 60 * 1000;

/**
 * Ist gerade ein Spiel gelaufen, dessen Ergebnis eingetragen werden koennte?
 *
 * Ohne diese Frage wuerde der Worker unter der Woche stundenlang Laeufe
 * anstossen, in denen es nichts zu holen gibt - und er haenge davon ab, dass
 * die Wochentage im Cron-Ausdruck stimmen. Cloudflare hat "6,0" fuer
 * Samstag und Sonntag abgewiesen; solche Stolperstellen sollen nicht
 * daruber entscheiden, wie oft der Workflow laeuft.
 */
function spielKuerzlich(roh) {
  const jetzt = Date.now();
  for (const mannschaft of Object.values(roh.teams || {})) {
    for (const spiel of Object.values(mannschaft.spiele || {})) {
      const anwurf = alsOrtszeit(spiel.datum);
      if (anwurf <= jetzt && jetzt - anwurf < NACHSPIELZEIT_MS) return true;
    }
  }
  return false;
}

async function nachschauen(env) {
  if (!env.GITHUB_TOKEN) {
    console.log("kein GITHUB_TOKEN gesetzt - nichts angestossen");
    return;
  }
  let alter = Infinity;
  let gespielt = true;      // ohne Daten im Zweifel nachlegen
  try {
    const antwort = await fetch(DATEN_URL, { cf: { cacheTtl: 0 } });
    if (antwort.ok) {
      const roh = await antwort.json();
      const stand = Date.parse(roh.aktualisiert);
      if (Number.isFinite(stand)) alter = (Date.now() - stand) / 60000;
      gespielt = spielKuerzlich(roh);
    }
  } catch (e) {
    // Sind die Daten nicht erreichbar, ist das erst recht ein Grund
    // nachzulegen - alter bleibt auf Infinity.
    console.error("Daten nicht erreichbar:", String(e));
  }

  if (alter < HOECHSTALTER_MIN) {
    console.log(`Daten sind ${Math.round(alter)} Minuten alt - GitHub war puenktlich`);
    return;
  }
  if (!gespielt && alter < TAGESFRIST_MIN) {
    console.log(`Daten sind ${Math.round(alter)} Minuten alt, aber es lief kein `
                + `Spiel - kein Grund nachzulegen`);
    return;
  }

  const r = await fetch(
    "https://api.github.com/repos/beatzep/handball-kalender/dispatches",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
        // Ohne User-Agent antwortet die GitHub-API mit 403.
        "User-Agent": "muru-zaehler",
      },
      body: JSON.stringify({ event_type: "spielplan-nachziehen" }),
    });
  const text = r.status === 204 ? "" : await r.text();
  console.log(`Daten waren ${Math.round(alter)} Minuten alt, Workflow angestossen:`,
              r.status, text);
  if (r.status === 403) {
    // Haeufigste Ursache: der Token hat "Actions" statt "Contents".
    // repository_dispatch haengt bei GitHub an den Repository-Inhalten.
    console.error("403 - der Token braucht die Berechtigung "
                  + "'Contents: Read and write' auf dieses Repository");
  }
}
