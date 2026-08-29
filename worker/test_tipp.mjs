import worker from "./index.js";

// KV und Spieldaten nachbilden
const speicher = new Map();
const env = { ZAEHLER: {
  get: async (k) => (speicher.has(k) ? speicher.get(k) : null),
  put: async (k, v) => void speicher.set(k, v),
  list: async ({ prefix }) => ({
    keys: [...speicher.keys()].filter(k => k.startsWith(prefix)).map(name => ({ name })),
  }),
}};

const VERGANGEN = "2020-01-01T20:00:00";
const ZUKUNFT = "2099-01-01T20:00:00";
globalThis.fetch = async () => ({
  ok: true,
  json: async () => ({ teams: { herren1: { name: "Herren I", spiele: {
    KOMMEND:  { datum: ZUKUNFT,  gegner: "A", heim: true,  ergebnis: null },
    GELAUFEN: { datum: VERGANGEN, gegner: "B", heim: true,
                ergebnis: { heim: 30, gast: 25 } },
    LAEUFT:   { datum: VERGANGEN, gegner: "C", heim: false, ergebnis: null },
  }}}}),
});

const H = { Origin: "https://beatzep.github.io", "Content-Type": "application/json" };
const ruf = async (pfad, methode = "GET", koerper) => {
  const r = await worker.fetch(new Request("https://x.dev" + pfad, {
    method: methode, headers: H, body: koerper ? JSON.stringify(koerper) : undefined,
  }), env);
  return { status: r.status, daten: await r.json() };
};

const pruefungen = [];
const pruefe = (name, ok, info = "") => pruefungen.push({ name, ok, info });
let r;

r = await ruf("/tipp", "POST", { geraet: "edis", spiel: "KOMMEND", heim: 30, gast: 25, name: "Edis" });
pruefe("Tipp wird angenommen", r.status === 200 && r.daten.name === "Edis", JSON.stringify(r));

r = await ruf("/tipp", "POST", { geraet: "edis", spiel: "KOMMEND", heim: 28, gast: 26 });
pruefe("Tipp überschreibbar bis Anwurf", r.daten.tipp?.[0] === 28, JSON.stringify(r.daten));

r = await ruf("/tipper?geraet=edis");
pruefe("Name bleibt beim Überschreiben erhalten", r.daten.name === "Edis", JSON.stringify(r.daten));

r = await ruf("/tipp", "POST", { geraet: "edis", spiel: "LAEUFT", heim: 20, gast: 20 });
pruefe("Nach Anwurf gesperrt", r.status === 409, JSON.stringify(r));

r = await ruf("/tipp", "POST", { geraet: "edis", spiel: "GIBTESNICHT", heim: 1, gast: 1 });
pruefe("Unbekanntes Spiel abgewiesen", r.status === 404);

r = await ruf("/tipp", "POST", { geraet: "edis", spiel: "KOMMEND", heim: -3, gast: 1 });
pruefe("Negatives Ergebnis abgewiesen", r.status === 400);
r = await ruf("/tipp", "POST", { geraet: "edis", spiel: "KOMMEND", heim: 500, gast: 1 });
pruefe("Unmögliches Ergebnis abgewiesen", r.status === 400);

// Punktevergabe bei Ergebnis 30:25. Ueber /tipp ginge das nicht mehr - das
// Spiel ist gelaufen und der Worker sperrt zu Recht. Im echten Ablauf wurde
// vor dem Anwurf getippt, darum hier direkt abgelegt.
const ablegen = (id, name, heim, gast) => speicher.set(
  `tipper:${id}`, JSON.stringify({ name, tipps: { GELAUFEN: [heim, gast] } }));
ablegen("exakt", "Exakt", 30, 25);
ablegen("diff", "Differenz", 28, 23);
ablegen("tend", "Tendenz", 40, 20);
ablegen("falsch", "Daneben", 20, 30);
ablegen("ohne", "", 30, 25);            // ohne Namen

