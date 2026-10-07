// Uji smoke mesin screener-praktis.html (tanpa browser).
// Pakai: node _test-praktis.js
"use strict";
const fs = require("fs");
const path = require("path");
const cp = require("child_process");

const HERE = __dirname;
let gagal = 0;
function cek(nama, kondisi, info) {
  if (kondisi) { console.log("  OK   " + nama); }
  else { gagal++; console.log("  GAGAL " + nama + (info ? "  -> " + info : "")); }
}

const html = fs.readFileSync(path.join(HERE, "..", "web", "screener-praktis.html"), "utf-8");

// 1) cek sintaks seluruh blok <script>
const blocks = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const script = blocks.reduce((a, b) => (a.length > b.length ? a : b), "");
const tmp = path.join(HERE, ".tmp-praktis-check.js");
fs.writeFileSync(tmp, script, "utf-8");
try {
  cp.execSync("node --check \"" + tmp + "\"", { stdio: "pipe" });
  cek("sintaks blok <script> HTML valid", true);
} catch (e) {
  cek("sintaks blok <script> HTML valid", false, String(e.stderr || e));
}
fs.unlinkSync(tmp);

// 2) ekstrak modul SP dan jalankan
const m = script.match(/var SP = \(function \(\) \{[\s\S]*?\n\}\)\(\);/);
cek("modul SP ditemukan", !!m);
if (!m) process.exit(gagal ? 1 : 0);
const SP = new Function(m[0] + "; return SP;")();

// 3) data nyata
const csv = fs.readFileSync(path.join(HERE, "..", "contoh", "data-10-emiten.csv"), "utf-8");
const ksei = JSON.parse(fs.readFileSync(path.join(HERE, "..", "data", "ksei.json"), "utf-8"));

const rows = SP.parseCSV(csv);
cek("parseCSV: 10 baris emiten", rows.length === 10, "dapat " + rows.length);
cek("parseCSV: kolom kode terbaca", rows[0].kode === "BBCA", rows[0] && rows[0].kode);

const kmap = SP.ingestKsei(ksei, {});
cek("ingestKsei: BBCA ada", !!kmap.BBCA && typeof kmap.BBCA.asing_pct === "number");
cek("ingestKsei: 1000+ emiten", Object.keys(kmap).length > 900, "dapat " + Object.keys(kmap).length);

const data = SP.build(rows, kmap);
cek("build: 10 record", data.length === 10, "dapat " + data.length);
const data2 = SP.build(rows, kmap);
cek("build deterministik (fase/skor/aksi sama)", data.every(function (x, i) { return x.fase === data2[i].fase && x.skor === data2[i].skor && x.aksi === data2[i].aksi; }));

const fases = {}; let skorOk = true, mosFinite = true, intiOk = true;
data.forEach(x => {
  fases[x.fase] = (fases[x.fase] || 0) + 1;
  if (!(Number.isInteger(x.skor) && x.skor >= 0 && x.skor <= 100)) skorOk = false;
  if (!isFinite(x.val.mos)) mosFinite = false;
  if (!(x.val.intrinsic > 0)) intiOk = false;
});
cek("semua skor integer 0..100", skorOk);
cek("semua MOS terhitung", mosFinite);
cek("semua nilai intrinsik > 0", intiOk);
console.log("       sebaran fase contoh:", JSON.stringify(fases));
cek("contoh memuat 'Akumulasi'", (fases["Akumulasi"] || 0) > 0);
cek("contoh memuat 'Spring'", (fases["Spring"] || 0) > 0);
cek("contoh: TLKM = Spring", (data.find(x => x.kode === "TLKM") || {}).fase === "Spring");
cek("contoh: BBCA = Akumulasi", (data.find(x => x.kode === "BBCA") || {}).fase === "Akumulasi");
cek("contoh: PTBA = Markup (asing masuk kuat)", (data.find(x => x.kode === "PTBA") || {}).fase === "Markup");

// 4) fase yang jarang ada — dibuat manual untuk memastikan logika benar
const dist = { kode: "TEST", harga: "980", s_springlow: "900", s_resistance: "1000",
  s_vol_ratio: "1.6", s_sideways: "0", s_spring: "0", s_closeabove: "1", eps: "50", ekuitas: "10000", saham: "1000", laba: "1500", cagr: "5" };
cek("distribusi terdeteksi", SP.detectFase(dist, { dksei_asing_1m: -1.2 }) === "Distribusi");
cek("markup terdeteksi", SP.detectFase(dist, { dksei_asing_1m: 1.2 }) === "Markup");
cek("spring mengalahkan markup", SP.detectFase(Object.assign({}, dist, { s_spring: "1" }), { dksei_asing_1m: 1.2 }) === "Spring");

// 5) MOS: harga jauh di bawah nilai intrinsik harus positif
const murah = { kode: "MURAH", harga: "100", eps: "100", ekuitas: "50000", saham: "1000", laba: "10000", cagr: "10" };
cek("MOS positif saat murah", SP.valuasi(murah).mos > 0);

