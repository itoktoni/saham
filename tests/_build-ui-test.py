# Regenerasi _ui.js: stub DOM + <script> dari HTML + ekor tes.
# Pakai: python _build-ui-test.py
import re, io, os

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, "..", "web", "screener-saham-indonesia.html")
UI   = os.path.join(HERE, "_ui.js")

html = io.open(HTML, encoding="utf-8").read()
ui   = io.open(UI, encoding="utf-8").read()

# 1) ekor tes = dari 'let gagal=0;' sampai akhir
m = re.search(r"let gagal=0;", ui)
if not m:
    raise SystemExit("GAGAL: penanda 'let gagal=0;' tidak ditemukan di _ui.js")
tail = ui[m.start():]

# 2) prefiks stub = sampai (termasuk) baris "use strict";
m2 = re.search(r'^"use strict";\s*$', ui, re.M)
if not m2:
    raise SystemExit("GAGAL: penanda '\"use strict\";' tidak ditemukan di _ui.js")
prefix = ui[:m2.end()] + "\n"

# 3) skrip dari HTML = isi <script> ... </script> terakhir
blocks = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, re.S)
if not blocks:
    raise SystemExit("GAGAL: tidak ada blok <script> di HTML")
script = max(blocks, key=len)
if "function cek(" in script:
    raise SystemExit("GAGAL: blok skrip HTML ikut memuat kode tes")

io.open(UI, "w", encoding="utf-8", newline="\n").write(prefix + script.strip() + "\n\n" + tail)
print("OK  _ui.js diperbarui dari %s" % os.path.basename(HTML))
print("    skrip HTML : %d char" % len(script))
print("    ekor tes   : %d char" % len(tail))
