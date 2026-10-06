// Laporan diagnostik skor (Fase 0): komponen skor vs return maju 20 hari,
// plus hit-rate "Beli" untuk baseline dan calon fix (counterfactual).
// Pakai: node tests/_diag-skor.js
// Input : data/diag-fitur.csv  (dihasilkan scripts/diag-skor.py)
//
// Catatan: mirror komponen skor ada di file ini. Assert total == SP.skor
// dijalankan tiap baris supaya mirror tidak pernah melenceng dari halaman.
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

const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const toNum = SP.toNum;
const orNull = v => (v == null || v === "" ? null : toNum(v));

// ---------------------------------------------------------------- komponen
// Mirror resmi rumus skor HALAMAN (post-kalibrasi Fase 0). Assert totalOf()
// di bawah dibandingkan ke SP.skor tiap baris — kalau beda, file ini yang
// salah, bukan halamannya.
function komponen(r, k, fase, val) {
  k = k || {};
  const sNilai = clamp((val.mos + 20) / 70 * 100, 0, 100);   // raw (skor lama)
  // versi halaman: cap di MOS 50%, decay drawdown, blend bandar 60/40
  let sN = clamp((val.mos + 20) / 70 * 100, 0, val.mos > CFG.capMOS ? CFG.capNilai : 100);
  const h52 = toNum(r.high_52), harga = toNum(r.harga);
  const draw = (h52 > 0 && harga > 0) ? Math.max(0, (h52 - harga) / h52) : 0;
  sN = sN * clamp(1 - draw / CFG.drawDiv, 0.35, 1);
  if (k.asing_avg_price && harga > 0) {
    const mosBandar = (k.asing_avg_price - harga) / k.asing_avg_price * 100;
    sN = (1 - CFG.bandarBlend) * sN
       + CFG.bandarBlend * clamp((mosBandar + 20) / 70 * 100, 0, 100);
  }

  let sKualitas = 50;
  if (val.roe >= 15) sKualitas += 20; else if (val.roe >= 8) sKualitas += 10;
  if (toNum(r.der) > 1.5) sKualitas -= 20;
  if (r.eps_trend === "up") sKualitas += 10; else if (r.eps_trend === "down") sKualitas -= 15;
  if (toNum(r.laba) > 0 || val.roe > 0) sKualitas += 10; else sKualitas -= 20;
  sKualitas = clamp(sKualitas, 0, 100);

  let sTiming = { "Spring": 90, "Akumulasi": 78, "Markup": 68, "Netral": 50, "Distribusi": 15 }[fase];
  if (toNum(r.s_freqspike) === 1) sTiming += 5;
  if (toNum(r.s_vol_ratio) >= 1.3) sTiming += 5;
  if (fase === "Netral" && toNum(r.s_sideways) === 1) sTiming += 8;
  sTiming = clamp(sTiming, 0, 100);

  const dA = k.dksei_asing_1m == null ? 0 : k.dksei_asing_1m;
  const dI = k.dksei_institusi_1m == null ? 0 : k.dksei_institusi_1m;
  const sAliran = clamp(50 + Math.max(dA, dI) * 8, 0, 100);

  const sMom = (r.ret20 == null || r.ret20 === "") ? 50
             : clamp(50 - toNum(r.ret20) * 4, 0, 100);
  return { sNilai, sNfix: sN, sKualitas, sTiming, sAliran, sMom };
}
const W_BARU = { n: 0.15, k: 0.30, t: 0.15, a: 0.10, m: 0.30 };
const W_LAMA = { n: 0.40, k: 0.25, t: 0.20, a: 0.15, m: 0 };
const totalOf = c => clamp(Math.round(
  W_BARU.n * c.sNfix + W_BARU.k * c.sKualitas + W_BARU.t * c.sTiming
  + W_BARU.a * c.sAliran + W_BARU.m * c.sMom), 0, 100);

// ---------------------------------------------------------------- calon fix
const CFG = { drawDiv: 0.6, capMOS: 50, capNilai: 65,
              bandarBlend: 0.4, bandarGate: -10 };

function skorV(x, opt) {
  opt = opt || {};
  const c = komponen(x.r, x.k, x.fase, x.val);
  const w = opt.w || W_BARU;
  const sN = opt.raw ? c.sNilai : c.sNfix;
  const parts = [w.n * sN, w.k * c.sKualitas, w.t * c.sTiming, w.a * c.sAliran];
  if (w.m > 0) parts.push(w.m * c.sMom);
  return clamp(Math.round(parts.reduce((a, b) => a + b, 0)), 0, 100);
}

function aksiV(fase, sc, val, pos, th, useBandarGate, mosBandar) {
  pos = pos == null ? 0.5 : pos;
  if (fase === "Distribusi") return "Hindari";
  if (val.mos <= 0) return "Pantau";
  if (fase === "Akumulasi" || fase === "Spring") {
    if (sc < th) return "Pantau";
    if (useBandarGate && mosBandar != null && mosBandar <= CFG.bandarGate) return "Pantau";
    return "Beli";
  }
  if (fase === "Markup") return (pos < 0.55 && sc >= 70) ? "Beli" : "Pantau";
  return sc >= 55 ? "Pantau" : "Hindari";
}