r = await ruf("/tipptabelle");
const t = Object.fromEntries((r.daten.tabelle || []).map(e => [e.name, e.punkte]));
pruefe("Exakter Tipp: 10 Punkte", t["Exakt"] === 10, JSON.stringify(t));
pruefe("Richtige Differenz: 5 Punkte", t["Differenz"] === 5, JSON.stringify(t));
pruefe("Richtige Tendenz: 3 Punkte", t["Tendenz"] === 3, JSON.stringify(t));
pruefe("Falsche Tendenz: 0 Punkte", t["Daneben"] === 0, JSON.stringify(t));
pruefe("Ohne Namen nicht in der Tabelle", r.daten.tabelle.every(e => e.name),
       JSON.stringify(r.daten.tabelle.map(e => e.name)));
pruefe("Tabelle absteigend sortiert",
       r.daten.tabelle[0].name === "Exakt" && r.daten.tabelle[0].platz === 1,
       JSON.stringify(r.daten.tabelle.map(e => e.name + ":" + e.punkte)));

// Punkte stapeln sich ueber Spiele hinweg: ein zusaetzlicher Tipp auf ein
// noch nicht gespieltes Spiel darf den Punktestand nicht veraendern.
await ruf("/tipp", "POST", { geraet: "exakt", spiel: "KOMMEND", heim: 1, gast: 1 });
r = await ruf("/tipptabelle");
const exakt = r.daten.tabelle.find(e => e.name === "Exakt");
pruefe("Ungewertetes Spiel ändert die Punkte nicht",
       exakt.punkte === 10 && exakt.spiele === 1 && exakt.tipps === 2, JSON.stringify(exakt));

// Wiedererkennung: dieselbe Kennung findet ihre Tipps wieder
r = await ruf("/tipper?geraet=exakt");
pruefe("Kennung findet ihre Tipps wieder",
       Object.keys(r.daten.tipps).length === 2 && r.daten.name === "Exakt",
       JSON.stringify(r.daten));

// Jede Mannschaft hat ihre eigene Wertung
speicher.clear();
globalThis.fetch = async () => ({ ok: true, json: async () => ({ teams: {
  herren1: { name: "Herren I", spiele: {
    H1SPIEL: { datum: VERGANGEN, gegner: "A", heim: true,
               ergebnis: { heim: 30, gast: 25 } } } },
  ma: { name: "mA-Jugend", spiele: {
    MASPIEL: { datum: VERGANGEN, gegner: "B", heim: true,
               ergebnis: { heim: 20, gast: 22 } } } },
}})});
speicher.set("tipper:nur-h1", JSON.stringify({ name: "Nur H1", tipps: { H1SPIEL: [30, 25] } }));
speicher.set("tipper:nur-ma", JSON.stringify({ name: "Nur mA", tipps: { MASPIEL: [20, 22] } }));
speicher.set("tipper:beide", JSON.stringify({ name: "Beide",
  tipps: { H1SPIEL: [30, 25], MASPIEL: [40, 1] } }));

speicher.delete("tipper-index");     // wie ein Neuaufbau nach direktem Schreiben
r = await ruf("/tipptabelle?mannschaft=herren1");
let namen = r.daten.tabelle.map(e => e.name).sort();
pruefe("Herren-I-Tabelle zeigt nur deren Tipper",
       JSON.stringify(namen) === JSON.stringify(["Beide", "Nur H1"]), JSON.stringify(namen));

r = await ruf("/tipptabelle?mannschaft=ma");
namen = r.daten.tabelle.map(e => e.name).sort();
pruefe("mA-Tabelle zeigt nur deren Tipper",
       JSON.stringify(namen) === JSON.stringify(["Beide", "Nur mA"]), JSON.stringify(namen));

const beideInMa = r.daten.tabelle.find(e => e.name === "Beide");
pruefe("Punkte der anderen Mannschaft zaehlen hier nicht",
       beideInMa.punkte === 0 && beideInMa.tipps === 1, JSON.stringify(beideInMa));

