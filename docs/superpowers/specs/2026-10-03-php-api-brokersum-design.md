# Spec: PHP API Broker Summary + MariaDB (IndoPremier)

Tanggal: 2026-10-03 | Status: disetujui user (API pakai PHP)
Koneksi: MariaDB 10.11.10 @127.0.0.1:3306, db `saham` (kosong), root tanpa password.
PHP CLI 8.4 + pdo_mysql ADA. EnvKit MCP http://127.0.0.1:47600 (token di chat).

## 1. Latar & keputusan

Data broker-summary IndoPremier (gross buy/sell + avg, window bebas) disimpan
ke MariaDB sebagai histori snapshot per Download. API ditulis PHP, di-serve
EnvKit (nginx + php-fpm). Python app memanggil via HTTP (urllib stdlib).
DB/EnvKit mati → fallback JSON lama, Download tetap jalan (portabilitas utuh).

## 2. Skema (`saham`)

```sql
CREATE TABLE IF NOT EXISTS broker_summary (
  id BIGINT AUTO_RANDOM ... -- AUTO_INCREMENT
  kode VARCHAR(8) NOT NULL,
  tgl_awal DATE NOT NULL, tgl_akhir DATE NOT NULL,
  broker VARCHAR(4) NOT NULL, sisi ENUM('B','S') NOT NULL,
  lot BIGINT NOT NULL, val_rp BIGINT NOT NULL, avg INT NOT NULL,
  diambil DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id), KEY (kode, tgl_akhir), UNIQUE (kode, tgl_awal, tgl_akhir, broker, sisi)
) ENGINE=InnoDB;
```
(`UNIQUE` = idempoten: Download ulang window sama tidak ganda.)

## 3. PHP API — QUERY SAJA / read-only (satu folder site EnvKit)

- `GET /api/summary?kode=ADRO&limit=3` → 3 snapshot window terakhir per broker/sisi.
- `GET /api/health` → `{ok, db: true/false}` (untuk fallback cepat).
- TANPA endpoint tulis. Tulis database HANYA via CLI `scripts/db-tulis.php`
  (dipanggil Python subprocess, JSON via stdin → hasil via stdout).
- Tanpa framework (router + PDO, <200 baris). Kredensial via env `.env`
  (bukan hardcode): DB_HOST/PORT/NAME/USER/PASS.

## 4. Python (`fetch-brokersum.py`, stdlib) + tulis CLI

- Fetch IndoPremier `fd=all&board=all`, window 30 hari kalender, 1 req/emiten,
  delay 1 dtk, timeout 30. Parse tabel buyer/seller: lot (koma ribuan → int),
  val ("14.7 B"/"3.0 B"/"510 M" → rupiah int), avg (koma ribuan → int).
- Tulis DB: pipe JSON ke `php scripts/db-tulis.php` (subprocess, best-effort;
  gagal = log, lanjut). CLI ini juga yang `CREATE TABLE IF NOT EXISTS`.
- Respons ke frontend: bentuk SAMA seperti scope sekarang
  (`top_buyers/top_sellers/series` versi ringkas) agar drawer/kombo/exit
  tidak berubah; label sumber "IP".

## 5. Hosting (butuh konfirmasi saat eksekusi)

- Opsi utama: site EnvKit baru (misal `saham-api.test`) via `add_site` +
  deploy file + uji `GET /health`. Alternatif bila user menolak site baru:
  PHP built-in server (`php -S`) via scheduled task — rapuh, tidak disarankan.
- phpMyAdmin/Adminer opsional untuk lihat tabel (instal bila diminta).

## 6. Error handling & edge case

- API/DB mati → Python catch → JSON-only, badge kuning "DB mati".
- Window hari libur (data kosong) → snapshot kosong tetap disimpan dengan
  flag? TIDAK (YAGNI): skip bila buyers+sellers kosong.
- Angka "—"/kosong → 0. Duplikat → `INSERT ... ON DUPLICATE KEY UPDATE`.

## 7. Testing

- PHP CLI: `php db-tulis.php --selftest` (buat tabel → insert dummy → baca → hapus).
- PHP API: `GET /api/health` + `/api/summary?kode=ADRO` setelah ada data.
- Python offline: fixture HTML → angka B/M/koma benar.
- Live: 1 emiten → baris DB + respons bentuk scope; matikan mysql
  (konfirmasi dulu) → Download tetap sukses.
- Manual: Adminer opsional.

## 8. Non-goals (YAGNI)

- Tanpa baca histori untuk sinyal (tahap berikut), tanpa auth API (localhost),
  tanpa ubah skor/aksi/frontend selain label sumber, tanpa rebuild `.exe`.
