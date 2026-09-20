// Prueft das Aufraeumen der Tipprunde: auflisten, Namen entfernen, loeschen.
import worker from "./index.js";

const speicher = new Map();
const env = { ADMIN_BENUTZER: "chef@muru.hsg", ADMIN_PASSWORT: "geheim",
  ZAEHLER: {
    get: async (k) => (speicher.has(k) ? speicher.get(k) : null),
    put: async (k, v) => void speicher.set(k, v),
    delete: async (k) => void speicher.delete(k),
    list: async ({ prefix }) => ({
      keys: [...speicher.keys()].filter(k => k.startsWith(prefix)).map(name => ({ name })),
    }),
  }};
globalThis.fetch = async () => ({ ok: true, json: async () => ({ teams: {} }) });

const H = { Origin: "https://beatzep.github.io", "Content-Type": "application/json" };
const ruf = async (pfad, koerper) => {
  const r = await worker.fetch(new Request("https://x.dev" + pfad, {
    method: "POST", headers: H, body: JSON.stringify(koerper) }), env);
  return { status: r.status, daten: await r.json() };
};
const anmeldung = { benutzer: "chef@muru.hsg", passwort: "geheim" };

const pruefungen = [];
const pruefe = (name, ok, info = "") => pruefungen.push({ name, ok, info });

speicher.set("tipper:aaaa", JSON.stringify({ name: "Edis", tipps: { S1: [30, 25] } }));
speicher.set("tipper:bbbb", JSON.stringify({ name: "Sexseven", tipps: { S1: [20, 30] } }));
speicher.set("tipper:cccc", JSON.stringify({ name: "Sammy", tipps: { S1: [1, 2] } }));

let r = await ruf("/tipper-liste", {});
pruefe("Ohne Anmeldung keine Liste", r.status === 401, JSON.stringify(r.daten));

r = await ruf("/tipper-entfernen", { geraet: "aaaa", art: "ganz" });
pruefe("Ohne Anmeldung kein Loeschen", r.status === 401);
pruefe("und der Eintrag steht noch", speicher.has("tipper:aaaa"));

r = await ruf("/tipper-liste", anmeldung);
pruefe("Angemeldet kommt die Liste", r.status === 200 && r.daten.tipper.length === 3,
       JSON.stringify(r.daten).slice(0, 120));
const beanstandet = r.daten.tipper.filter(t => t.beanstandet).map(t => t.name);
pruefe("Der anstoessige Name ist markiert",
       JSON.stringify(beanstandet) === JSON.stringify(["Sexseven"]),
       JSON.stringify(beanstandet));
pruefe("und steht oben", r.daten.tipper[0].name === "Sexseven",
       r.daten.tipper[0].name);

// Name entfernen: Tipp bleibt, Eintrag bleibt
r = await ruf("/tipper-entfernen", { ...anmeldung, geraet: "bbbb", art: "name" });
pruefe("Name entfernen meldet den bisherigen Namen",
       r.status === 200 && r.daten.war === "Sexseven", JSON.stringify(r.daten));
const nachher = JSON.parse(speicher.get("tipper:bbbb"));
pruefe("Der Eintrag existiert weiter", !!speicher.get("tipper:bbbb"));
pruefe("Der Name ist leer", nachher.name === "");
pruefe("Der Tipp ist unveraendert",
       JSON.stringify(nachher.tipps) === JSON.stringify({ S1: [20, 30] }),
       JSON.stringify(nachher.tipps));

// Ganz loeschen
r = await ruf("/tipper-entfernen", { ...anmeldung, geraet: "cccc", art: "ganz" });
pruefe("Loeschen meldet den bisherigen Namen",
       r.status === 200 && r.daten.war === "Sammy", JSON.stringify(r.daten));
pruefe("Der Eintrag ist weg", !speicher.has("tipper:cccc"));
const index = JSON.parse(speicher.get("tipper-index") || '{"ids":[]}');
pruefe("und auch aus der Liste raus", !index.ids.includes("cccc"),
       JSON.stringify(index.ids));