r = await ruf("/tipptabelle");
pruefe("Ohne Angabe alle Mannschaften", r.daten.tabelle.length === 3,
       String(r.daten.tabelle.length));

// Eintraege, die nicht so aussehen wie erwartet.
// Live legte ein solcher Eintrag die komplette Tipptabelle mit HTTP 400
// lahm - fuer alle Mannschaften, bei jedem Seitenaufruf. Die Wertung laeuft
// jetzt je Tipper gekapselt, und was sich deuten laesst, wird gedeutet.
speicher.set("tipper:objekt", JSON.stringify({ name: "Objektform",
  tipps: { H1SPIEL: { heim: 30, gast: 25 } } }));
speicher.delete("tipper-index");
r = await ruf("/tipptabelle?mannschaft=herren1");
pruefe("Ein abweichend gespeicherter Tipp kippt die Tabelle nicht",
       r.status === 200, JSON.stringify(r).slice(0, 160));
let objekt = (r.daten.tabelle || []).find(e => e.name === "Objektform");
pruefe("Tipp in Objektform wird gewertet statt verworfen",
       objekt && objekt.punkte === 10, JSON.stringify(objekt));

speicher.set("tipper:zahl", JSON.stringify({ name: "Zahlform", tipps: { H1SPIEL: 30 } }));
speicher.set("tipper:leer", JSON.stringify({ name: "Ohne Tipps", tipps: null }));
speicher.set("tipper:namelos", JSON.stringify({ name: null, tipps: { H1SPIEL: [30, 25] } }));
speicher.set("tipper:kaputt", "{kein json");
speicher.set("tipper:string", JSON.stringify("nur ein String"));
speicher.set("tipper:liste", JSON.stringify([1, 2, 3]));
speicher.delete("tipper-index");
r = await ruf("/tipptabelle?mannschaft=herren1");
pruefe("Sechs unbrauchbare Eintraege gleichzeitig: Tabelle steht",
       r.status === 200, JSON.stringify(r).slice(0, 160));
pruefe("Die brauchbaren Eintraege sind weiterhin da",
       (r.daten.tabelle || []).some(e => e.name === "Nur H1")
       && (r.daten.tabelle || []).some(e => e.name === "Objektform"),
       JSON.stringify(r.daten));

// Kein Eintrag darf beim Lesen veraendert oder geloescht werden
const vorher = new Map(speicher);
await ruf("/tipptabelle?mannschaft=herren1");
await ruf("/tipptabelle");
let veraendert = [...vorher.keys()].filter(k => speicher.get(k) !== vorher.get(k));
pruefe("Die Tabelle veraendert keinen gespeicherten Tipp",
       veraendert.length === 0 && speicher.size === vorher.size,
       JSON.stringify(veraendert));

// Mehr Tipper als das Subrequest-Limit der Anfrage zulaesst
for (let i = 0; i < 60; i++) {
  speicher.set(`tipper:m${i}`, JSON.stringify({ name: `M${i}`, tipps: { H1SPIEL: [30, 25] } }));
}
speicher.delete("tipper-index");
r = await ruf("/tipptabelle?mannschaft=herren1");
pruefe("Sehr viele Tipper: Tabelle bleibt erreichbar", r.status === 200,
       JSON.stringify(r.daten).slice(0, 120));
pruefe("Unvollstaendige Tabelle wird als solche gemeldet",
       !!r.daten.unvollstaendig && r.daten.unvollstaendig.ausgelassen > 0,
       JSON.stringify(r.daten.unvollstaendig));

