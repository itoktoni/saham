// Pakai: node tests/test-labarugi-display.js
"use strict";
const fs = require("fs");
const path = require("path");
let gagal = 0;
function cek(nama, kondisi, info) {
  if (kondisi) { console.log("  OK   " + nama); }
  else { gagal++; console.log("  GAGAL " + nama + (info ? "  -> " + info : "")); }
}
const html = fs.readFileSync(path.join(__dirname, "..", "web", "screener-praktis.html"), "utf-8");
const blocks = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const script = blocks.reduce((a, b) => (a.length > b.length ? a : b), "");
const m = script.match(/var SP = \(function \(\) \{[\s\S]*?\n\}\)\(\);/);
cek("modul SP ditemukan", !!m);
if (!m) process.exit(1);
const SP = new Function(m[0] + "; return SP;")();
cek("SP.labarugiSVG ada", typeof SP.labarugiSVG === "function");
if (typeof SP.labarugiSVG === "function") {
  const seri = { q: [{ t: "2026-03-31", rev: 9e12, ni: -0.5e12 }, { t: "2026-06-30", rev: 10e12, ni: 1e12 }], y: [] };
  const s = SP.labarugiSVG(seri, "q");
  cek("keluaran <svg", s.indexOf("<svg") === 0, s.slice(0, 60));
  cek("tooltip <title> ada", s.indexOf("<title>") > 0);
  cek("seri kosong -> __KOSONG__", SP.labarugiSVG({ q: [], y: [] }, "q") === "__KOSONG__");
}
cek("S.labarugi dimuat dari API", html.indexOf("S.labarugi") >= 0 && html.indexOf("j.labarugi") >= 0);
cek("drawer panggil labarugiSVG", html.indexOf("labarugiSVG") >= 0 && html.indexOf("Revenue & Net Income") >= 0);
cek("ada toggle Kuartal/Tahunan", html.indexOf("Kuartal") >= 0 && html.indexOf("Tahunan") >= 0);
cek("scan gabung labarugi tanpa hapus", /for\s*\(\s*var k in j\.labarugi\s*\)/.test(html) || html.indexOf("Object.assign({}, S.labarugi, j.labarugi)") >= 0);
cek("SP.lrMiniSVG ada", typeof SP.lrMiniSVG === "function");
if (typeof SP.lrMiniSVG === "function") {
  const seri = { q: [{ t: "2025-09-30", rev: 7e12, ni: 0.7e12 }, { t: "2025-12-31", rev: 8e12, ni: 0.8e12 },
    { t: "2026-03-31", rev: 9e12, ni: -0.5e12 }, { t: "2026-06-30", rev: 10e12, ni: 1e12 }], y: [] };
  const s = SP.lrMiniSVG(seri, "q", "BBCA");
  cek("mini mulai <svg", s.indexOf("<svg") === 0, s.slice(0, 60));
  cek("mini ringkas (<3000 char)", s.length > 100 && s.length < 3000, String(s.length));
  cek("mini ada <title> tooltip", s.indexOf("<title>") > 0);
  cek("mini kosong -> __KOSONG__", SP.lrMiniSVG({ q: [], y: [] }, "q", "XX") === "__KOSONG__");
  cek("memo: seri sama -> string identik", SP.lrMiniSVG(seri, "q", "BBCA") === s);
  cek("memo: mode beda -> hasil beda", SP.lrMiniSVG(seri, "y", "BBCA") === "__KOSONG__");
  cek("memo: seri baru -> hitung ulang", SP.lrMiniSVG({ q: seri.q.slice(0, 2), y: [] }, "q", "BBCA") !== s);
}
cek("tabel punya kolom lr", html.indexOf('{ k: "lr"') >= 0);
cek("baris tabel panggil lrMiniSVG", html.indexOf("SP.lrMiniSVG") >= 0);
cek("toggle drawer ikut render tabel", /_lrMode = "q"; isiDrawer\([^)]*\); render\(\)/.test(html));
if (gagal) { console.log("HASIL: " + gagal + " GAGAL"); process.exit(1); }
else { console.log("HASIL: semua lolos"); }
