// RED: display FS dual-skala 1-10 + label + verdict (tanpa ubah fundSkor).
// Pakai: node tests/test-fs-display.js
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
if (!m) { process.exit(1); }
const SP = new Function(m[0] + "; return SP;")();

// 1) helper normalisasi harus ada (display-only, rumus fundSkor tak tersentuh)
cek("SP.fsSkala10 ada", typeof SP.fsSkala10 === "function");
cek("SP.fsLabel ada", typeof SP.fsLabel === "function");
cek("SP.fsPilar ada", typeof SP.fsPilar === "function");

if (typeof SP.fsSkala10 === "function") {
  const eq = (a, b) => Math.abs(a - b) < 0.06;
  // Kasus user: Valuasi 1,0/30 -> 0,3/10 ; Kualitas 4,3/30 -> 1,4/10
  cek("Valuasi 1,0/30 -> 0,3/10", eq(SP.fsSkala10(1.0, 30), 0.3), SP.fsSkala10(1.0, 30));
  cek("Kualitas 4,3/30 -> 1,4/10", eq(SP.fsSkala10(4.3, 30), 1.4), SP.fsSkala10(4.3, 30));
  cek("Momentum 1,0/10 -> 1,0/10", eq(SP.fsSkala10(1.0, 10), 1.0), SP.fsSkala10(1.0, 10));
  cek("Makro 5,0/10 -> 5,0/10", eq(SP.fsSkala10(5.0, 10), 5.0), SP.fsSkala10(5.0, 10));
  cek("AntiTrap 8,0/20 -> 4,0/10", eq(SP.fsSkala10(8.0, 20), 4.0), SP.fsSkala10(8.0, 20));
  cek("maks selalu 10: 30/30->10", eq(SP.fsSkala10(30, 30), 10));
  cek("maks selalu 10: 20/20->10", eq(SP.fsSkala10(20, 20), 10));
}

if (typeof SP.fsLabel === "function") {
  cek("0,3 -> Bahaya", SP.fsLabel(0.3) === "Bahaya", SP.fsLabel(0.3));
  cek("1,4 -> Bahaya", SP.fsLabel(1.4) === "Bahaya", SP.fsLabel(1.4));
  cek("4,0 -> Kurang", SP.fsLabel(4.0) === "Kurang", SP.fsLabel(4.0));
  cek("5,0 -> Cukup", SP.fsLabel(5.0) === "Cukup", SP.fsLabel(5.0));
  cek("7,5 -> Bagus", SP.fsLabel(7.5) === "Bagus", SP.fsLabel(7.5));
  cek("9,5 -> Sangat Bagus", SP.fsLabel(9.5) === "Sangat Bagus", SP.fsLabel(9.5));
}

if (typeof SP.fsPilar === "function") {
  const p = SP.fsPilar(1.0, 30);
  cek("fsPilar kembalikan mentah+skala+label", p && p.mentah === 1.0 && typeof p.skala10 === "number" && typeof p.label === "string", JSON.stringify(p));
}

// 2) fundSkor tak berubah nilainya (rumusba display-only)
{
  const r = { der: "0.4", eps_trend: "down", dividen: "0", ev_cfo: "20", cagr: "2" };
  const fund = { nilai: { der: 0.4 }, tren: { eps: "turun", roe: "turun" }, kas: { dividen: [] } };
  const fs = SP.fundSkor(r, fund, { unggulan: [] });
  cek("fundSkor tetap hitung total mentah", typeof fs.total === "number" && typeof fs.p.valuasi === "number", JSON.stringify(fs && fs.p));
}

// 3) drawer tampilkan dual angka + label (cek string HTML sumber)
cek("drawer pakai fsSkala10/fsPilar", html.indexOf("fsSkala10") >= 0 || html.indexOf("fsPilar") >= 0);
cek("drawer tampilkan /10", html.indexOf("/10") >= 0);
cek("drawer ada kata Bahaya/Kurang/Cukup/Bagus", /Bahaya|Kurang|Cukup|Bagus/.test(html));

if (gagal) { console.log("HASIL: " + gagal + " GAGAL"); process.exit(1); }
else { console.log("HASIL: semua lolos"); }