// 6) skor & aksi pasca-kalibrasi Fase 0 (2026-10-02)
{
  const r0 = rows[0], k0 = kmap[r0.kode] || {};
  const val0 = SP.valuasi(r0), fase0 = SP.detectFase(r0, k0);
  const skorTurun = SP.skor(Object.assign({}, r0, { ret20: "-8" }), k0, fase0, val0);
  const skorNaik = SP.skor(Object.assign({}, r0, { ret20: "8" }), k0, fase0, val0);
  cek("momrev: ret20 -8% menaikkan skor vs +8%", skorTurun > skorNaik,
    skorTurun + " vs " + skorNaik);
  const skorTanpa = SP.skor(r0, k0, fase0, val0);   // ret20 kosong -> netral 50
  cek("momrev netral bila ret20 kosong", Number.isInteger(skorTanpa) && skorTanpa >= 0 && skorTanpa <= 100);

  const mosOk = { mos: 30 }, mosDalam = { mos: -5 };
  cek("aksi: Akumulasi skor 68 < 70 -> Pantau", SP.aksi("Akumulasi", 68, mosOk, 0.5) === "Pantau");
  cek("aksi: Akumulasi skor 70 -> Beli", SP.aksi("Akumulasi", 70, mosOk, 0.5) === "Beli");
  cek("aksi: gerbang bandar (mosBandar -15) tahan Beli", SP.aksi("Akumulasi", 85, mosOk, 0.5, -15) === "Pantau");
  cek("aksi: mosBandar -5 lolos gerbang", SP.aksi("Akumulasi", 85, mosOk, 0.5, -5) === "Beli");
  cek("aksi: MOS<=0 tetap Pantau", SP.aksi("Akumulasi", 95, mosDalam, 0.5) === "Pantau");
  cek("aksi: Distribusi tetap Hindari", SP.aksi("Distribusi", 95, mosOk, 0.9) === "Hindari");
}

// 7) horizon, umur fase & kontrak (Fase eksekusi 2026-10-02)
{
  cek("KALIBRASI tersedia & lengkap", SP.KALIBRASI && SP.KALIBRASI.hijau3 === "50,4%" && SP.KALIBRASI.lift1 === "+2,5pp");
  cek("expiryKontrak: +84 hari kalender", SP.expiryKontrak("2026-10-02") === "2026-12-25", SP.expiryKontrak("2026-10-02"));
  const st = SP.statusKontrak({ buka: "2026-10-02", kdl: "2026-12-25" }, "2026-10-10");
  cek("statusKontrak: hari & sisa benar", st.hari === 8 && st.sisa === 76 && !st.lewat, JSON.stringify(st));
  const stL = SP.statusKontrak({ buka: "2026-10-02", kdl: "2026-12-25" }, "2027-01-01");
  cek("statusKontrak: lewat -> kedaluwarsa", stL.lewat === true && stL.sisa < 0, JSON.stringify(stL));
  cek("umurFase: 20 hari", SP.umurFase("2026-10-01", "2026-10-21") === 20);
  cek("umurFase: tak negatif", SP.umurFase("2026-10-21", "2026-10-01") === 0);
  cek("tanggalIndo: 2 Okt 2026", SP.tanggalIndo("2026-10-02") === "2 Okt 2026", SP.tanggalIndo("2026-10-02"));

  cek("banner horizon ada di HTML", html.includes('id="horizonWarn"'));
  cek("select timeframe 4 mode di drawer", html.includes('id="dwHorizon"') && html.includes("max 1 day") && html.includes("max 1 month"));
  cek("umur fase: sp_umur + kolom tabel", html.includes('localStorage.getItem("sp_umur")') && html.includes('t: "Umur Fase"'));
  cek("kontrak: sp_kontrak + kolom tabel", html.includes('localStorage.getItem("sp_kontrak")') && html.includes('t: "Kontrak"'));
  cek("dropdown metode ada di toolbar", html.includes('id="metode"') && html.includes("Barang Kering"));
  cek("render memakai matchMetode", html.includes("S.metode") && html.includes("matchMetode"));
  cek("pilihan metode dipersist", html.includes("sp_metode"));
  cek("kolom Likuid ada", html.includes('t: "Likuid"'));
  cek("blok akumulasi drawer ada", html.includes("Akumulasi 30 hari") && html.includes("barAkumulasi") && html.includes("Siapa yang serap"));
  cek("ambang likuid 5M", html.includes("5000000000"));
  cek("kolom FV ada", html.includes('t: "FV"'));
  cek("rincian FV drawer ada", html.includes("FV Graham") && html.includes("FV ROE-PBV") && html.includes("FV Equity growth"));
  cek("state scope ada", html.includes("scope: {}"));
  cek("endpoint scope dipakai", html.includes("/api/scope"));
  cek("badge Scope di makro", html.includes("Scope:</span>"));
  cek("kolom Combo ada", html.includes('t: "Combo"'));
  cek("blok kombo drawer ada", html.includes("Kombo smart-money") && html.includes("SP.combo"));
  cek("helper combo ada", html.includes("comboLvl"));
  cek("dropdown Tema ada", html.includes('id="tema"'));
  cek("smartMoney ada", html.includes("SP.smartMoney"));
  cek("blok smart money drawer ada", html.includes("Smart money vs harga kita"));
  cek("aturan terlalu-jauh ada", html.includes("Terlalu jauh di atas harga smart money"));
  cek("panel quest ada", html.includes('id="questPanel"') && html.includes("Misi Malam Ini"));
  cek("suspen dipakai", html.includes("SP.suspen"));
  cek("css kode-susp ada", html.includes("kode-susp"));
  cek("bounty dipakai", html.includes("SP.bounty"));
  cek("arsip sp_bounty ada", html.includes("sp_bounty"));
  cek("kolom centang ada", html.includes('id="pickAll"') && html.includes("pickRow"));
  cek("tombol tambah ada", html.includes('id="btnTambah"'));
  cek("cekBar ada", html.includes('id="cekBar"'));
  cek("picked state ada", html.includes("S.picked"));
  cek("exitLevel ada", html.includes("SP.exitLevel"));
  cek("drawer live selaraskan tabel", html.includes("S.data[sdi] = b"));
  cek("blok level drawer ada", html.includes("exit liquidity") && html.includes("rata-rata jual"));
  cek("panel sektoral ada", html.includes('id="sektorPanel"') && html.includes("Rotasi sektoral"));
  cek("renderSektor dipanggil di rebuild", html.includes("renderSektor"));
  cek("makro memuat item Sektor", html.includes("Sektor:</span>"));
  cek("angka banner/help pakai KALIBRASI (satu sumber)", html.includes("SP.KALIBRASI.hijau3"));
}

