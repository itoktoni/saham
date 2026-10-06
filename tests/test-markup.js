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