// Das Tageskontingent fuer list() (1.000 im kostenlosen Tarif) war live
// erschoepft, weil die Seite pro Aufruf 24 Tabellen lud. Der Lesepfad darf
// deshalb gar kein list() mehr brauchen.
let listAufrufe = 0;
const zaehlendesEnv = { ZAEHLER: {
  get: env.ZAEHLER.get, put: env.ZAEHLER.put,
  list: async (o) => { listAufrufe += 1; return env.ZAEHLER.list(o); },
}};
const rufZ = async (pfad) => {
  const r = await worker.fetch(new Request("https://x.dev" + pfad, { headers: H }),
                               zaehlendesEnv);
  return { status: r.status, daten: await r.json() };
};

speicher.delete("tipper-index");
await rufZ("/tipptabelle?mannschaft=herren1");     // baut die Liste auf
const nachErstem = listAufrufe;
for (let i = 0; i < 30; i++) await rufZ("/tipptabelle?mannschaft=herren1");
pruefe("Weitere Abrufe brauchen kein list() mehr",
       nachErstem === 1 && listAufrufe === 1, `erst ${nachErstem}, dann ${listAufrufe}`);

// Und wenn das Kontingent doch erschoepft ist: lieber eine etwas aeltere
// Liste als die leere Flaeche, die monatelang zu sehen war.
const sperrendesEnv = { ZAEHLER: {
  get: env.ZAEHLER.get, put: env.ZAEHLER.put,
  list: async () => { throw new Error("KV list() limit exceeded for the day."); },
}};
const rufS = async (pfad) => {
  const r = await worker.fetch(new Request("https://x.dev" + pfad, { headers: H }),
                               sperrendesEnv);
  return { status: r.status, daten: await r.json() };
};
r = await rufS("/tipptabelle?mannschaft=herren1");
pruefe("Bei erschoepftem list()-Kontingent steht die Tabelle trotzdem",
       r.status === 200 && r.daten.tabelle.length > 0,
       JSON.stringify(r.daten).slice(0, 120));

// Ein neuer Tipper muss sofort auftauchen, nicht erst beim Neuaufbau.
// Die Spieldaten oben kennen nur gelaufene Partien - hier eine kommende.
const vorherigeSpiele = globalThis.fetch;
globalThis.fetch = async () => ({ ok: true, json: async () => ({ teams: {
  herren1: { name: "Herren I", spiele: {
    H1SPIEL: { datum: VERGANGEN, gegner: "A", heim: true,
               ergebnis: { heim: 30, gast: 25 } },
    NAECHSTES: { datum: ZUKUNFT, gegner: "D", heim: true, ergebnis: null } } },
  ma: { name: "mA-Jugend", spiele: {
    MASPIEL: { datum: VERGANGEN, gegner: "B", heim: true,
               ergebnis: { heim: 20, gast: 22 } } } },
}})});
// Die 60 Eintraege aus der Mengenprobe raeumen, sonst faellt der neue
// hinter die Lesegrenze. Die gemerkte Liste wird mitgezogen statt neu
// aufgebaut - sonst wuerde der Test nicht zeigen, dass /tipp sie pflegt.
for (let i = 0; i < 60; i++) speicher.delete(`tipper:m${i}`);
{
  const idx = JSON.parse(speicher.get("tipper-index"));
  idx.ids = idx.ids.filter(id => !/^m\d+$/.test(id));
  speicher.set("tipper-index", JSON.stringify(idx));
}
r = await ruf("/tipp", "POST",
  { geraet: "frisch", spiel: "NAECHSTES", heim: 1, gast: 2, name: "Frisch Getippt" });
pruefe("Neuer Tipp wird angenommen", r.status === 200, JSON.stringify(r.daten));
r = await ruf("/tipptabelle");
pruefe("Neuer Tipper steht sofort in der Tabelle",
       r.daten.tabelle.some(e => e.name === "Frisch Getippt"),
       JSON.stringify(r.daten.tabelle.map(e => e.name)));
globalThis.fetch = vorherigeSpiele;