// 8) preset metode screening (label Indonesia)
{
  cek("METODE tersedia (5 preset)", Array.isArray(SP.METODE) && SP.METODE.length === 5, String(SP.METODE));
  const bSide = { kode: "SIDE", nama: "Side", r: { harga: "1000", s_sideways: "1", s_vol_ratio: "0.7", s_spring: "0", s_closeabove: "1", s_springlow: "950", s_resistance: "1050" }, k: {}, fase: "Akumulasi", pos: 0.3 };
  const bSpring = { kode: "SPR", nama: "Spr", r: { harga: "1000", s_sideways: "0", s_vol_ratio: "1.0", s_spring: "1", s_closeabove: "1", s_springlow: "950", s_resistance: "1050" }, k: {}, fase: "Spring", pos: 0.2 };
  const bBreak = { kode: "BRK", nama: "Brk", r: { harga: "1000", s_sideways: "0", s_vol_ratio: "1.4", s_spring: "0", s_closeabove: "1", s_springlow: "900", s_resistance: "1050" }, k: {}, fase: "Markup", pos: 0.8 };
  const bCont = { kode: "CTC", nama: "Ctc", r: { harga: "1000", s_sideways: "0", s_vol_ratio: "0.9", s_spring: "0", s_closeabove: "1", s_springlow: "900", s_resistance: "1050" }, k: {}, fase: "Netral", pos: 0.5 };
  const bJelang = { kode: "JEL", nama: "Jel", r: { harga: "1000", s_sideways: "0", s_vol_ratio: "1.2", s_spring: "0", s_closeabove: "1", s_springlow: "900", s_resistance: "1050" }, k: {}, fase: "Netral", pos: 0.65 };
  cek("matchMetode ada", typeof SP.matchMetode === "function");
  cek("barang kering lolos", SP.matchMetode(bSide, "Barang Kering") === true);
  cek("barang kering bukan lolos-resistance", SP.matchMetode(bSide, "Lolos Resistance") === false);
  cek("kocokan = spring", SP.matchMetode(bSpring, "Kocokan Terakhir") === true);
  cek("lolos butuh pos tinggi", SP.matchMetode(bBreak, "Lolos Resistance") === true);
  cek("jelang di tengah range", SP.matchMetode(bJelang, "Jelang Breakout") === true);
  cek("jelang bukan barang kering", SP.matchMetode(bJelang, "Barang Kering") === false);
  cek("kontraksi tetap", SP.matchMetode(bCont, "Kontraksi VCP") === true);
  cek("Semua lolos semua", SP.matchMetode(bSide, "Semua") === true);
}