// Profil perbandingan pasca-kalibrasi. "SKOR BARU (halaman)" memakai
// SP.skor/SP.aksi asli — barisnya adalah kebenaran produk. sisanya
// kontrafaktual: skor lama (bobot 40/25/20/15, tanpa momrev/fix, th65),
// sensibilitas ambang, kontribusi fix MOS+bandar, dan kontribusi momrev.
const PROFILES = [
  { nama: "SKOR LAMA (pre-kalibrasi)", opt: { w: W_LAMA, raw: 1 }, th: 65 },
  { nama: "SKOR BARU (halaman)", base: true },
  { nama: "SKOR BARU th65", opt: {}, th: 65, gate: true },
  { nama: "SKOR LAMA+fix", opt: { w: W_LAMA }, th: 65, gate: true },
  { nama: "SKOR BARU tanpa momrev", opt: { w: { n: 0.21, k: 0.43, t: 0.21, a: 0.15, m: 0 } }, th: 70, gate: true },
];


// ---------------------------------------------------------------- muat data
const fiturPath = path.join(ROOT, "data", "diag-fitur.csv");
if (!fs.existsSync(fiturPath)) {
  console.error("data/diag-fitur.csv tidak ada — jalankan dulu: python scripts/diag-skor.py");
  process.exit(1);
}
const rowsRaw = SP.parseCSV(fs.readFileSync(fiturPath, "utf-8"));
if (!rowsRaw.length) { console.error("diag-fitur.csv kosong"); process.exit(1); }

let mirrorBeda = 0;
const data = [];
for (const rr of rowsRaw) {
  const r = {
    kode: rr.kode, nama: rr.nama, sektor: rr.sektor,
    harga: rr.harga, eps: rr.eps, ekuitas: rr.ekuitas, saham: rr.saham,
    laba: rr.laba, der: rr.der, cagr: rr.cagr, roe: rr.roe, pbv: rr.pbv,
    per: rr.per, eps_trend: rr.eps_trend, nilai_harian: rr.nilai_harian,
    s_sideways: rr.s_sideways, s_vol_ratio: rr.s_vol_ratio,
    s_freqspike: rr.s_freqspike, s_spring: rr.s_spring,
    s_closeabove: rr.s_closeabove, s_springlow: rr.s_springlow,
    s_resistance: rr.s_resistance, high_52: rr.high_52,
    ret20: orNull(rr.ret20),
  };
  const k = {
    dksei_asing_1m: orNull(rr.dksei_asing_1m),
    dksei_institusi_1m: orNull(rr.dksei_institusi_1m),
    asing_pct: orNull(rr.asing_pct),
    asing_avg_price: orNull(rr.asing_avg_price),
  };
  const val = SP.valuasi(r);
  const fase = SP.detectFase(r, k);
  const sc0 = SP.skor(r, k, fase, val);
  if (totalOf(komponen(r, k, fase, val)) !== sc0) mirrorBeda++;
  const pos = SP.posRange(r);
  const mosBandar = (k.asing_avg_price && toNum(r.harga) > 0)
    ? (k.asing_avg_price - toNum(r.harga)) / k.asing_avg_price * 100 : null;
  data.push({
    r, k, val, fase, sc0, pos, mosBandar,
    split: rr.split, t: rr.t,
    ret20: orNull(rr.ret20), ihsg_r1: orNull(rr.ihsg_r1),
    fwd20: orNull(rr.fwd20), fwd60: orNull(rr.fwd60),
    c: komponen(r, k, fase, val),
    act0: SP.aksi(fase, sc0, val, pos, mosBandar),
  });
}
if (mirrorBeda) console.log("[!] mirror komponen berbeda SP.skor pada " + mirrorBeda + " baris — periksa file ini.");

// Label yang dievaluasi: default fwd20 (1 bulan), argv "fwd60" = 3 bulan.
const LABEL = process.argv[2] === "fwd60" ? "fwd60" : "fwd20";

// ---------------------------------------------------------------- statistik
function pearson(xs, ys) {
  const n = xs.length;
  if (n < 3) return NaN;
  let sx = 0, sy = 0;
  for (let i = 0; i < n; i++) { sx += xs[i]; sy += ys[i]; }
  const mx = sx / n, my = sy / n;
  let num = 0, dx = 0, dy = 0;
  for (let i = 0; i < n; i++) {
    const a = xs[i] - mx, b = ys[i] - my;
    num += a * b; dx += a * a; dy += b * b;
  }
  return (dx > 0 && dy > 0) ? num / Math.sqrt(dx * dy) : NaN;
}
const fmtP = x => (isFinite(x) ? (x >= 0 ? " " : "") + x.toFixed(3) : "  -- ");
const fmtPct = x => (isFinite(x) ? (x >= 0 ? " " : "") + x.toFixed(1) + "%" : "   -- ");

