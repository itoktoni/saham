# Spec: Direktori Broker + Label Ukuran

Tanggal: 2026-10-03 | Pendekatan: A (JSON + fungsi sentral) | Status: disetujui user
File: `data/broker-direktori.json` (baru, user-editable), `app/app-screener.py`
  (serve), `web/screener-praktis.html` (fungsi + label + legenda).

## 1. Latar & keputusan

Kode broker saja menyesatkan (XL Rp30M herd vs XL Rp2M satu pelaku).
Solusi: direktori kategori + aturan ukuran — "nilai menentukan, bukan cuma kode".
Ambang: ≥Rp1M = bukan ritel; Rp100jt–1M = campuran. Display-only.

## 2. Direktori (`data/broker-direktori.json`)

- Bentuk: `{KODE: {kat, nama, afiliasi}}`.
  kat ∈ `asing, smart, abu, ritel, zombie`. Isi awal dari daftar user
  (asing: AK BK ZP YU AI KZ BQ DP RX; smart: RF KI IF HP DH SS MU ES DR YJ BB DX OD RB OK;
  abu: CC SQ NI AZ LG XA YB; ritel: XC XL YP PD MG CP; zombie: ZOMBIE).
- Konflik daftar (RB di smart dan OK?/Bakrie) diselesaikan: RB ikut smart/Afiliasi Salim
  sesuai bagian 2 (bukan ungu); bila ragu → `abu`, bukan tebak.
- Server baca tiap Download → `S.dirBroker` (respons + inisialisasi setara scope;
  tanpa file → `{}` = semua abu). Tanpa fetch/TTL (file lokal statis).

## 3. Fungsi sentral (`SP.brokerInfo`, murni, fixed)

- `brokerInfo(kode, nval, dir)` → `{label, warna, flag}`.
  label = "Kategori — Nama"; tak dikenal → abu "Lainnya".
- Warna (hex fixed): asing `#1f5fd0`, smart `#17795e`, abu `#8a8f98`,
  ritel `#b26a00`, zombie `#c9cfd6`; afiliasi menimpa dot: PP `#b26a00`→
  bedakan: PP `#e65100`, Sinarmas `#4fc3f7`, Salim `#1a237e`, Bakrie `#6a1b9a`,
  scalper (MG/CP) `#9ccc65`, impostor-kombo (XC/XL/YP/AZ/PD) `#fdd835`.
  (Warna final di legenda; fungsi kembalikan kode warna + nama kelas.)
- Ukuran (hanya kat ritel, `nval` absen → skip): |nval|≥1M → flag
  "besar, bukan ritel" + warna oranye `#e65100`; 100jt–1M → flag "campuran".

## 4. Titik pakai (label saja, tanpa ubah angka/aturan)

- Daftar broker exit-level, baris smart-money, chip kombo/bounty, kartu pulse:
  format `KODE ●` + tooltip label + flag.
- Legenda di Lanjutan + catatan ukuran. Tanpa kolom tabel baru.

## 5. Error handling & edge case

- File rusak/absen → `{}` → semua abu "Lainnya"/tanpa direktori.
- `nval` 0/absen → tanpa flag ukuran.

## 6. Testing

- Smoke `brokerInfo`: OD→asing; XL+2M→flag besar; XL+50jt→ritel biasa;
  ZZ→abu; tanpa nval→tanpa flag; RB→smart/Salim.
- String HTML + manual: drawer + edit JSON 1 kategori → reload berubah.

## 7. Non-goals (YAGNI)

- Tanpa ubah skor/fase/aturan combo/exit, tanpa auto-update direktori,
  tanpa rebuild `.exe`.