// 9) agregat sektoral + narasi
{
  const rows9 = [
    { kode: "ADRO", sektor: "Energi", r: { ret20: "5" } },
    { kode: "PTBA", sektor: "Energi", r: { ret20: "1" } },
    { kode: "BBCA", sektor: "Keuangan", r: { ret20: "-2" } },
    { kode: "NON", sektor: "", r: {} }
  ];
  const ag = SP.agregatSektor(rows9);
  cek("agregat: 3 grup (Energi, Keuangan, Lainnya)", ag.length === 3, JSON.stringify(ag.map(g => g.sektor)));
  cek("agregat: Energi teratas avg +3,0%", ag[0].sektor === "Energi" && ag[0].avg1m === 3, JSON.stringify(ag[0]));
  cek("agregat: breadth Energi 2/2", ag[0].hijau === 2 && ag[0].total === 2);
  cek("agregat: pendorong ADRO dulu", ag[0].pendorong[0].kode === "ADRO" && ag[0].pendorong.length === 2);
  const nar = SP.narasiSektor(ag, 4);
  cek("narasi menyebut sektor + pendorong + sampel kecil", nar.includes("Energi") && nar.includes("ADRO") && nar.includes("sampel kecil"), nar);
  cek("narasi kosong bila tanpa return", SP.narasiSektor(SP.agregatSektor([{ kode: "X", sektor: "A", r: {} }]), 1).includes("Belum ada data"));
}

// 10) bar akumulasi harian
{
  const up = [[100, 500], [101, 2000], [102, 2000], [103, 100]];
  const bu = SP.barAkumulasi(up);
  cek("barAkumulasi: 4 hasil, hari pertama abu", bu.length === 4 && bu[0].c === "A", JSON.stringify(bu));
  cek("barAkumulasi: naik+vol tinggi = hijau", bu[1].c === "H" && bu[2].c === "H");
  cek("barAkumulasi: naik+vol kecil = abu", bu[3].c === "A");
  const dn = [[100, 500], [99, 2000], [98, 100]];
  const bd = SP.barAkumulasi(dn);
  cek("barAkumulasi: turun+vol tinggi = merah", bd[1].c === "M" && bd[2].c === "A");
  cek("barAkumulasi: kosong aman", Array.isArray(SP.barAkumulasi(undefined)) && SP.barAkumulasi(undefined).length === 0);
}

// 11) rincian fair value
{
  const mur = { kode: "MURAH", harga: "100", eps: "100", ekuitas: "50000", saham: "1000", laba: "10000", cagr: "10" };
  const vm = SP.valuasi(mur);
  cek("rincian: 3 komponen valid", vm.nMetode === 3 && vm.rincian.graham > 0 && vm.rincian.roepbv > 0 && vm.rincian.growth > 0, JSON.stringify(vm.rincian));
  cek("rincian: graham terbesar, median = growth", vm.rincian.graham > vm.rincian.roepbv && vm.intrinsic === vm.rincian.growth, vm.intrinsic + " vs " + vm.rincian.growth);
  const kosong = SP.valuasi({});
  cek("rincian: kosong aman", kosong.intrinsic === 0 && kosong.nMetode === 0 && kosong.rincian.graham === 0);
}

// 11b) anti-sampah BVPS (kasus ADRO: bookValue USD vs harga IDR)
{
  const adro = { kode: "ADRO", harga: "2500", eps: "361", ekuitas: "4608079072", saham: "28800494200", laba: "0", cagr: "0" };
  const va = SP.valuasi(adro);
  cek("sampah: PBV absurd disembunyikan", va.pbv === null && va.bvpsRusak === true, JSON.stringify({ pbv: va.pbv, rusak: va.bvpsRusak }));
  cek("sampah: metode BVPS keluar dari median", va.nMetode === 1 && va.rincian.graham > 0 && va.rincian.roepbv === 0, "nMetode=" + va.nMetode);
  const fund = { nilai: { bvps: 3070, roe: 11.13 }, sumber: { bvps: "SS", roe: "SS" } };
  const vf = SP.valuasi(adro, fund);
  cek("sampah: fund override pulihkan PBV", vf.bvps === 3070 && Math.abs(vf.pbv - 0.814) < 0.02 && vf.nMetode === 3, JSON.stringify({ bvps: vf.bvps, pbv: vf.pbv, n: vf.nMetode }));
  const vn = SP.valuasi({ kode: "N", harga: "100", eps: "10", ekuitas: "5000", saham: "100", laba: "1000", cagr: "5" });
  cek("sampah: data normal tak berubah", vn.bvpsRusak === false && Math.abs(vn.pbv - 2) < 1e-9 && vn.nMetode === 3, JSON.stringify({ pbv: vn.pbv, n: vn.nMetode }));
  const b1 = SP.build([Object.assign({ nama: "ADRO" }, adro)], {})[0];
  const b2 = SP.build([Object.assign({ nama: "ADRO" }, adro)], {}, { ADRO: fund })[0];
  cek("sampah: build tanpa fund tetap jalan", b1.val.pbv === null && b1.val.intrinsic > 0);
  cek("sampah: build dengan fund pakai BVPS benar", Math.abs(b2.val.pbv - 0.814) < 0.02, String(b2.val.pbv));
}