// Unfug abweisen
r = await ruf("/tipper-entfernen", { ...anmeldung, geraet: "aaaa", art: "alles" });
pruefe("Unbekannte Art wird abgewiesen", r.status === 400, JSON.stringify(r.daten));
pruefe("und der Eintrag steht noch", speicher.has("tipper:aaaa"));
r = await ruf("/tipper-entfernen", { ...anmeldung, art: "ganz" });
pruefe("Ohne Kennung wird abgewiesen", r.status === 400);

// Ein entfernter Name darf nicht mehr in der Wertung stehen
r = await ruf("/tipper-liste", anmeldung);
pruefe("Nach dem Aufraeumen bleiben zwei Eintraege",
       r.daten.tipper.length === 2, String(r.daten.tipper.length));
pruefe("und keiner davon ist beanstandet",
       !r.daten.tipper.some(t => t.beanstandet));

// Zusammenfuehren: dieselbe Person mit zwei Geraeten
speicher.set("tipper:dddd", JSON.stringify({ name: "", tipps: { S2: [10, 12] } }));

r = await ruf("/tipper-zusammenfuehren", { ziel: "aaaa", quelle: "dddd" });
pruefe("Ohne Anmeldung kein Zusammenfuehren", r.status === 401);

r = await ruf("/tipper-zusammenfuehren", { ...anmeldung, ziel: "aaaa", quelle: "aaaa" });
pruefe("Ziel gleich Quelle wird abgewiesen", r.status === 400, JSON.stringify(r.daten));

r = await ruf("/tipper-zusammenfuehren", { ...anmeldung, ziel: "aaaa" });
pruefe("Ohne Quelle wird abgewiesen", r.status === 400);

r = await ruf("/tipper-zusammenfuehren", { ...anmeldung, ziel: "aaaa", quelle: "dddd" });
pruefe("Zusammenfuehren meldet den neuen Stand",
       r.status === 200 && r.daten.name === "Edis" && r.daten.tipps === 2,
       JSON.stringify(r.daten));
pruefe("Die Quelle ist weg", !speicher.has("tipper:dddd"));
const zusammen = JSON.parse(speicher.get("tipper:aaaa"));
pruefe("Beide Tipps stehen jetzt beim Ziel",
       zusammen.tipps.S1 && zusammen.tipps.S1.join(":") === "30:25"
       && zusammen.tipps.S2 && zusammen.tipps.S2.join(":") === "10:12",
       JSON.stringify(zusammen.tipps));
const indexNachMerge = JSON.parse(speicher.get("tipper-index") || '{"ids":[]}');
pruefe("Quelle raus aus der Liste, Ziel drin",
       !indexNachMerge.ids.includes("dddd") && indexNachMerge.ids.includes("aaaa"),
       JSON.stringify(indexNachMerge.ids));

// Tippen beide dasselbe Spiel unterschiedlich, gilt der Tipp des Ziels
speicher.set("tipper:eeee", JSON.stringify({ name: "Edis Zweitgeraet", tipps: { S1: [1, 1] } }));
r = await ruf("/tipper-zusammenfuehren", { ...anmeldung, ziel: "aaaa", quelle: "eeee" });
pruefe("Ueberschneidung: der Tipp des Ziels bleibt bestehen",
       JSON.parse(speicher.get("tipper:aaaa")).tipps.S1[0] === 30,
       JSON.stringify(JSON.parse(speicher.get("tipper:aaaa")).tipps));

let fehler = 0;
for (const p of pruefungen) {
  if (!p.ok) fehler++;
  console.log(`${p.ok ? "  ok  " : "FEHLER"}  ${p.name}${p.ok ? "" : "   " + p.info}`);
}
console.log(fehler ? `\n${fehler} Prüfung(en) fehlgeschlagen`
                   : `\nAlle ${pruefungen.length} Prüfungen bestanden`);
process.exit(fehler ? 1 : 0);