// Genau die Lage vom 29.08.2026: kein Index, und list() geht nicht mehr.
// Wer jetzt tippt, muss trotzdem in der Tabelle erscheinen, und sobald das
// Kontingent wieder da ist, muessen die Aelteren dazukommen.
{
  const vorher2 = globalThis.fetch;
  globalThis.fetch = async () => ({ ok: true, json: async () => ({ teams: {
    herren1: { name: "Herren I", spiele: {
      H1SPIEL: { datum: VERGANGEN, gegner: "A", heim: true,
                 ergebnis: { heim: 30, gast: 25 } },
      NAECHSTES: { datum: ZUKUNFT, gegner: "D", heim: true, ergebnis: null } } },
  }})});
  const s2 = new Map();
  let listErlaubt = false;
  const env2 = { ZAEHLER: {
    get: async (k) => (s2.has(k) ? s2.get(k) : null),
    put: async (k, v) => void s2.set(k, v),
    list: async ({ prefix }) => {
      if (!listErlaubt) throw new Error("KV list() limit exceeded for the day.");
      return { keys: [...s2.keys()].filter(k => k.startsWith(prefix)).map(name => ({ name })) };
    },
  }};
  const ruf2 = async (pfad, methode = "GET", koerper) => {
    const r = await worker.fetch(new Request("https://x.dev" + pfad, {
      method: methode, headers: H, body: koerper ? JSON.stringify(koerper) : undefined,
    }), env2);
    return { status: r.status, daten: await r.json() };
  };

  // Ein Alteingesessener liegt im Speicher, aber in keiner Liste
  s2.set("tipper:alt", JSON.stringify({ name: "Schon dabei", tipps: { H1SPIEL: [30, 25] } }));

  let x = await ruf2("/tipptabelle?mannschaft=herren1");
  pruefe("Ohne Liste und ohne list() sagt die Tabelle es ehrlich", x.status === 400,
         JSON.stringify(x.daten));

  x = await ruf2("/tipp", "POST",
    { geraet: "neuling", spiel: "NAECHSTES", heim: 3, gast: 2, name: "Neu Getippt" });
  pruefe("Tippen geht auch ohne Liste", x.status === 200, JSON.stringify(x.daten));

  x = await ruf2("/tipptabelle?mannschaft=herren1");
  pruefe("Wer jetzt tippt, steht sofort in der Tabelle",
         x.status === 200 && x.daten.tabelle.some(e => e.name === "Neu Getippt"),
         JSON.stringify(x.daten).slice(0, 140));
  pruefe("Eine erst im Aufbau befindliche Wertung gibt sich als solche zu erkennen",
         !!(x.daten.unvollstaendig && x.daten.unvollstaendig.imAufbau),
         JSON.stringify(x.daten.unvollstaendig));

  listErlaubt = true;                      // am naechsten Tag
  {                                        // und die Stundensperre ist abgelaufen
    const idx = JSON.parse(s2.get("tipper-index"));
    idx.gesperrtBis = 0;
    s2.set("tipper-index", JSON.stringify(idx));
  }
  x = await ruf2("/tipptabelle?mannschaft=herren1");
  const drin = (x.daten.tabelle || []).map(e => e.name).sort();
  pruefe("Sobald list() wieder geht, sind die Aelteren dabei",
         drin.includes("Schon dabei") && drin.includes("Neu Getippt"),
         JSON.stringify(drin));
  pruefe("Danach gilt die Wertung wieder als vollstaendig",
         !x.daten.unvollstaendig, JSON.stringify(x.daten.unvollstaendig));
  globalThis.fetch = vorher2;
}

let fehler = 0;
for (const p of pruefungen) {
  if (!p.ok) fehler++;
  console.log(`${p.ok ? "  ok  " : "FEHLER"}  ${p.name}${p.ok ? "" : "   " + p.info}`);
}
console.log(fehler ? `\n${fehler} Prüfung(en) fehlgeschlagen`
                   : `\nAlle ${pruefungen.length} Prüfungen bestanden`);
process.exit(fehler ? 1 : 0);