// 12) kombo smart-money
{
  const d10 = new Date(Date.now() - 10 * 864e5).toISOString().slice(0, 10);
  const sc = { acc: { top_buyers: [{ broker: "OD", nval: 5 }], top_sellers: [], series: { OD: [[1, 1], [2, 3], [-1, 2], [3, 5], [4, 9]] } }, insider: [{ name: "DIR A", date: d10, action_type: "buy", changes_value: "100", badges: ["DIREKTUR"] }] };
  const c3 = SP.combo({ kode: "T", fase: "Spring" }, sc);
  cek("combo: 3 YES fase Spring = C3", c3.level === 3, JSON.stringify(c3));
  const cB = SP.combo({ kode: "T", fase: "Spring" }, { acc: sc.acc, insider: [{ name: "X", date: d10, action_type: "sell" }] });
  cek("combo: insider sell = breaker C1", cB.level === 1 && !!cB.breaker, JSON.stringify(cB));
  const c2 = SP.combo({ kode: "T", fase: "Markup" }, sc);
  cek("combo: tanpa fase = maks C2", c2.level === 2, JSON.stringify(c2));
  const cN = SP.combo({ kode: "T", fase: "Spring" }, null);
  cek("combo: tanpa scope = —", cN.level === -1);
  const cU = SP.combo({ kode: "T", fase: "Spring" }, { acc: {}, insider: [] });
  cek("combo: UNKNOWN tampil ?", cU.bukti[0].st === "?" && cU.level <= 1, JSON.stringify(cU));
}

// 13) exit-liquidity level
{
  const sv = [];
  for (let i = 0; i < 20; i++) sv.push([-1000, -1000 * (i + 1), 1000, 900 - i]);
  const sv2 = sv.map(p => [-500, p[1], 1000, p[3] - 20]);
  const bv = [];
  for (let i = 0; i < 20; i++) bv.push([1000, 1000 * (i + 1), 900 - i, 1000]);
  const scX = { acc: { top_sellers: [{ broker: "OD" }, { broker: "AK" }], top_buyers: [{ broker: "CC" }, { broker: "YU" }], series: { OD: sv, AK: sv2, CC: bv, YU: bv } } };
  const aL = SP.exitLevel({ r: { harga: "1000" }, fase: "Distribusi" }, scX, 2);
  cek("exitLevel: alarm premium + broker", aL && aL.tipe === "alarm" && aL.broker.length === 2 && aL.premium >= 3, JSON.stringify(aL));
  const bL = SP.exitLevel({ r: { harga: "800" }, fase: "Akumulasi" }, scX, 2);
  cek("exitLevel: bargain di bawah avg beli", bL && bL.tipe === "bargain", JSON.stringify(bL));
  const nL = SP.exitLevel({ r: { harga: "900" }, fase: "Netral" }, scX, 2);
  cek("exitLevel: netral tanpa alarm", nL === null, JSON.stringify(nL));
  cek("exitLevel: cache lama ditandai", SP.exitLevel({ r: { harga: "1000" }, fase: "Distribusi" }, scX, 1).stale === true);
  cek("exitLevel: tanpa savg null", SP.exitLevel({ r: { harga: "1000" }, fase: "Distribusi" }, { acc: { top_sellers: [{ broker: "OD" }], top_buyers: [], series: { OD: [[-1, -1, null, null]] } } }, 2) === null);
}

// 14) smart money vs harga kita
{
  const ex = { kode: "T", fase: "Akumulasi", r: { harga: "900" }, asing_avg: 1000, val: { intrinsic: 1200 } };
  const en = { acc: { top_buyers: [{ broker: "OD" }], series: { OD: [[10, 10, 800, 810]] } }, insider: [{ name: "DIR A", date: "2026-09-20", action_type: "buy", price_formatted: "1,100" }] };
  const sm = SP.smartMoney(ex, en, 0);
  cek("smartMoney: 3 baris + terbaik = broker termurah", sm.rows.length === 3 && sm.terbaik.sumber === "Broker OD", JSON.stringify(sm));
  cek("smartMoney: jarak +12,5% di atas avg broker", Math.abs(sm.jarakPct - 12.5) < 0.01, String(sm.jarakPct));
  cek("smartMoney: upside +33,3%", Math.abs(sm.upsidePct - 33.33) < 0.1, String(sm.upsidePct));
  const sm0 = SP.smartMoney({ kode: "T", fase: "X", r: { harga: "900" }, val: {} }, null, 0);
  cek("smartMoney: tanpa data aman", sm0.terbaik === null);
}

