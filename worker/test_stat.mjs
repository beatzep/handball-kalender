import worker from "./index.js";

const speicher = new Map();
const env = {
  ADMIN_BENUTZER: "stammspieler@muru.hsg",
  ADMIN_PASSWORT: "geheim-fuer-den-test",
  ZAEHLER: {
    get: async (k) => (speicher.has(k) ? speicher.get(k) : null),
    put: async (k, v) => void speicher.set(k, v),
    list: async ({ prefix }) => ({
      keys: [...speicher.keys()].filter(k => k.startsWith(prefix)).map(name => ({ name })),
    }),
  },
};
globalThis.fetch = async () => ({ ok: true, json: async () => ({ teams: {} }) });

const H = { Origin: "https://beatzep.github.io", "Content-Type": "application/json" };
const ruf = async (pfad, methode = "GET", koerper) => {
  const r = await worker.fetch(new Request("https://x.dev" + pfad, {
    method: methode, headers: H, body: koerper ? JSON.stringify(koerper) : undefined,
  }), env);
  return { status: r.status, daten: await r.json() };
};

const pruefungen = [];
const pruefe = (n, ok, i = "") => pruefungen.push({ n, ok, i });
const ANMELDUNG = { benutzer: "stammspieler@muru.hsg", passwort: "geheim-fuer-den-test" };
let r;

// Zaehlen
await ruf("/zaehl", "POST", { ereignis: { aufruf: 1 }, mannschaft: { herren1: 1 },
                              bereich: { kalender: 1 } });
await ruf("/zaehl", "POST", { ereignis: { aufruf: 1, abo: 1 }, mannschaft: { damen: 1 },
                              bereich: { tabelle: 1, statistik: 1 } });
r = await ruf("/auswertung", "POST", ANMELDUNG);
pruefe("Aufrufe summiert", r.daten.gesamt.ereignis.aufruf === 2, JSON.stringify(r.daten.gesamt));
pruefe("Abo-Klick gezählt", r.daten.gesamt.ereignis.abo === 1);
pruefe("Nach Mannschaft getrennt",
       r.daten.gesamt.mannschaft.herren1 === 1 && r.daten.gesamt.mannschaft.damen === 1,
       JSON.stringify(r.daten.gesamt.mannschaft));
pruefe("Nach Bereich getrennt", r.daten.gesamt.bereich.statistik === 1);
pruefe("Verlauf hat 30 Tage", r.daten.verlauf.length === 30, String(r.daten.verlauf.length));
pruefe("Heutiger Tag im Verlauf",
       r.daten.verlauf[r.daten.verlauf.length - 1].aufrufe === 2,
       JSON.stringify(r.daten.verlauf.slice(-1)));

// Verteilung auf mehrere Schluessel
for (let i = 0; i < 40; i++) await ruf("/zaehl", "POST", { ereignis: { aufruf: 1 } });
const teile = [...speicher.keys()].filter(k => k.startsWith("stat:"));
pruefe("Zählung auf mehrere Schlüssel verteilt", teile.length > 1, JSON.stringify(teile));
r = await ruf("/auswertung", "POST", ANMELDUNG);
pruefe("Verteilte Zählung wieder zusammengeführt",
       r.daten.gesamt.ereignis.aufruf === 42, String(r.daten.gesamt.ereignis.aufruf));

// Anmeldung
r = await ruf("/auswertung", "POST", { benutzer: "stammspieler@muru.hsg", passwort: "falsch" });
pruefe("Falsches Passwort abgewiesen", r.status === 401);
r = await ruf("/auswertung", "POST", { benutzer: "wer-anders", passwort: "geheim-fuer-den-test" });
pruefe("Falscher Benutzer abgewiesen", r.status === 401);
r = await ruf("/auswertung", "POST", {});
pruefe("Ohne Anmeldung abgewiesen", r.status === 401);

const ohnePasswort = { ...env, ADMIN_PASSWORT: "" };
const rr = await worker.fetch(new Request("https://x.dev/auswertung", {
  method: "POST", headers: H, body: JSON.stringify(ANMELDUNG) }), ohnePasswort);
pruefe("Ohne hinterlegtes Passwort kein Zugang", rr.status === 401);

// Unbekannte Felder werden verworfen
await ruf("/zaehl", "POST", { ereignis: { unbekannt: 5, aufruf: "viele" },
                              mannschaft: { "Fremd Verein!": 3, "gf-2": 2 } });
r = await ruf("/auswertung", "POST", ANMELDUNG);
pruefe("Unbekanntes Ereignis verworfen", !("unbekannt" in r.daten.gesamt.ereignis));
// Mannschaften werden nicht mehr gegen eine feste Liste geprueft, sondern
// gegen ihre Form: die Liste kannte nur herren1, herren2 und damen, seit der
// Erweiterung fiel damit jeder Jugend-Aufruf still aus der Zaehlung.
pruefe("Jugendmannschaft wird gezaehlt", r.daten.gesamt.mannschaft["gf-2"] === 2,
       JSON.stringify(r.daten.gesamt.mannschaft));
pruefe("Kein Mannschaftsschluessel mit Sonderzeichen",
       !("Fremd Verein!" in r.daten.gesamt.mannschaft));

// Die Deckelung haelt den Speicher sauber, wenn jemand den Endpunkt findet
const viele = {};
for (let i = 0; i < 40; i++) viele["erfunden-" + i] = 1;
await ruf("/zaehl", "POST", { ereignis: {}, mannschaft: viele });
r = await ruf("/auswertung", "POST", ANMELDUNG);
const erfunden = Object.keys(r.daten.gesamt.mannschaft)
  .filter((k) => k.startsWith("erfunden-")).length;
pruefe("Hoechstens acht Mannschaften je Anfrage", erfunden <= 8, String(erfunden));
pruefe("Nichtzahl verworfen", r.daten.gesamt.ereignis.aufruf === 42,
       String(r.daten.gesamt.ereignis.aufruf));

await ruf("/zaehl", "POST", { ereignis: { aufruf: 99999 } });
r = await ruf("/auswertung", "POST", ANMELDUNG);
pruefe("Absurd hohe Zahl gedeckelt", r.daten.gesamt.ereignis.aufruf === 542,
       String(r.daten.gesamt.ereignis.aufruf));

let fehler = 0;
for (const p of pruefungen) {
  if (!p.ok) fehler++;
  console.log(`${p.ok ? "  ok  " : "FEHLER"}  ${p.n}${p.ok ? "" : "   " + p.i}`);
}
console.log(fehler ? `\n${fehler} Prüfung(en) fehlgeschlagen`
                   : `\nAlle ${pruefungen.length} Prüfungen bestanden`);
process.exit(fehler ? 1 : 0);
