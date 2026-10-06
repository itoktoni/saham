// Pilih universe diagnostik: top-N kandidat menurut modul SP yang asli.
// Pakai: node tests/_score-top.js [top=80]
// Input : data/diag-snapshot.csv (scan pasar) + data/data-idx.csv (watchlist)
//         + data/ksei.json
// Output: data/diag-universe.txt (satu kode per baris, urut skor desc)
"use strict";
const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..");
const html = fs.readFileSync(path.join(ROOT, "web", "screener-praktis.html"), "utf-8");
const blocks = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const script = blocks.reduce((a, b) => (a.length > b.length ? a : b), "");
const m = script.match(/var SP = \(function \(\) \{[\s\S]*?\n\}\)\(\);/);
if (!m) { console.error("modul SP tidak ditemukan"); process.exit(1); }
const SP = new Function(m[0] + "; return SP;")();

const top = parseInt(process.argv[2] || "80", 10);

const ksei = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "ksei.json"), "utf-8"));
const kmap = SP.ingestKsei(ksei, {});

// Watchlist lebih kaya (ekuitas/saham/laba) — menang saat kode sama dengan TV.
const byKode = {};
for (const f of ["data/data-idx.csv", "data/diag-snapshot.csv"]) {
  const p = path.join(ROOT, f);
  if (!fs.existsSync(p)) continue;
  for (const r of SP.parseCSV(fs.readFileSync(p, "utf-8"))) {
    const k = String(r.kode || "").trim().toUpperCase();
    if (k) byKode[k] = r;
  }
}
const rows = Object.values(byKode);
const data = SP.build(rows, kmap);
data.sort((a, b) => b.skor - a.skor);

const pilih = data.slice(0, top);
fs.writeFileSync(path.join(ROOT, "data", "diag-universe.txt"),
  pilih.map(x => x.kode).join("\n") + "\n", "utf-8");

console.log("top " + pilih.length + " kandidat (dari " + data.length + " saham):");
for (const x of pilih.slice(0, 10)) {
  console.log("  " + x.kode.padEnd(6) + " skor " + String(x.skor).padStart(3) +
    "  " + x.fase.padEnd(10) + " MOS " + x.val.mos.toFixed(0) + "%  " + x.aksi);
}
