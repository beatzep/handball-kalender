// Prueft den Namensfilter der Tipprunde.
//
// Er ist bewusst grob: lieber einmal zu viel abgelehnt als ein Schimpfwort
// auf der Vereinsseite. Wo diese Abwaegung jemanden trifft, der wirklich so
// heisst, steht das hier ausdruecklich - damit es eine Entscheidung bleibt
// und kein Versehen.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const hier = dirname(fileURLToPath(import.meta.url));
const quelle = readFileSync(join(hier, "index.js"), "utf8");
const teil = quelle.slice(quelle.indexOf("const SCHIMPFWOERTER"),
                          quelle.indexOf("function gueltig(spiel)"));
const { anstoessig, vergleichsform } = await import(
  "data:text/javascript," + encodeURIComponent(teil
    + "\nexport { anstoessig, vergleichsform };"));

const pruefungen = [];
const pruefe = (name, ok, info = "") => pruefungen.push({ name, ok, info });

// 1. Was abgelehnt gehoert
for (const n of ["Sexseven", "Arschloch", "hurensohn99", "Der Wichser",
                 "fickt euch", "Schwuchtel", "Hitler", "bitch42"]) {
  pruefe(`abgelehnt: ${n}`, !!anstoessig(n));
}

// 2. Verschleierung hilft nicht
for (const n of ["W1chs3r", "F.U.C.K", "N3g3r", "@rsch", "f_i_c_k",
                 "Wichßer", "SCHEISSE", "sch3iss3", "fuuuck", "Wichsser"]) {
  pruefe(`Verschleierung erkannt: ${n}`, !!anstoessig(n));
}

// 3. Die Namen, die heute in der Wertung stehen, muessen durchgehen
for (const n of ["Edis", "Sammy", "Jan Bußer", "Hoffe", "Konsti", "Schunki",
                 "Holzi", "Dominik Doell", "Saskia", "Vojin", "Elisa", "Nico",
                 "Pascal", "Hermy", "Buschi"]) {
  pruefe(`echter Tipper geht durch: ${n}`, !anstoessig(n),
         String(anstoessig(n)));
}

// 4. Haeufige deutsche Namen duerfen nicht haengen bleiben
for (const n of ["Dick", "Dickmann", "Dickel", "Wichmann", "Assmann",
                 "Tittel", "Hurler", "Massage", "Klassen", "Nigge"]) {
  pruefe(`deutscher Name geht durch: ${n}`, !anstoessig(n),
         String(anstoessig(n)));
}

// 5. Bewusst in Kauf genommen: seltene Namen, die der Filter mitnimmt.
// Aendert sich hier etwas, soll es auffallen - nicht stillschweigend.
for (const [n, wort] of [["Sexauer", "sex"], ["Fickert", "fick"],
                         ["Analyse", "anal"], ["Kackert", "kacke"]]) {
  pruefe(`bewusst streng: ${n} wird abgelehnt`, anstoessig(n) === wort,
         String(anstoessig(n)));
}

// 6. Harmloses bleibt harmlos
pruefe("leerer Name ist nicht anstoessig", anstoessig("") === null);
pruefe("nur Ziffern sind nicht anstoessig", anstoessig("12345") === null);
pruefe("Vergleichsform loest Umlaute auf", vergleichsform("Müßig") === "muesig");

let fehler = 0;
for (const p of pruefungen) {
  if (!p.ok) fehler++;
  console.log(`${p.ok ? "  ok  " : "FEHLER"}  ${p.name}${p.ok ? "" : "   " + p.info}`);
}
console.log(fehler ? `\n${fehler} Prüfung(en) fehlgeschlagen`
                   : `\nAlle ${pruefungen.length} Prüfungen bestanden`);
process.exit(fehler ? 1 : 0);
