# Spec: Fondasi Ingestion SahamScope (Sub-proyek 0 dari 4)

Tanggal: 2026-10-03 | Pendekatan: A (Python fetch + cache + endpoint) | Status: disetujui user
Program: (0) fondasi ini → (1) Combo meter → (2) Exit-liquidity alarm → (3) Bounty board.
File: `scripts/fetch-sahamscope.py` (baru), `app/app-screener.py` (panggil + endpoint),
  `web/screener-praktis.html` (badge + `S.scope`), `data/sahamscope.json` (cache).

## 1. Latar & keputusan

Lima sumber SahamScope terverifikasi bisa diambil (pulse harian T-1, broker-accumulation
per emiten, insiders per emiten, shareholders statis, mom-changes). Fondasi ini menyiapkan
jalur data agar sub-proyek 1–3 tinggal konsumsi. Scope unduhan: WATCHLIST saja
(per-emiten 2 req; seluruh pasar 845 req tidak layak).

## 2. Fetch (`scripts/fetch-sahamscope.py`, stdlib saja)

- Fungsi `ambil_scope(kodes, log_fn)`: `GET dashboard-summary` (1 req) +
  per kode `broker-accumulation?top=5&start_date={H-30}` dan `insiders?page_size=10`
  (delay 1,0 dtk antar req; timeout 30 dtk/req; UA browser seperti fetcher lain).
- Keluaran dict: `{diambil (ISO), pulse: {tgl, top_net_buy[5: kode,broker,nval], highlight_insiders[10]}, emiten: {KODE: {acc: {top_buyers[5], top_sellers[5], series: {BROKER: [[nval,cum] x ≤30]}}, insider: [≤10 item apa adanya]}}}`.
- Series diringkas (tanpa bavg/savg harian) — cukup untuk fondasi.
- Static files besar/basi (`idx_shareholders.json`, `mom_changes_latest.json`) TIDAK
  diunduh otomatis (manual bila sub-proyek butuh).

## 3. Cache & integrasi server (`app/app-screener.py`)

- Cache `data/sahamscope.json`, TTL 24 jam dari field `diambil`; kunci reinstall:
  modul dimuat via `load_mod` seperti fetcher lain (tambah import explisit bila
  dibutuhkan PyInstaller/launcher — launcher mode source, jadi aman).
- `muat_semua()` (jalur Download Data): panggil `ambil_scope` setelah KSEI dengan
  cache 24 jam; sertakan hasilnya di respons (`"scope": {...}` atau
  `{"ok": false, "peringatan": ...}`); KEGAGALAN SCOPE TIDAK MENGGAGALKAN DOWNLOAD.
- Endpoint baru `GET /api/scope`: baca cache apa adanya (tidak fetch).
  Respons tanpa cache: `{"ok": false, "error": "belum ada cache scope"}`.
- Scan Pasar TIDAK memicu fetch scope (cakupan watchlist saja).

## 4. Kontrak frontend (`web/screener-praktis.html`)

- State `S.scope = {}`; diisi dari `j.scope` di handler Download dan dari
  `/api/scope` saat inisialisasi (agar refresh tidak kehilangan badge).
- Strip makro: badge `Scope {tgl singkat}` + tooltip sumber; kondisi:
  segar (<24 jam) normal, basi kuning, gagal/total-absen → badge kuning
  "Scope {basi/gagal} — data {tgl}" atau disembunyikan bila tak ada cache sama sekali.
- Drawer BELUM berubah (konsumsi di sub-proyek 1–3).

## 5. Error handling & edge case

- Timeout/HTTP error/JSON rusak per req → catat log, lanjut emiten berikutnya;
  hasil parsial tetap disimpan dengan `peringatan` berisi daftar gagal.
- API mati total + ada cache → sajikan cache + badge basi/kuning.
- API mati total + tanpa cache → Download tetap ok; badge disembunyikan; toast
  menyebut scope gagal (tidak memblokir).
- `top_net_sell` dashboard terlihat janggal (nilai kecil) → fondasi menyimpan
  apa adanya TANPA menampilkannya di UI (validasi di sub-proyek pemakai).

## 6. Testing

- Python offline: impor modul + parse contoh respons tersimpan (unit tanpa network).
- Python live (sekali, manual): `ambil_scope(["BBCA","TLKM"])` → cache tertulis valid.
- Node smoke: `S.scope` terisi dari respons; badge 3 kondisi (segar/basi/absen).
- Simulasi gagal: API dimatikan (URL salah via env/monkeypatch) → Download tetap sukses.
- Manual browser: Download Data → badge "Scope {tgl}" muncul; matikan internet →
  Download ulang → badge kuning + data lama tetap tampil.

## 7. Non-goals (YAGNI)

- Tanpa kolom/skor/flag baru, tanpa unduh file statis besar, tanpa Scan Pasar,
  tanpa validasi `top_net_sell`, tanpa rebuild `.exe` (launcher mode source).
