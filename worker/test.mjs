import worker from "./index.js";

// KV nachbilden
const speicher = new Map();
const env = { ZAEHLER: {
  get: async (k) => (speicher.has(k) ? speicher.get(k) : null),
  put: async (k, v) => void speicher.set(k, v),
}};

const H = { Origin: "https://beatzep.github.io", "Content-Type": "application/json" };
const ruf = async (pfad, methode = "GET", koerper) => {
  const r = await worker.fetch(new Request("https://x.dev" + pfad, {
    method: methode, headers: H,
    body: koerper ? JSON.stringify(koerper) : undefined,
  }), env);
  return { status: r.status, cors: r.headers.get("Access-Control-Allow-Origin"), daten: await r.json() };
};

const SPIEL = "2627RPBKROERMA0101";
const pruefungen = [];
const pruefe = (name, ok, info = "") => pruefungen.push({ name, ok, info });

let r = await ruf(`/stand?spiel=${SPIEL}`);
pruefe("Leerer Stand ist 0", r.daten.hype === 0 && r.daten.dabei === 0, JSON.stringify(r.daten));

r = await ruf("/hype", "POST", { spiel: SPIEL, anzahl: 7 });
pruefe("Hype +7", r.daten.hype === 7, JSON.stringify(r.daten));
r = await ruf("/hype", "POST", { spiel: SPIEL, anzahl: 3 });
pruefe("Hype summiert auf 10", r.daten.hype === 10, JSON.stringify(r.daten));

r = await ruf("/hype", "POST", { spiel: SPIEL, anzahl: 9999 });
pruefe("Obergrenze greift (max 25)", r.daten.hype === 35, JSON.stringify(r.daten));

r = await ruf("/hype", "POST", { spiel: SPIEL, anzahl: -5 });
pruefe("Negative Werte ignoriert", r.daten.hype === 35, JSON.stringify(r.daten));

r = await ruf("/dabei", "POST", { spiel: SPIEL, geraet: "geraetA", an: true });
pruefe("Erste Zusage", r.daten.dabei === 1);
r = await ruf("/dabei", "POST", { spiel: SPIEL, geraet: "geraetA", an: true });
pruefe("Doppelte Zusage zaehlt einmal", r.daten.dabei === 1, JSON.stringify(r.daten));
r = await ruf("/dabei", "POST", { spiel: SPIEL, geraet: "geraetB", an: true });
pruefe("Zweites Geraet", r.daten.dabei === 2);
r = await ruf("/dabei", "POST", { spiel: SPIEL, geraet: "geraetA", an: false });
pruefe("Abmelden moeglich", r.daten.dabei === 1, JSON.stringify(r.daten));

r = await ruf(`/stand?spiel=${SPIEL}&vergleich=2627RPBKROERMA9999`);
pruefe("Vergleichswert wird geliefert", r.daten.vorher?.hype === 0, JSON.stringify(r.daten));

r = await ruf("/stand?spiel=../../etc/passwd");
pruefe("Ungueltige Spielnummer abgewiesen", r.status === 400, JSON.stringify(r));
r = await ruf("/hype", "POST", { spiel: "a b c", anzahl: 1 });
pruefe("Ungueltige Kennung abgewiesen", r.status === 400);
r = await ruf("/unbekannt");
pruefe("Unbekannter Pfad 404", r.status === 404);

// Fremde Herkunft darf keine CORS-Freigabe bekommen
const fremd = await worker.fetch(new Request("https://x.dev/stand?spiel=" + SPIEL,
  { headers: { Origin: "https://boese.example" } }), env);
pruefe("Fremde Herkunft ohne CORS-Freigabe",
  fremd.headers.get("Access-Control-Allow-Origin") === "null");

// Zaehler sind pro Spiel getrennt
r = await ruf("/hype", "POST", { spiel: "2627RPBKROERMA0206", anzahl: 4 });
pruefe("Anderes Spiel eigener Zaehler", r.daten.hype === 4, JSON.stringify(r.daten));
r = await ruf(`/stand?spiel=${SPIEL}`);
pruefe("Erstes Spiel unveraendert", r.daten.hype === 35, JSON.stringify(r.daten));

let fehler = 0;
for (const p of pruefungen) {
  if (!p.ok) fehler++;
  console.log(`${p.ok ? "  ok  " : "FEHLER"}  ${p.name}${p.ok ? "" : "   " + p.info}`);
}
console.log(fehler ? `\n${fehler} Prüfung(en) fehlgeschlagen` : `\nAlle ${pruefungen.length} Prüfungen bestanden`);
process.exit(fehler ? 1 : 0);
