# MEMORY.md — Proyek D:\saham

Catatan jangka panjang proyek analisis/screener saham Indonesia.

## Konvensi proyek

- **Bahasa keluaran:** Bahasa Indonesia (dokumen sumber, UI tool, dan catatan memori memakai Bahasa Indonesia).
- **Gaya deliverable:** tool interaktif berupa **satu file HTML mandiri** (tanpa CDN/dependensi eksternal) agar bisa dibuka langsung dan jalan offline. Simpan di root `D:\saham\`.
- **Sumber kebenaran metodologi:** tiga dokumen di root proyek —
  - `panduan-software-screening-valuasi-saham.md` (screening, 5 rumus valuasi, MOS, matriks keputusan)
  - `panduan-investasi-hendriko-gani.md` (cycle investing top-down, makro, manajemen risiko)
  - `pola-swing-antitesis-bandar.md` (bandarmology, spring, TP/SL, position sizing)
- **Prinsip penggabungan:** satu alur 7 langkah (Makro → Data → Screening → Valuasi → MOS → Swing → Keputusan). Jangan pecah menjadi tool terpisah.
- **Konvensi warna:** naik = merah, turun = hijau.
- **Data contoh wajib diberi label ilustrasi** dan disertai peringatan agar diganti data riil sebelum dipakai mengambil keputusan.

## Artefak utama

- `screener-saham-indonesia.html` — screener + valuasi + swing, alur 7 langkah, dibuat 2026-09-20. Satu file, tanpa dependensi, offline. Dilengkapi **stepper 8 bagian yang bisa dilipat** dan **panel panduan per langkah** (tabel sumber data + cara membaca indikator).
- `fetch-data-idx.py` — penarik data otomatis (IDX + Yahoo Finance), hanya pustaka standar Python. Menulis CSV/JSON yang langsung bisa diimpor screener. Mode `--pasar` mengambil regime makro → `pasar.json`; mode `--laporan` / `--laporan-saja` mengambil laporan keuangan resmi IDX.
- `cache-laporan/` — cache berkas laporan IDX per emiten per tahun (`.xlsx`, atau `.inline.zip` bila xlsx-nya rusak). Aman dihapus; akan diunduh ulang.
- `laporan-idx.json` — keluaran mode `--laporan-saja`: angka laporan per emiten per tahun.
- `pasar.json` — regime pasar otomatis: IHSG (MA50/MA200, jarak puncak, return 1/3/6 bulan) → saran kuadran; likuiditas IDX (nilai transaksi harian vs rata-rata) → longgar/netral/ketat; agregasi kekuatan sektor.
- `idx-profil.json` — cache profil 962 emiten IDX (umur 7 hari).
- `contoh-data-idx.csv` / `.json` — contoh keluaran nyata untuk mencoba tombol impor.
- `contoh-stockbit-iata.json` — contoh JSON hasil parsing Key Stats (termasuk artefak `sector: "ID flag"` yang sengaja dibiarkan sebagai bahan uji).
- `_build-ui-test.py` + `_ui.js` — harness uji UI tanpa peramban. **Selalu jalankan `python _build-ui-test.py` sebelum `node _ui.js`**, karena `_ui.js` adalah rakitan (stub DOM + blok `<script>` dari HTML + ekor tes). Jangan pernah menyunting salinan skrip di `_ui.js` secara langsung — uji akan lulus terhadap HTML yang sudah basi.

## Regime makro otomatis (Langkah 1) — apa yang otomatis dan apa yang tidak

| Indikator | Jenis | Sumber |
|---|---|---|
| Kuadran siklus | **Otomatis** | riwayat IHSG 1 tahun (`^JKSE`, Yahoo) |
| Tren likuiditas | **Otomatis** | `GetIndexSummary` baris `COMPOSITE` kolom `Value`, vs rata-rata 30 hari |
| Kekuatan sektor | **Semi-otomatis** | agregasi return 6 bulan emiten yang sudah ditarik |
| BI Rate | **Manual** | situs BI |
| Toleransi risiko | **Manual** | selera pengguna |

**Aturan kuadran** (urut, berhenti di yang pertama cocok): `r3<−10%` & di bawah MA50 → **Bust**; `r3<0` & di bawah MA50 → **Slowdown**; `r3>0` & jarak puncak >−8% → **Overheat**; `r3>0` & jarak puncak ≤−8% → **Recovery**; sisanya **Slowdown**.

**Ambang likuiditas:** rasio ≥1,15 → Longgar · ≤0,85 → Ketat · selain itu Netral.
**Target MOS per kuadran:** Recovery 25% · Overheat 30% · Slowdown 35% · Bust 40% (tak diketahui → 30%).

**Indeks sektor IDX tidak ada di sumber gratis** — Yahoo hanya memberi 1 titik data untuk `IDXENERGY.JK`, dan `GetIndexSummary` hanya memuat 10 indeks lebar tanpa indeks sektor. Karena itu kekuatan sektor **dihitung dari agregasi emiten** dan UI wajib menyebut *"bukan indeks sektor resmi"*.


## Sumber data: utamakan laporan resmi IDX, tempel hanya untuk yang tidak ada

**Laporan keuangan IDX dapat ditarik OTOMATIS tanpa login** — ini penemuan terpenting proyek. `fetch-data-idx.py --laporan` mengambil laba, ekuitas, liabilitas, arus kas, kas, dan riwayat laba 10 tahun yang **asli**, lalu menimpa nilai turunan Yahoo.

| Jalur | Kelengkapan | Catatan |
|---|---|---|
| `--laporan` (laporan resmi IDX) | **Lengkap & otomatis** | Neraca, laba rugi, arus kas, 10 tahun, sektor IDX-IC resmi. Tanpa login. |
| Tempel JSON Key Stats | **Paling lengkap** | F-Score, Altman Z, rasio siap pakai — tidak ada di laporan IDX, wajib salin-tempel manual. |
| `fetch-data-idx.py` tanpa `--laporan` | Sedang | Otomatis, tapi ekuitas/FCF masih turunan Yahoo. |
| Import CSV/JSON | Seadanya | Fleksibel untuk data sendiri. |
| Data contoh | Ilustrasi | Hanya untuk mencoba alur. |

**Jangan pernah** membuat scraper otomatis untuk sumber di balik login (melanggar ToS, rapuh, dan berisiko akun diblokir). Pola yang dipakai proyek SahamLens — pengguna menyalin sendiri, alat hanya membaca — adalah pola yang benar dan sudah diadopsi di sini. **Login IDX tidak diperlukan sama sekali** — sudah diverifikasi; jangan minta kredensial pengguna.

**Sumber yang sudah dievaluasi:**
- `IDNCraft/SahamLens` — React/TS, parser salin-tempel, tanpa jaringan. Referensi pola.
- `NeaByteLab/IDX-UI` — Deno + SQLite, API **localhost saja**. Berguna sebagai referensi endpoint; `bid-offer` & `foreign` adalah kandidat jawaban untuk `s_topbuyer`.
- `Yuukinaesa/Saham` — Streamlit + yfinance. Berguna untuk kalkulator ARA/ARB (fraksi harga IDX) dan struktur biaya platform (IPOT 0,19/0,29 · Stockbit 0,15/0,25 · BNI Bions 0,17/0,27).

## Laporan keuangan IDX otomatis — hal yang WAJIB diketahui

- **Endpoint:** `GET /primary/ListedCompany/GetFinancialReport?kodeEmiten=&year=&periode=audit&pageSize=100&reportType=rdf`. Kuncinya **`reportType=rdf`** dan **`periode=audit`** (juga `TW1`/`TW2`/`TW3`). Memakai `rda` mengembalikan `ResultCount: 0`.
- **Cloudflare:** menolak `urllib` dengan HTTP 403 karena sidik jari TLS, tetapi **menerima `curl`**. Wajib mengunjungi halaman utama dulu untuk cookie `__cf_bm` (fungsi `pemanasan()`). Jangan hapus transport curl. Beri jeda — menembak bertubi-tubi memicu halaman tantangan.
- **Kode sheet BERBEDA per template industri** (bank `4220000`/`4322000`/`4510000`, infrastruktur `3210000`/`3312000`/`3510000`). **Selalu kenali sheet dari judulnya** ("Statement of financial position" / "profit or loss" / "cash flows"). Menghafal kode akan rusak pada industri lain.
- **Label "Pembulatan" IDX tidak dapat dipercaya antar tahun.** Nyata: BBCA 2022 & 2024 dalam jutaan, **2023 dalam rupiah penuh**, label ketiganya sama "Jutaan / In Million". Penanganannya **dua tahap dan urutannya penting**: (1) percayai label tiap tahun, (2) baru deteksi penyimpangan dari hasil berskala — bandingkan total aset dengan acuan (kelas besaran terbanyak, lalu median di dalamnya), geser tahun yang menyimpang ≥ pangkat 1000. **Jangan** memakai kelas besaran data *mentah* sebagai acuan: nilainya bisa jatuh tepat di batas pembulatan (`round(3,5)`=4 vs 3) dan merusak tahun yang sebenarnya benar (kasus ANTM 2020).
- **Pakai laba INDUK, bukan laba total.** `Laba (rugi) yang dapat diatribusikan ke entitas induk` adalah satu-satunya yang konsisten dengan EPS. `Jumlah laba (rugi)` sudah termasuk kepentingan non-pengendali (TLKM 2024: 30.743 vs 23.649 miliar).
- **Sebagian `.xlsx` rusak di sisi IDX** (ANTM 2024: HTTP 200 + content-type xlsx, isinya 165 byte kata "Administrator"). Karena itu `_xlsx_sah()` memeriksa **isi** berkas (harus diawali `PK`), bukan ukuran. Cadangannya `inlineXBRL.zip` (HTML + atribut `scale` yang justru memberi skala pasti).
- **Satuan `hist_laba` = MILIAR rupiah** (sesuai `chartLaba` di screener).
- **Kontrak CSV = 43 kolom.** 31 inti + 12 tambahan, tambahan **hanya di akhir**. Python dan HTML harus sinkron; kalau tidak, kolom seperti `hist_laba` terbuang tanpa peringatan.


## Aturan data (WAJIB dipatuhi saat menulis/mengubah importer atau fetcher)

- **Kontrak CSV ditentukan `CSV_HEADER` di HTML.** 31 kolom pertama adalah kontrak inti yang harus disinkronkan dengan `fetch-data-idx.py`; kolom tambahan hanya boleh **ditambahkan di akhir** agar berkas lama tetap bisa diimpor.
- **Jangan pernah menebak format angka yang ambigu.** Titik tunggal dianggap desimal (format berkas mesin); titik baru dianggap pemisah ribuan bila polanya jelas bergrup (`1.234.567`) atau ada koma.
- **Untuk emiten IDX, utamakan jalur tempel** bila butuh FCF, ekuitas asli, dan riwayat laba — Yahoo tidak menyediakannya.
- **Angka:** titik = desimal (`0.1924`) untuk berkas mesin; koma = desimal untuk gaya Indonesia (`1.234,56`). Pakai `toNum()`, jangan `replace(/\./g,"")` mentah-mentah.
- **BOM:** skrip Python menulis `utf-8-sig`; importer wajib membuang BOM atau seluruh baris terbuang.
- **Sektor:** pakai `normSektor()` / `normalisasi_sektor()`. IDX-IC memakai "Barang Konsumen Primer/Non-Primer".
- **Jangan simpan hasil pemetaan ke cache** — simpan mentah, petakan saat dibaca.
- **Auto-fetch tidak bisa jalan di dalam browser** (CORS + Cloudflare); selalu lewat skrip lokal.

## Utang teknis yang diketahui

- `s_topbuyer` (konsentrasi top buyer) tidak tersedia di sumber gratis — harus diisi manual dari broker summary.
- F-Score, Altman Z, dan sebagian rasio siap pakai hanya ada di jalur tempel JSON Key Stats.
- Sebagian emiten/laporan lama tidak punya lampiran `.xlsx` maupun `inlineXBRL.zip`; `instance.zip` (XBRL mentah) belum diparse sebagai cadangan terakhir.
- Data emiten berkapitalisasi kecil di Yahoo sering salah; laporan IDX sudah menutup sebagian, sisanya belum dicari sumber alternatif.
- Belum memodelkan fraksi harga, auto-rejection, pajak, dan biaya transaksi IDX.
- Belum ada backtest skor.

## Pelajaran yang harus diingat (lanjutan)

- **Verifikasi kontrak data itu wajib, bukan formalitas.** Menguji impor CSV 43 kolom "yang seharusnya jalan" justru memunculkan 3 bug nyata. Jangan pernah menyatakan sebuah kontrak aman tanpa menjalankan berkas aslinya lewat pembacanya.
- **Jangan biarkan satu kolom turunan basi saat sumber aslinya masuk.** `gabung_laporan()` sudah menimpa ekuitas/laba/eps/fcf/kas/utang/der/sektor/hist_laba, tetapi lupa `eps_trend` -- dan justru kolom itu yang paling berbobot. Setiap kali menambahkan sumber data otoritatif, periksa **semua** kolom turunan yang bisa dihitung ulang darinya.
- **Pemisah CSV harus dipilih sekali dari baris judul, bukan dicoba dua-duanya.** Menganggap `,` dan `;` sama-sama pemisah membuat satu titik koma di kolom bebas menggeser seluruh kolom sesudahnya tanpa peringatan. Dan `csv.QUOTE_MINIMAL` di Python hanya mengutip koma, **bukan** titik koma -- jadi penulis CSV di Python harus dikutip tangan agar kembar dengan `csvLine()` di JS.
- **Satu konsep, satu ambang.** Ambang likuiditas sempat berbeda antara filter (5e9) dan tier peringkat (10e9), sehingga emiten bisa lolos filter tetapi tetap dihukum. Cari ambang yang terduplikasi setiap kali menambah filter.
- **Skor tier vs peringkat tidak boleh dicampur dalam satu penjumlahan tanpa disadari.** 1/200/1000 jauh melebihi jumlah peringkat (maks 16), jadi tier yang menentukan urutan, bukan peringkat. Kalau memang itu maksudnya, tulis terus terang di UI; kalau tidak, samakan skalanya.
- **Tren laba dari riwayat: regresi linear pada nilai yang dinormalkan** terhadap laba tipikal, bukan regresi log-linear (log tidak terdefinisi untuk laba <= 0). Ambang 5% dari laba tipikal per tahun, minimal 4 titik data.

## Screener Praktis (2026-10-01) — UI screener-first + data KSEI

Konteks: pengguna menilai `screener-saham-indonesia.html` (alur 7 langkah) terlalu rumit. Dibuat tool praktis terpisah: **`screener-praktis.html`** — screener dulu, klik saham → langkah demi langkah. Alat lama tetap ada sebagai referensi "advanced".

### Artefak baru
- `screener-praktis.html` — satu file, offline, tanpa dependensi. Modul JS `SP` (parseCSV, build, detectFase, valuasi, skor) sengaja diekspos global agar bisa diuji tanpa browser.
- `fetch-ksei.py` — penarik kepemilikan KSEI → `ksei.json` (1000+ emiten). Mode: unduh 2 bulan terakhir untuk delta.
- `_test-praktis.js` — uji smoke mesin (jalankan `node _test-praktis.js`): cek `node --check` blok script, parse CSV, fase, skor, valuasi.
- `PRODUCT.md` / `DESIGN.md` — artefak Impeccable (konteks produk + sistem visual).
- `cache-ksei/` — cache zip KSEI (aman dihapus). `ksei.json` — keluaran kepemilikan.

### Sumber data: apa yang jalan & apa yang TERBLOKIR
- **KSEI JALAN (gratis, tanpa login).** `https://web.ksei.co.id/archive_download/holding_composition` memuat tautan `/Download/BalanceposEfekYYYYMMDD.zip` (tanggal = hari bursa terakhir bulan). Isi: `BalanceposYYYYMMDD.txt`, **pipe-delimited**, 25 kolom: `Date|Code|Type|Sec. Num|Price|` lalu 9 tipe **Local** (IS,CP,PF,IB,ID,MF,SC,FD,OT)+Total, lalu 9 tipe **Foreign**+Total. `Local ID` = ritel domestik. **PENTING:** filter `?Year=YYYY` diabaikan (selalu balik 2026); tetapi URL bersifat deterministik → bulan lama diambil dengan menebak tanggal hari bursa terakhir (mundur bila 404). `seri_bulan` default 24. Tiap baris juga menyimpan `asing_saham`/`lokal_saham`; dari seri (lembar asing bulanan × `harga_ksei` akhir bulan) dihitung **`asing_avg_price` = rata-rata harga PEMBELIAN asing** (hanya bulan saat lembar asing naik) + `asing_net_saham`. Format stabil; urllib/curl sama-sama berhasil.
- **TRADINGVIEW JALAN (gratis, tanpa kunci, tanpa login) — sumber terbaik untuk seluruh pasar.** `POST https://scanner.tradingview.com/indonesia/scan` dengan header `Content-Type: application/json`, `Origin/Referer: https://www.tradingview.com`. Body: `{"filter":[{"left":"type","operation":"equal","right":"stock"}],"options":{"lang":"en"},"columns":[...],"range":[0,1200]}`. Mengembalikan **~845–889 saham IDX sekaligus** dalam satu permintaan: `close, volume, change, relative_volume_10d_calc, market_cap_basic, price_earnings_ttm, price_book_ratio, return_on_equity, debt_to_equity, earnings_per_share_basic_ttm, sector, RSI, SMA50, SMA200, High.1M, Low.1M`, `Perf.1M` (return 1 bulan persen — dipakai sebagai `ret20`/momrev skor), `beta_1_year`, `net_margin`, dll. **`High.1M`/`Low.1M` setara resistance/support rentang 20 hari** (ANTM 3370/3020 identik dengan hitung_swing Yahoo) — jadi bisa mengisi logika fase yang sama. Kolom tak valid membuat permintaan error; uji dulu. Jangan andalkan untuk aliran asing/broker summary (tidak ada).
- **Sumber lain yang diuji (2026-10-01):** `stockanalysis.com` (200, fundamental per saham), `idnfinancials.com` (200), `pasardana.id` (200, halaman JS — aliran asing tak terbaca teks), `bigalpha.id` (200), `rti.co.id` (200 halaman; data di balik login/aplikasi), `cnbcindonesia.com/market` (200 berita). **GAGAL/kosong:** stooq tak punya IDX (404), investing.com 403 Cloudflare, duniainvestasi/sahamleader tidak terhubung, sahamidx redirect, Wayback tak mengarsip API IDX. **Kesimpulan: tidak ada sumber gratis yang andal untuk aliran asing/broker summary harian.** Proxy gratis: KSEI bulanan + TradingView harian (harga/volume/fundamental).
- **IDX LANGSUNG TERBLOKIR dari mesin ini (2026-10-01).** `GetStockSummary`/`GetIndexSummary`/bahkan homepage `www.idx.co.id` membalas **managed challenge Cloudflare interaktif** (HTTP 403 "Just a moment...") untuk: curl (system & Git, dua-duanya Schannel), urllib, **curl_cffi 0.16.3 (impersonate chrome)**, **Chromium & Edge asli via Playwright (headed & headless)**, r.jina.ai, allorigins. Challenge tidak auto-selesai (title "Tunggu sebentar..."). Artinya aliran asing HARIAN dan broker summary per saham **tidak bisa diotomatiskan** sekarang. `playwright` + `curl_cffi` sudah terpasang (bisa dicoba lagi nanti bila blokir hilang), tetapi jangan janjikan jalan sebelum diuji.
- Kesimpulan: MVP memakai **KSEI (bulanan) + Yahoo (harian)**. Adapter IDX harian disiapkan konsepnya tapi tidak dipakai.