const withFwd = data.filter(x => x[LABEL] != null);
const F = x => x[LABEL];
const splits = { ALL: withFwd, train: withFwd.filter(x => x.split === "train"),
                 test: withFwd.filter(x => x.split === "test") };

console.log("");
console.log("=".repeat(78));
console.log("DIAGNOSTIK SKOR — label " + LABEL + " | " + data.length + " baris ("
  + withFwd.length + " ber-label)");
console.log("=".repeat(78));
console.log("BASE RATE (tanpa skor apa pun — pembanding wajib tiap split):");
for (const s of ["train", "test", "ALL"]) {
  const rows = splits[s];
  const hijau = rows.filter(x => F(x) > 0).length;
  const mean = rows.reduce((a, x) => a + F(x), 0) / (rows.length || 1);
  console.log("  " + s.padEnd(6) + " n=" + String(rows.length).padStart(4)
    + "  hijau " + fmtPct(hijau / rows.length * 100)
    + "  rata2 " + (mean >= 0 ? "+" : "") + mean.toFixed(1) + "%");
}
console.log("");
console.log("korelasi PEARSON komponen vs " + LABEL);
console.log("komponen        " + "     ALL      train       test");
for (const key of ["sNilai", "sNfix", "sKualitas", "sTiming", "sAliran", "sMom"]) {
  const line = [splits.ALL, splits.train, splits.test]
    .map(rows => fmtP(pearson(rows.map(x => x.c[key]), rows.map(F)))).join("  ");
  console.log(key.padEnd(16) + line);
}
{
  const line = [splits.ALL, splits.train, splits.test]
    .map(rows => fmtP(pearson(rows.map(x => x.sc0), rows.map(F)))).join("  ");
  console.log("SKOR total      " + line);
  for (const [label, fn] of [
    ["ret20 (20 hari)", x => x.ret20],
    ["excess vs IHSG", x => (x.ret20 != null && x.ihsg_r1 != null ? x.ret20 - x.ihsg_r1 : null)],
    ["ihsg_r1 (regime)", x => x.ihsg_r1],
  ]) {
    const line = [splits.ALL, splits.train, splits.test].map(rows => {
      const p = rows.filter(x => fn(x) != null);
      return fmtP(pearson(p.map(fn), p.map(F))) + "(" + p.length + ")";
    }).join(" ");
    console.log(label.padEnd(16) + line);
  }
}

console.log("");
console.log("hit-rate Aksi (lift = hijau - base rate split; 'regime' = Beli hanya bila IHSG > 0)");
console.log("profil                split   nBeli  %Beli  hijau   lift   rata2fwd  rata2fwdSemua");
for (const p of PROFILES) {
  for (const s of ["train", "test", "ALL"]) {
    const rows = splits[s];
    const base = rows.filter(x => F(x) > 0).length / (rows.length || 1) * 100;
    let nBeli = 0, hijau = 0, sumB = 0, sumAll = 0;
    for (const x of rows) {
      sumAll += F(x);
      const sc = p.base ? x.sc0 : skorV(x, p.opt);
      let act = p.base ? x.act0 : aksiV(x.fase, sc, x.val, x.pos, p.th, !!p.gate, x.mosBandar);
      if (act === "Beli" && p.regime && !(x.ihsg_r1 != null && x.ihsg_r1 > 0)) act = "Pantau";
      if (act === "Beli") {
        nBeli++;
        sumB += F(x);
        if (F(x) > 0) hijau++;
      }
    }
    const pctBeli = rows.length ? nBeli / rows.length * 100 : NaN;
    const hit = nBeli ? hijau / nBeli * 100 : NaN;
    const meanB = nBeli ? sumB / nBeli : NaN;
    const meanAll = rows.length ? sumAll / rows.length : NaN;
    console.log(p.nama.padEnd(24) + s.padEnd(7)
      + String(nBeli).padStart(6) + fmtPct(pctBeli).padStart(7)
      + fmtPct(hit).padStart(7)
      + (isFinite(hit) ? (hit - base >= 0 ? " +" : " ") + (hit - base).toFixed(1) : "  --").padStart(6) + "pp"
      + (isFinite(meanB) ? (meanB >= 0 ? " " : "") + meanB.toFixed(1) : " --").padStart(9) + "%"
      + (meanAll >= 0 ? " " : "") + meanAll.toFixed(1).padStart(9) + "%");
  }
  console.log("");
}

// Sebaran fase pada baris ber-label — konteks membaca angka di atas.
const faseCnt = {};
for (const x of withFwd) faseCnt[x.fase] = (faseCnt[x.fase] || 0) + 1;
console.log("sebaran fase: " + Object.entries(faseCnt).map(([f, n]) => f + "=" + n).join("  "));
console.log("");
console.log("baca: kolom 'hijau' = % baris Beli yang fwd20 > 0. profil dipilih dari");
console.log("baris 'test' (bulan terakhir, tak dipakai saat menyusun konstanta).");