// 15) bounty 3 quest
{
  const rows15 = [
    { kode: "AA", r: { nilai_harian: "9000000000" } },
    { kode: "BB", r: { nilai_harian: "9000000000" } },
    { kode: "CC", r: { nilai_harian: "9000000000" } },
    { kode: "DD", r: { nilai_harian: "9000000000" } },
    { kode: "XX", r: { nilai_harian: "1000000" } },
    { kode: "YY", r: {} }
  ];
  const d60 = new Date(Date.now() - 10 * 864e5).toISOString().slice(0, 10);
  const sc15 = { pulse: { top_net_buy: [{ kode: "AA", broker: "OD", nval: 5 }] }, emiten: {
    AA: { acc: { top_buyers: [{ broker: "OD" }], series: { OD: [[1, 1], [1, 1], [1, 1], [1, 1], [1, 1]] } }, insider: [{ name: "DIR A", date: d60, action_type: "buy" }] },
    BB: { acc: { top_buyers: [{ broker: "CC" }], series: { CC: [[1, 1], [1, 1], [-1, 1], [1, 1], [-1, 1]] } }, insider: [] },
    CC: { acc: { top_buyers: [{ broker: "YU" }], series: { YU: [[1, 1], [1, 1], [1, 1], [1, 1], [1, 1]] } }, insider: [] },
    DD: { acc: { top_buyers: [{ broker: "SQ" }], series: { SQ: [[-1, 1], [-1, 1], [-1, 1], [-1, 1], [-1, 1]] } }, insider: [] } } };
  const bq = SP.bounty(rows15, sc15);
  cek("bounty: tepat 3 (illiquid + tanpa scope tersingkir)", bq.length === 3, JSON.stringify(bq.map(q => q.kode)));
  cek("bounty: AA teratas 100", bq[0].kode === "AA" && bq[0].skor === 100, JSON.stringify(bq[0]));
  cek("bounty: breakdown benar", bq[0].rinci.pulse === 50 && bq[0].rinci.streak === 30 && bq[0].rinci.insider === 20);
  cek("bounty: tanpa scope kosong", SP.bounty(rows15, {}).length === 0);
}

// 16) exitLevel/smartMoney via peta avg IndoPremier
{
  const eIP = { acc: { top_sellers: [{ broker: "OD" }, { broker: "AK" }], top_buyers: [{ broker: "CC" }, { broker: "YU" }], avgS: { OD: 880, AK: 870 }, avgB: { CC: 890, YU: 895 }, sumber: "IP" } };
  const aIP = SP.exitLevel({ r: { harga: "1000" }, fase: "Distribusi" }, eIP, 1);
  cek("exitLevel: peta IP tanpa scope v2", aIP && aIP.tipe === "alarm" && Math.abs(aIP.level - 875) < 0.01, JSON.stringify(aIP));
  const mIP = SP.smartMoney({ r: { harga: "900" }, val: {} }, eIP, 0);
  cek("smartMoney: broker dari peta IP", mIP.rows.some(r => r.sumber === "Broker CC" && r.avg === 890), JSON.stringify(mIP.rows));
}

// 17) direktori broker
{
  const dir = { OD: { kat: "smart", nama: "BRI Danareksa", afiliasi: "" }, XL: { kat: "ritel", nama: "Stockbit", afiliasi: "", kombo: true }, XC: { kat: "ritel", nama: "Ajaib", afiliasi: "", kombo: true } };
  cek("brokerInfo: OD smart", SP.brokerInfo("OD", 0, dir).label.includes("Smart money"));
  cek("brokerInfo: XL besar bukan ritel", SP.brokerInfo("XL", 2000000000, dir).flag === "besar, bukan ritel");
  cek("brokerInfo: XL kecil tetap ritel", SP.brokerInfo("XL", 50000000, dir).flag === "" && SP.brokerInfo("XL", 50000000, dir).warna === "#fdd835");
  cek("brokerInfo: campuran 100jt-1M", SP.brokerInfo("XL", 500000000, dir).flag === "campuran");
  cek("brokerInfo: tak dikenal abu", SP.brokerInfo("ZZ", 0, dir).warna === "#8a8f98");
  cek("brokerInfo: tanpa nval tanpa flag", SP.brokerInfo("XL", null, dir).flag === "");
  cek("brTag dipakai", html.includes("brTag("));
  cek("legenda broker ada", html.includes("Direktori broker"));
  cek("bahasa sederhana ada", html.includes("toko kelontong") && html.includes("sederhanaVerdict") && html.includes("sederhanaBandar") && html.includes("banderol per lembar") && html.includes("uang tunai beneran"));
  cek("endpoint stock dipakai", html.includes("/api/stock"));
  cek("drawer live ada", html.includes("Mengambil laporan segar") && html.includes("muat ulang"));
  cek("loadbar ada", html.includes("loadbar"));
  cek("fundBox ada", html.includes("Arus kas OCF/FCF") && html.includes("SP.gabung"));
  cek("blok saing ada", html.includes("Banding kompetitor") && html.includes("SP.pesaing") && html.includes("btnBanding") && html.includes("saingPick"));
  cek("helper saing ada", html.includes("saingBox"));
}

