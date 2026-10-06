const fs = require("fs");
const vm = require("vm");
const html = fs.readFileSync("web/screener-praktis.html", "utf8");
const src = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1];
function elStub() {
  return new Proxy({}, {
    get: (t, p) => {
      if (p === "style") return {};
      if (p === "classList") return { add() {}, remove() {}, toggle() {} };
      if (p === "tHead") return elStub();
      if (p === "tBodies") return [elStub()];
      return (...a) => elStub();
    },
    set: () => true
  });
}
const store = {};
const sandbox = {
  console,
  location: { protocol: "http:" },
  localStorage: {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: (k) => { delete store[k]; }
  },
  document: {
    getElementById: () => elStub(),
    createElement: () => elStub(),
    querySelectorAll: () => []
  },
  fetch: () => new Promise(() => {}),
  Blob: function () {},
  URL: { createObjectURL: () => "" }
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(src + "\n;globalThis.__SP = SP;", sandbox, { timeout: 10000 });
const SP = sandbox.__SP;
function entryStreak() {
  return { acc: {
    top_buyers: [{ broker: "CC", nval: 500 }],
    top_sellers: [{ broker: "XX", nval: 100 }],
    series: { CC: [[1], [2], [-1], [3], [4]] }
  } };
}
console.log("streak:", SP.streakBeli(entryStreak()) === true ? "OK" : "FAIL");
console.log("noentry:", SP.streakBeli(null) === false ? "OK" : "FAIL");
console.log("dominan:", SP.dominanJual({ acc: {
  top_buyers: [{ broker: "A", nval: 100 }],
  top_sellers: [{ broker: "B", nval: 500 }]
} }) === true ? "OK" : "FAIL");
const r = { s_springlow: 100, s_resistance: 200, harga: 190,
  s_vol_ratio: 2.0, s_spring: 0, s_sideways: 0, s_closeabove: 1 };
const k = { dksei_asing_1m: -1.0, dksei_institusi_1m: -0.5 };
console.log("fase-streak:", SP.detectFase(r, k, entryStreak()) === "Markup" ? "OK" : "FAIL");
console.log("fase-noscope:", SP.detectFase(r, k, null) === "Distribusi" ? "OK" : "FAIL");
const rRun = { s_springlow: 100, s_resistance: 200, harga: 190,
  s_vol_ratio: 2.0, s_spring: 0, s_sideways: 0, s_closeabove: 1,
  high_52: 200, ret20: 25, laba: 100000000000, der: 0.5, eps_trend: "fluktuatif",
  eps: 100, ekuitas: 1000000000000, saham: 1000000000, cagr: 10, nilai_harian: 0 };
const valMid = { mos: 10, roe: 10, intrinsic: 200 };
const built = SP.build([Object.assign({ kode: "TST", nama: "T", sektor: "S" }, rRun)],
  { TST: { dksei_asing_1m: -1.0, dksei_institusi_1m: -0.5 } }, {}, { TST: entryStreak() });
console.log("build-markup:", built[0].fase === "Markup" ? "OK" : "FAIL:" + built[0].fase);
const sc = SP.skorTF(rRun, {}, "Markup", valMid, "bulan", true);
console.log("smom-lunak:", sc === 49 ? "OK-nilai-" + sc : "FAIL:" + sc);
const rLiquid = Object.assign({}, rRun, { nilai_harian: 1000000000 });
const rBig = Object.assign({}, rRun, { nilai_harian: 50000000000 });
const scLiq = SP.skorTF(rLiquid, {}, "Netral", valMid, "bulan");
const scBig = SP.skorTF(rBig, {}, "Netral", valMid, "bulan");
console.log("bonus-liquid:", scLiq > scBig ? "OK" : "FAIL:" + scLiq + "vs" + scBig);
console.log("aksi-markup-beli:", SP.aksiTF("Markup", 65, { mos: 10 }, 0.8, null, "bulan", {}) === "Beli" ? "OK" : "FAIL");
console.log("aksi-markup-mahal:", SP.aksiTF("Markup", 65, { mos: -20 }, 0.8, null, "bulan", {}) === "Pantau" ? "OK" : "FAIL");
console.log("aksi-markup-rendah:", SP.aksiTF("Markup", 55, { mos: 10 }, 0.8, null, "bulan", {}) === "Pantau" ? "OK" : "FAIL");
