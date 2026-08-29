// Prueft das Sicherheitsnetz: stoesst der Worker den Workflow genau dann an,
// wenn GitHub seinen Zeitplan nicht eingehalten hat?
import worker from "./index.js";

const pruefungen = [];
const pruefe = (name, ok, info = "") => pruefungen.push({ name, ok, info });

async function lauf({ alterMinuten, token = "geheim", datenErreichbar = true,
                      dispatchStatus = 204 }) {
  const gerufen = [];
  const echtesFetch = globalThis.fetch;
  globalThis.fetch = async (url, optionen) => {
    const adresse = String(url);
    if (adresse.includes("daten.json")) {
      if (!datenErreichbar) throw new Error("nicht erreichbar");
      const stand = new Date(Date.now() - alterMinuten * 60000).toISOString();
      return { ok: true, json: async () => ({ aktualisiert: stand }) };
    }
    if (adresse.includes("/dispatches")) {
      gerufen.push({ adresse, optionen });
      return { status: dispatchStatus, text: async () => "" };
    }
    throw new Error("unerwartete Adresse: " + adresse);
  };
  const wartend = [];
  await worker.scheduled({}, { GITHUB_TOKEN: token },
                         { waitUntil: (p) => wartend.push(p) });
  await Promise.all(wartend);
  globalThis.fetch = echtesFetch;
  return gerufen;
}

let g = await lauf({ alterMinuten: 5 });
pruefe("Frische Daten: kein Anstoss", g.length === 0, `${g.length} Aufrufe`);

g = await lauf({ alterMinuten: 45 });
pruefe("45 Minuten alt: noch kein Anstoss", g.length === 0, `${g.length} Aufrufe`);

g = await lauf({ alterMinuten: 200 });
pruefe("Daten drei Stunden alt: Workflow wird angestossen", g.length === 1,
       `${g.length} Aufrufe`);
if (g.length === 1) {
  const k = JSON.parse(g[0].optionen.body);
  pruefe("Richtiger Anlass gemeldet", k.event_type === "spielplan-nachziehen",
         JSON.stringify(k));
  pruefe("Token wird mitgeschickt",
         g[0].optionen.headers.Authorization === "Bearer geheim");
  pruefe("User-Agent gesetzt (sonst antwortet GitHub mit 403)",
         !!g[0].optionen.headers["User-Agent"]);
  pruefe("Richtiges Repository", g[0].adresse.includes("beatzep/handball-kalender"));
}

g = await lauf({ alterMinuten: 200, datenErreichbar: false });
pruefe("Daten nicht erreichbar: erst recht anstossen", g.length === 1,
       `${g.length} Aufrufe`);

g = await lauf({ alterMinuten: 200, token: "" });   // "" statt undefined: sonst greift der Vorgabewert
pruefe("Ohne Token passiert nichts (kein Absturz)", g.length === 0);

// Ein abgelehnter Anstoss darf den Worker nicht umbringen
let geworfen = false;
try {
  g = await lauf({ alterMinuten: 200, dispatchStatus: 401 });
} catch (e) { geworfen = true; }
pruefe("Abgelehnter Anstoss wirft nicht", !geworfen);

let fehler = 0;
for (const p of pruefungen) {
  if (!p.ok) fehler++;
  console.log(`${p.ok ? "  ok  " : "FEHLER"}  ${p.name}${p.ok ? "" : "   " + p.info}`);
}
console.log(fehler ? `\n${fehler} Prüfung(en) fehlgeschlagen`
                   : `\nAlle ${pruefungen.length} Prüfungen bestanden`);
process.exit(fehler ? 1 : 0);
