# Smoke test UI screener-praktis (Playwright, file:// tanpa server).
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

URL = "file:///D:/saham/web/screener-praktis.html"
gagal = 0

def cek(nama, kondisi, info=""):
    global gagal
    if kondisi:
        print("  OK   " + nama)
    else:
        gagal += 1
        print("  GAGAL " + nama + (("  -> " + str(info)) if info else ""))

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto(URL)
    pg.evaluate("localStorage.clear()")
    pg.reload()
    pg.click("#btnContoh")
    pg.wait_for_function("document.querySelectorAll('#tbl tbody tr[data-kode]').length > 0")

    cek("data contoh termuat", True)
    cek("banner horizon tampil", pg.is_visible("#horizonWarn"))
    cek("banner berisi horizon 3 bulan", "3 bulan" in pg.inner_text("#horizonWarn"))
    pg.click("#hzwMin")
    cek("banner mengecil jadi pill", "min" in pg.evaluate("document.getElementById('horizonWarn').className"))
    pg.click("#hzwBuka")
    cek("pill bisa dibuka lagi", "min" not in pg.evaluate("document.getElementById('horizonWarn').className"))

    hdr = pg.inner_text("#tbl thead")
    cek("kolom Umur Fase ada", "umur fase" in hdr.lower(), hdr.replace("\n", " "))
    cek("kolom Kontrak ada", "kontrak" in hdr.lower(), hdr.replace("\n", " "))
    cek("baris awal umur 'baru'", "baru" in pg.inner_text("#tbl tbody"))

    cek("segmented timeframe tampil", pg.is_visible("#tfSeg"))
    cek("chip SISA max-hold tampil", "SISA" in pg.inner_text("#tbl tbody"))
    pg.click("#tbl tbody tr:first-child")
    pg.wait_for_selector(".drawer.on")
    cek("drawer terbuka + select timeframe ada", pg.is_visible("#dwHorizon"))
    cek("baris umur ada di drawer", "Umur fase" in pg.inner_text("#dwBody"))
    pg.select_option("#dwHorizon", "kilat")
    cek("peringatan belum-terkalibrasi muncul", pg.is_visible("#dwHorizonNote"))
    cek("TP diberi sorot .hz", "hz" in pg.evaluate("document.getElementById('dwTp').className"))
    cek("pilihan timeframe tersimpan", pg.evaluate("localStorage.getItem('sp_tf')") == "kilat")
    cek("banner tampil saat mode kilat", pg.is_visible("#horizonWarn"))
    pg.select_option("#dwHorizon", "bulan")
    cek("peringatan hilang saat bulanan", not pg.is_visible("#dwHorizonNote"))
    cek("sorot .hz dilepas", "hz" not in pg.evaluate("document.getElementById('dwTp').className"))

    ada_beli = pg.evaluate("!!document.querySelector('#tbl tbody .a-beli')")
    kode_beli = None
    if ada_beli:
        kode_beli = pg.evaluate("document.querySelector('#tbl tbody tr:has(.a-beli)').getAttribute('data-kode')")

    # injeksi tiket kedaluwarsa -> chip KDL + kartu kontrak di drawer
    pg.evaluate("localStorage.setItem('sp_kontrak', JSON.stringify({BBCA:{buka:'2026-01-01',kdl:'2026-04-01',strike:6225,tp:6600,sl:6070,skor:80}}))")
    pg.reload()
    pg.click("#btnContoh")
    pg.wait_for_function("document.querySelectorAll('#tbl tbody tr[data-kode]').length > 0")
    cek("chip KDL tampil untuk tiket lewat", "KDL" in pg.inner_text("#tbl tbody"))

    pg.click("tr[data-kode='BBCA']")
    pg.wait_for_selector(".drawer.on")
    isi = pg.inner_text("#dwBody")
    cek("kartu kontrak di drawer", "Kontrak 60 hari bursa" in isi)
    cek("odds pakai angka kalibrasi", "50,4%" in isi)
    cek("tombol tutup kontrak ada", pg.is_visible("#dwKtlTutup"))
    cek("rol hanya bila aksi Beli", not pg.is_visible("#dwKtlRol"))
    pg.click("#dwKtlTutup")
    pg.wait_for_timeout(250)
    cek("kartu kontrak hilang setelah ditutup", "belum ada" in pg.inner_text("#dwBody") and not pg.is_visible("#dwKtlTutup"))
    cek("chip KDL hilang dari tabel", "KDL" not in pg.inner_text("#tbl tbody"))

    if pg.is_visible("#dwClose"):
        pg.click("#dwClose")
        pg.wait_for_timeout(150)
    if ada_beli and kode_beli:
        pg.click("tr[data-kode='" + kode_beli + "']")
        pg.wait_for_selector(".drawer.on")
        cek("tombol catat kontrak muncul (" + kode_beli + ")", pg.is_visible("#dwKtlBuka"))
        if pg.is_visible("#dwKtlBuka"):
            pg.click("#dwKtlBuka")
            pg.wait_for_timeout(250)
            cek("chip H+0 setelah dicatat", "H+0" in pg.inner_text("#tbl tbody"))
            cek("kartu kontrak + tombol rol muncul", pg.is_visible("#dwKtlRol"))
    else:
        print("  INFO contoh tak punya aksi Beli â€” alur catat dilewati (alur inti sudah diuji via injeksi)")

    cek("sp_umur terisi", bool(pg.evaluate("localStorage.getItem('sp_umur')")))
    cek("sp_kontrak berisi tiket BBRI yang baru dicatat", "BBRI" in (pg.evaluate("localStorage.getItem('sp_kontrak')") or ""))

    b.close()

print(("\n" + str(gagal) + " uji GAGAL") if gagal else "\nSemua uji lulus")
sys.exit(1 if gagal else 0)