// 18) gabung fundamental
{
  const rr = { harga: "1000", eps: "10", roe: "", der: "", pbv: "", ekuitas: "", saham: "" };
  const ff = { nilai: { roe: 20, eps: 12 }, sumber: { roe: "IP", eps: "IP" }, flag: [], tren: { roe: "naik" }, kas: { ocf: 5, fcf: 4 }, fv_graham: 1500 };
  const g = SP.gabung(rr, ff);
  cek("gabung: prioritas IP", g.tampil.roe.v === 20 && g.tampil.roe.s === "IP");
  cek("gabung: fallback Yahoo", SP.gabung({ harga: "1", eps: "7" }, null).tampil.eps.v === 7);
  const g2 = SP.gabung({ harga: "1", eps: "10", roe: "", ekuitas: "100", saham: "10", laba: "5" }, { nilai: { roe: 30 }, sumber: { roe: "SS" }, flag: [], tren: {}, kas: {} });
  cek("gabung: konflik >25% flag", g2.flag.length > 0 && g2.tampil.roe.v === 30, JSON.stringify(g2));
}

// 19) banding kompetitor
{
  const fd = {
    A: { klasifikasi: { industri: ["Bank"] }, sejenis: ["B", "C"] },
    B: { klasifikasi: { industri: ["Bank"] }, sejenis: [] },
    C: { klasifikasi: { industri: ["Bank"] }, sejenis: [] },
    D: { klasifikasi: { industri: ["Energi"] }, sejenis: [] }
  };
  const dd = [
    { kode: "A", r: { harga: "1000" }, val: { per: 10, pbv: 1, roe: 20, intrinsic: 1200, mos: 15 }, fase: "Akumulasi", skor: 70 },
    { kode: "B", r: { harga: "2000" }, val: { per: 20, pbv: 2, roe: 10, intrinsic: 1800, mos: -5 }, fase: "Markup", skor: 60 },
    { kode: "C", r: { harga: "3000" }, val: { per: 30, pbv: 3, roe: 5, intrinsic: 2500, mos: 0 }, fase: "Netral", skor: 50 },
    { kode: "D", r: { harga: "4000" }, val: { per: 5, pbv: 0.5, roe: 30, intrinsic: 5000, mos: 25 }, fase: "Netral", skor: 55 }
  ];
  const p = SP.pesaing("A", dd, fd);
  cek("pesaing: 2 peer se-industri (D tersingkir)", p.peers.length === 2 && p.peers[0].kode === "B", JSON.stringify(p.peers.map(q => q.kode)));
  cek("pesaing: industri Bank", p.industri === "Bank");
  cek("pesaing: median pbv 2 roe 10", p.med.pbv === 2 && p.med.roe === 10, JSON.stringify(p.med));
  cek("pesaing: rank pbv 1 roe 1", p.rankPbv === 1 && p.rankRoe === 1);
  cek("pesaing: vonis menyebut termurah + tertinggi", p.vonis.includes("termurah") && p.vonis.includes("tertinggi"), p.vonis);
  cek("pesaing: tanpa fund aman", SP.pesaing("Z", dd, {}).peers.length === 0);
}

// 20) label industri
{
  const fm = {
    SUPA: { klasifikasi: { industri: ["Bank"], bisnis: ["Digital Banking", "Banking"] }, sejenis: [] },
    BBCA: { klasifikasi: { industri: ["Bank"], bisnis: ["Banking", "Corporate Banking"] }, sejenis: [] },
    MERK: { klasifikasi: { industri: ["Farmasi &amp; Riset Kesehatan"], bisnis: [] }, sejenis: [] }
  };
  cek("industri: bank digital bila bisnis utama digital", SP.industriLabel("SUPA", fm, "") === "Bank Digital");
  cek("industri: bank konvensional tetap Bank", SP.industriLabel("BBCA", fm, "") === "Bank");
  cek("industri: decode entitas HTML", SP.industriLabel("MERK", fm, "") === "Farmasi & Riset Kesehatan");
  cek("industri: fallback sektor", SP.industriLabel("XX", {}, "Keuangan") === "Keuangan");
  cek("industri: kosong aman", SP.industriLabel("XX", {}, "") === "—");
  cek('kolom Industri ada', html.includes('t: "Industri"'));
}

// 21) suspen heuristik
{
  const xSusp = { kode: "ZZZZ", r: { harga: "1000", nilai_harian: "0", s_vol_ratio: "0", sumber: "Yahoo Finance + IDX - kualitas baik" } };
  const xOk = { kode: "BBCA", r: { harga: "9000", nilai_harian: "9000000000", s_vol_ratio: "1.2", sumber: "Yahoo Finance + IDX - kualitas baik" } };
  cek("suspen: nilai 0 -> true", SP.suspen(xSusp) === true);
  cek("suspen: normal -> false", SP.suspen(xOk) === false);
  cek("suspen: tanpa data -> false", SP.suspen({}) === false);
  cek("suspen: harga kosong -> true", SP.suspen({ r: { harga: "0", nilai_harian: "100", s_vol_ratio: "1" } }) === true);
}

