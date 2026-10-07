const fs = require("fs");
const html = fs.readFileSync("web/screener-saham-indonesia.html", "utf8");
for (const k of ["ev_cfo", "ev_fcf", "cfo3", "sloan", "cash_badge"]) {
  if (!html.includes(k)) throw new Error("kolom hilang: " + k);
}
if (!html.includes("evcfo") && !html.includes("evCfo")) throw new Error("rank evcfo hilang");
for (const k of ["peg_cfo", "cfo_cagr", "gross_margin", "margin_stabil", "capex_inten", "klasifikasi", "thowilz"]) {
  if (!html.includes(k)) throw new Error("kolom hilang: " + k);
}
if (!html.includes("thowilz") && !html.includes("Thowilz")) throw new Error("panel Thowilz hilang");
console.log("cash-ui OK");
