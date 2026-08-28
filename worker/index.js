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

      return antwort({ fehler: "unbekannter Pfad" }, request, 404);
    } catch (e) {
      return antwort({ fehler: "Anfrage fehlerhaft" }, request, 400);
    }
  },
};