### Logika fase bandar (`detectFase` di screener-praktis.html)
`pos` = posisi harga dalam rentang 20 hari dari `s_springlow`..`s_resistance`. `dA`/`dI` = delta kepemilikan asing/institusi 1 bulan (pp) dari KSEI.
Urut: **Spring** bila `s_spring=1`; **Distribusi** bila `pos>=0.72` & `vol>=1.3` & (dA<0 atau dI<0); **Markup** bila `s_closeabove` & `pos>=0.5` & (vol>=1.1 atau dA+dI>=1.0); **Akumulasi** bila `pos<=0.65` & (dA>0 atau dI>0) & vol<1.2 (atau sideways & aliran naik); sisanya **Netral**.

### Skor 0–100 (DICALIBRASI ULANG 2026-10-02, Fase 0+1 selesai)
**15% Nilai + 30% Kualitas + 15% Timing + 10% Aliran + 30% Momrev.** Detail:
- **Nilai**: `clamp((mos+20)/70*100, 0, mos>50 ? 65 : 100)` (MOS dicap di 65 skor bila MOS>50%) × `clamp(1 − drawdown/0.6, 0.35, 1)` (drawdown = 1 − harga/high_52; makin jatuh makin diredam — MOS dari saham yang jatuh dinilai skeptis), lalu digabung 60/40 dengan `mosBandar = (asing_avg − harga)/asing_avg*100` bila ada rata2 beli asing.
- **Momrev**: `clamp(50 − ret20*4, 0, 100)`; netral 50 bila `ret20` kosong. Sumber `ret20`: jalur pasar penuh = kolom TV **`Perf.1M`** (persen, ditambahkan ke `TV_COLS`); jalur watchlist = `(close[-1]/close[-22] − 1)*100` dari chart Yahoo di `ambil_emiten`.
- **Aksi** `aksi(fase,skor,val,pos,mosBandar)`: **Distribusi→Hindari**; **MOS≤0→Pantau**; **Akumulasi/Spring→Beli bila skor≥70 dan (mosBandar==null atau mosBandar>−10)** (gerband: tahan bila asing sudah untung ≥10% = `asing_pnl≥10`); **Markup→Beli hanya bila markup AWAL (pos<0.55 dan skor≥70)**; Netral→Pantau bila skor≥55. `pos` = posisi harga dalam rentang `s_springlow`..`s_resistance`.
- **Bukti (jangan diubah tanpa re-run diag):** `python scripts/diag-skor.py --top 80 --step 3 --no-report` lalu `node tests/_diag-skor.js [fwd20|fwd60]`. Window 2 tahun (5y chart), hold-out ekor 7 bulan (crash Mei'26 + recovery). fwd60 test: skor lama lift +2,5pp (38,1% hijau) → **skor baru +13,9pp (49,5% hijau, base 35,6%, rata2 +1,9% vs −3,6%)**, Beli cuma 25,8% baris. fwd20: skor lama −1,9pp → baru +2,5pp (**horizon 1 bulan tak bisa dijanjikan hijau**). Gerbang IHSG & komponen excess vs IHSG = TRAP (lift negatif). Mirror komponen di `tests/_diag-skor.js` harus == `SP.skor` (assert per baris).
- **BUG IHSG yang pernah diam-diam merusak:** `ihsg_close_le` membandingkan tanggal IHSG tanpa-dash vs kunci ber-dash (`YYYY-MM-DD`) → semua kunci 2026 jatuh ke close akhir-2025 → `ihsg_r1` −11..−35% seragam. Kini kunci dinormalisasi di dalam fungsi + validasi keras (level 1000–20000, ≥400 tanggal, |r1|>30% → RuntimeError) + cache `data/diag-ihsg.json`.

### Aturan kerja tool praktis
- **Jangan buat `_build-ui-praktis` ala `_ui.js`**; uji lewat `_test-praktis.js` yang mengekstrak modul `SP` dari HTML dan menjalankannya di Node.
- Semua `id` yang dipakai `$("...")` harus ada di HTML (dicek rutin).
- Setelah mengubah UI, jalankan detektor Impeccable: `C:\Users\itokt\.config\opencode\skills\impeccable\scripts\impeccable.cmd detect --json screener-praktis.html` (target: `[]`).
- Impeccable kini v4.3.1; perintah `context`/`detect` lewat `impeccable.cmd` (bukan `detect.mjs` lagi).
- **Atribut `hidden` bisa "mati" bila elemen punya `display` sendiri.** `.macro` dan `.alert` memakai `display:flex`, yang mengalahkan `[hidden]` bawaan peramban → elemen tetap terlihat walau JS menandai `hidden`. Solusi: aturan global `[hidden]{display:none!important}`. Ingat ini setiap menambah elemen yang di-hide/tampilkan lewat atribut `hidden`.
- **Artefak aplikasi (klik-dua-kali, tanpa perintah):** `app-screener.py` (server lokal stdlib di 127.0.0.1:8765 + endpoint `/api/status`, `/api/download` [watchlist Yahoo+KSEI], `/api/scan` [seluruh pasar TradingView+KSEI]; memuat `fetch-data-idx.py` & `fetch-ksei.py` sebagai modul), `Jalankan Screener.vbs` (peluncur tanpa jendela; coba `pythonw` lalu `python`), `Matikan Screener.vbs` (taskkill via `screener.pid`). Server membuka peramban sendiri; `SCREENER_NO_BROWSER=1` untuk menonaktifkan (dipakai saat uji). Log ke `logs/screener-app.log`. Cache di memori: KSEI 6 jam, emiten Yahoo 30 menit, TradingView 10 menit.
- **Struktur folder (2026-10-01):** root hanya `Screener Saham.exe`, `Jalankan Screener.vbs`, `Matikan Screener.vbs`, `Install.bat`, `Uninstall.bat`, `README.md`. Isi: `app/` (app-screener.py), `web/` (screener-praktis.html + screener-saham-indonesia.html), `scripts/` (fetch-data-idx.py, fetch-ksei.py), `data/` (ksei.json, data-idx.csv/json, pasar.json, idx-profil.json, daftar-saham.txt, cache-ksei/, cache-laporan/), `docs/`, `contoh/`, `tests/`, `logs/`. `app-screener.py` memakai ROOT+RES: mode sumber `ROOT`=induk `app/`; mode `.exe` (`sys.frozen`) `ROOT`=folder exe dan sumber daya di `sys._MEIPASS`. Lalu `os.chdir(data/)`. PID di root (`screener.pid`). Skrip `scripts/*.py` juga `chdir` ke `../data` bila dijalankan langsung.
- **Exe portable:** dibangun dengan PyInstaller onefile noconsole: `python -m PyInstaller --onefile --noconsole --name "Screener Saham" --add-data "D:\saham\web;web" --add-data "D:\saham\scripts;scripts" D:\saham\app\app-screener.py`. **WAJIB** ada impor eksplisit (blok `# noqa`) modul yang dipakai skrip runtime (`xml.etree.ElementTree`, `argparse`, `http.cookiejar`, `io`, `math`, `re`, `shutil`, `struct`, `subprocess`, `urllib.error`, `zipfile`, `collections`) di app-screener.py — kalau tidak, muncul `No module named 'xml'`. Jangan hapus blok itu. Hasil ditempel di root sebagai `Screener Saham.exe`.
- **Tombol UI:** **Download Data** (watchlist, Yahoo+KSEI, fitur swing akurat) dan **Scan Seluruh Pasar** (TradingView, ~845 saham, fase diperkirakan dari High.1M/Low.1M + volume relatif). Kolom tabel: `Kode, Nama, Harga, Fase, Asing %, ΔAsing 1m, Rata2 Asing, Upside, MOS %, Skor, Aksi`. **Rata2 Asing** = kseki.`asing_avg_price` (rata-rata harga beli asing 24 bln); **Upside** = (nilai intrinsik − harga)/harga. Drawer menambah: Net beli asing 24bln, Posisi asing (untung/rugi = harga/asing_avg−1), Ruang ke puncak 52mg (`high_52` dari TradingView `price_52_week_high`, atau max high 1y Yahoo). Untuk pasar penuh, `s_spring` & `s_freqspike` = 0 (butuh riwayat harga).
- **Konfigurasi unduhan (2026-10-01):** sumber kebenaran = `data/config.json` `{daftar_saham:[...], bulan_ksei:24}`. Endpoint `GET/POST /api/config` (POST menulis config.json **dan** daftar-saham.txt, dedup kode, toleran BOM via `utf-8-sig`, membatalkan cache KSEI bila bulan berubah). Panel **Pengaturan unduhan** di UI (details tertutup default). **Download Data** = daftar pantau (default 10 emiten) via Yahoo+KSEI; **Scan Seluruh Pasar** = seluruh IDX (~845) via TradingView. `bulan_ksei` 2–48.
- **PELAJARAN: `.exe` onefile PyInstaller menjalankan PROSES ANAK.** `Start-Process` mengembalikan PID bootloader; `Stop-Process -Id` itu TIDAK mematikan aplikasinya → port 8765 tetap dipakai instance lama dan uji berikutnya menembak server basi. Selalu `Get-Process -Name "Screener Saham" | Stop-Process -Force`.
- **Alur pemakaian (yang diinginkan pengguna):** klik dua kali **`Jalankan Screener.vbs`** → peramban terbuka → klik **Download Data** → data KSEI + Yahoo diambil otomatis. Tidak ada perintah yang diketik. Tombol **Impor Berkas** tetap ada sebagai cadangan bila berkas sudah dimiliki; **Muat Contoh** untuk pratinjau offline.
- **Fitur horizon & kontrak (2026-10-02):** banner `#horizonWarn` (angka dari `SP.KALIBRASI` — SATU sumber untuk banner/help/tiket; jangan hardcode di tempat lain), select `#dwHorizon` di drawer Step 4 (≤1 bulan → sorot TP/SL + peringatan, tersimpan `sp_horizon`), kolom **Umur Fase** (`sp_umur`: umur = sejak fase pertama terpantau, reset saat fase berubah, "baru" bila belum pernah terlihat) & **Kontrak** (`sp_kontrak`: dicatat manual dari drawer bila aksi Beli, masa +84 hari kalender = 60 hari bursa, chip `H+n`, merah `KDL`, tombol Tutup/Rol). Uji: `node tests/_test-praktis.js` (asesi SP) + `python tests/_smoke-ui.py` (Playwright file://, 28 pemeriksaan DOM — th memakai `text-transform:uppercase`, jadi bandingkan inner_text case-insensitive).
- Jalur manual (cadangan): `python fetch-ksei.py` → `python fetch-data-idx.py --file daftar-saham.txt --laporan` → buka HTML → Impor Berkas (`data-idx.csv` + `ksei.json`).