// 22) timeframe mode
{
  const r = { harga: "1000", eps: "100", ekuitas: "50000", saham: "1000", laba: "10000", cagr: "10", der: "0.5", eps_trend: "up", nilai_harian: "9000000000", s_vol_ratio: "1.5", s_freqspike: "0", s_sideways: "0", ret20: "0.05" };
  const val = SP.valuasi(r, {});
  const k = { dksei_asing_1m: 1.0, dksei_institusi_1m: 0.5 };
  cek("tf: config 4 mode ada", ["scalp", "kilat", "minggu", "bulan"].every(t => !!(SP.TF && SP.TF[t])), JSON.stringify(SP.TF && Object.keys(SP.TF)));
  cek("tf: skor integer 0..100 semua mode", ["scalp", "kilat", "minggu", "bulan"].every(t => { const s = SP.skorTF(r, k, "Markup", val, t); return Number.isInteger(s) && s >= 0 && s <= 100; }));
  const rMurah = Object.assign({}, r, { harga: "100" });
  const rMahal = Object.assign({}, r, { harga: "5000" });
  cek("tf: scalping abaikan MOS (murah==mahal)", SP.skorTF(rMurah, k, "Markup", SP.valuasi(rMurah, {}), "scalp") === SP.skorTF(rMahal, k, "Markup", SP.valuasi(rMahal, {}), "scalp"));
  cek("tf: bulanan bedakan murah vs mahal", SP.skorTF(rMurah, k, "Markup", SP.valuasi(rMurah, {}), "bulan") !== SP.skorTF(rMahal, k, "Markup", SP.valuasi(rMahal, {}), "bulan"));
  cek("tf: distribusi selalu Hindari", ["scalp", "kilat", "minggu", "bulan"].every(t => SP.aksiTF("Distribusi", 95, val, 0.9, null, t, {}) === "Hindari"));
  cek("tf: kilat lock H+0 bukan Beli", SP.aksiTF("Markup", 90, val, 0.6, null, "kilat", { isLockH0: true }) !== "Beli");
  const sisa = SP.sisaTF("2026-10-01", "2026-10-05", "kilat");
  cek("tf: sisa kilat H+3 KDL", sisa.lewat === true && sisa.label === "KDL", JSON.stringify(sisa));
  const sisa2 = SP.sisaTF("2026-10-04", "2026-10-05", "minggu");
  cek("tf: sisa minggu H+1", sisa2.lewat === false && sisa2.label === "H+1", JSON.stringify(sisa2));
  cek("tf: mode tak dikenal jatuh ke bulan", SP.skorTF(r, k, "Markup", val, "ngaco") === SP.skorTF(r, k, "Markup", val, "bulan"));
  cek("tf: segmented control ada", html.includes('id="tfSeg"') && html.includes("max 1 day") && html.includes("max 2") && html.includes("max 1 week") && html.includes("max 1 month"));
  cek("tf: sp_tf dipakai", html.includes("sp_tf"));
  cek("tf: chip sisa ada", html.includes("sisaChip") || html.includes("SISA"));
  cek("tf: banner belum terkalibrasi", html.includes("belum terkalibrasi"));
  cek("ekspor: BOM + kolom TF", html.includes("\\uFEFF") && html.includes("skor_tf") && html.includes("aksi_tf"));
  cek("ekspor: semua data tanpa filter", html.includes("var rows = S.data;") && !html.includes("S._tampil"));
}

// 23) thowilz di halaman default exe
{
  cek("thowilz: SP.twBadge Lolos", SP.twBadge("Lolos").indexOf("a-beli") >= 0);
  cek("thowilz: SP.twBadge Kill", SP.twBadge("Kill").indexOf("a-hindar") >= 0);
  cek("thowilz: SP.twBadge kosong", SP.twBadge("-") === "—" && SP.twBadge("") === "—" && SP.twBadge(null) === "—");
  cek("thowilz: SP.twNum", SP.twNum(null) === "—" && SP.twNum("") === "—" && SP.twNum(0) === "—" && SP.twNum(7.22, 1) !== "—");
  cek("thowilz: marker kolom di HTML", html.indexOf("thowilz") >= 0 && html.indexOf("Kualitas Kas") >= 0);
  cek("thowilz: drawer panel di HTML", html.indexOf("Kualitas Kas Thowilz") >= 0 && html.indexOf("Checklist Thowilz") >= 0);
}

// 24) petunjuk mode pasar (scan tanpa data kas)
{
  cek("scan: banner mode pasar ada", html.indexOf("tanpa data kas") >= 0 && html.indexOf("laporan segar") >= 0);
}

// 25) banner ciut default + lengkapi kas top-40
{
  cek("banner: default ciut", html.indexOf('st !== "full"') >= 0 && html.indexOf('id="hzwMin"') >= 0);
  cek("lengkapi: tombol + endpoint", html.indexOf('id="btnLengkapi"') >= 0 && html.indexOf("/api/lengkapi") >= 0);
}

console.log(gagal ? ("\n" + gagal + " uji GAGAL") : "\nSemua uji lulus");
process.exit(gagal ? 1 : 0);
