# Sistem Screening Saham: Fundamental + Catalyst + Bandarmology + Technical

## 1. Tujuan

Membangun sistem screening saham Indonesia untuk trading harian sampai swing 1–4 minggu.

Prinsip utama:

> **Fundamental = WHAT**  
> **Catalyst / Corporate Action = WHY NOW**  
> **Bandarmology / Flow = WHO IS MOVING IT**  
> **Technical = WHEN TO ENTER**

Fundamental tidak dipakai sebagai sinyal entry tunggal karena laporan keuangan bersifat lagging. Sistem harus mencari perubahan bisnis, katalis, aliran dana, dan konfirmasi harga.

---

# 2. Arsitektur Score

Total score: **100**

| Komponen | Bobot | Fungsi |
|---|---:|---|
| Fundamental Quality | 15 | Menilai kualitas bisnis |
| Fundamental Growth / Earnings Momentum | 10 | Mencari percepatan kinerja |
| Catalyst & Corporate Action | 15 | Mencari alasan saham berpotensi bergerak |
| Bandarmology / Market Flow | 25 | Mendeteksi akumulasi/distribusi |
| Technical Trend | 15 | Menentukan kondisi trend |
| Technical Entry | 10 | Menentukan timing entry |
| Risk / Event Warning | 10 | Mengurangi risiko kejadian negatif |
| **TOTAL** | **100** | |

> Bobot dapat diubah setelah dilakukan backtest.

---

# 3. Filosofi Screening

Jangan mencari:

> "Saham dengan fundamental terbaik."

Tetapi cari:

> **"Saham yang fundamentalnya cukup sehat, sedang mengalami perubahan positif, mendapat katalis, mulai diakumulasi, lalu dikonfirmasi technical."**

Tujuan fundamental tahap awal adalah **membuang saham yang buruk**, bukan memprediksi harga secara langsung.

---

# 4. STAGE 1 — Fundamental Quality

## 4.1 Revenue Growth

Hitung:

```text
Revenue Growth YoY =
(Revenue periode sekarang - Revenue periode sebelumnya)
/
Revenue periode sebelumnya × 100%
```

Score contoh:

| Revenue Growth YoY | Score |
|---:|---:|
| > 30% | 5 |
| 15–30% | 4 |
| 5–15% | 3 |
| 0–5% | 1 |
| < 0% | 0 |

## 4.2 Net Profit Growth

```text
Profit Growth YoY =
(Net Profit sekarang - Net Profit sebelumnya)
/
Net Profit sebelumnya × 100%
```

| Profit Growth YoY | Score |
|---:|---:|
| > 30% | 5 |
| 15–30% | 4 |
| 5–15% | 3 |
| 0–5% | 1 |
| < 0% | 0 |

## 4.3 Cash Flow

Periksa:

- Operating Cash Flow
- Free Cash Flow
- apakah laba didukung kas nyata

Red flag:

```text
Net Profit ↑
Operating Cash Flow ↓ / negatif
```

Jangan langsung dianggap buruk karena bisa ada faktor working capital, tetapi harus diberi perhatian.

## 4.4 Balance Sheet

Periksa:

- DER
- Net Debt
- Current Ratio
- Interest Coverage
- perubahan utang

DER harus dibandingkan dengan perusahaan sejenis/sektor yang sama.

## 4.5 Margin

Periksa:

- Gross Margin
- Operating Margin
- Net Profit Margin

Hal menarik:

```text
Revenue ↑
Margin ↑
Profit ↑↑
```

Ini menunjukkan operating leverage / earnings acceleration.

---

# 5. STAGE 2 — Earnings Momentum

Jangan hanya melihat apakah laba naik.

Cari **acceleration**.

Contoh:

```text
Q1 = 50 M
Q2 = 80 M
Q3 = 150 M
```

Lebih menarik daripada:

```text
Q1 = 100 M
Q2 = 105 M
Q3 = 110 M
```

## 5.1 Earnings Acceleration

Hitung perubahan pertumbuhan laba antarperiode.

Contoh:

```text
Profit Growth Q1 = +5%
Profit Growth Q2 = +18%
Profit Growth Q3 = +42%
```

Interpretasi:

```text
+5 → +18 → +42
```

= earnings acceleration.

Tambahkan score jika:

- revenue acceleration
- profit acceleration
- EPS acceleration
- margin expansion

---

# 6. STAGE 3 — Valuation

Valuation bukan sinyal BUY tunggal.

Gunakan:

- PER
- PBV
- EV/EBITDA
- PEG
- Dividend Yield jika relevan

## Prinsip

PER murah + laba turun:

```text
P/E 3x
Profit -50%
```

belum tentu murah.

PER harus dibaca bersama growth.

Contoh yang lebih menarik:

```text
Profit Growth +40%
PER 8x
```

dibanding:

```text
Profit Growth -30%
PER 3x
```

---

# 7. STAGE 4 — Catalyst Scanner

Ini bagian penting untuk mengatasi masalah laporan keuangan yang terlambat.

Cari perubahan yang bisa memengaruhi ekspektasi laba sebelum laporan berikutnya.

## Positive Catalyst

- kontrak baru
- ekspansi kapasitas
- peningkatan produksi
- peningkatan volume penjualan
- harga komoditas menguntungkan
- akuisisi produktif
- debt reduction
- buyback
- produk baru
- ekspansi pasar
- perubahan kebijakan yang menguntungkan
- kenaikan ASP / harga jual
- peningkatan utilisasi pabrik

## Negative Catalyst

- penurunan produksi
- kontrak batal
- margin tertekan
- harga komoditas turun
- utang meningkat tajam
- masalah operasional
- tuntutan hukum material
- suspensi
- restrukturisasi karena kesulitan keuangan

---

# 8. Corporate Action Scanner

Corporate action harus dipisahkan dari fundamental.

## Event yang perlu dipantau

- Right Issue
- Private Placement
- Stock Split
- Reverse Stock Split
- Warrant
- Buyback
- Dividen
- Merger
- Akuisisi
- Tender Offer
- Perubahan Pengendali
- RUPS
- Restrukturisasi Utang
- Suspensi
- Delisting
- Akuisisi aset
- Penjualan aset

---

# 9. Right Issue Analysis

Jangan menggunakan aturan:

> Right issue = buruk.

Analisis:

## Positif

Dana digunakan untuk:

- ekspansi produktif
- meningkatkan kapasitas
- akuisisi bisnis profitable
- mengurangi utang mahal
- memperbaiki struktur modal

## Negatif

Dana digunakan untuk:

- menutup kerugian
- membayar kewajiban karena cash flow buruk
- menambal kebutuhan modal berulang
- dilusi sangat besar
- transaksi dengan pihak terafiliasi yang merugikan

## Yang perlu dihitung

### Dilution

```text
Dilution =
Saham Baru / Total Saham Setelah Right Issue
```

### Harga teoritis setelah right issue

Gunakan TERP:

```text
TERP =
(Harga Saham × Saham Lama + Harga RI × Saham Baru)
/
(Saham Lama + Saham Baru)
```

Kemudian bandingkan dengan harga pasar.

---

# 10. Event Risk Score

Buat skor risiko terpisah.

Contoh:

| Event | Impact |
|---|---:|
| Buyback | +3 |
| Kontrak besar | +3 |
| Akuisisi produktif | +2 |
| Ekspansi kapasitas | +2 |
| Dividen kuat | +1 |
| Right Issue produktif | +1 |
| Right Issue dilutif | -3 |
| Private Placement dilutif | -3 |
| Restrukturisasi bermasalah | -4 |
| Potensi suspensi | -5 |

Score final harus mempertimbangkan materialitas dan konteks perusahaan.

---

# 11. STAGE 5 — Bandarmology / Market Flow

Bobot: **25**

Data yang dapat digunakan:

- Broker Summary
- Net Buy / Net Sell
- volume
- value transaksi
- frekuensi transaksi
- perubahan broker dominan
- foreign flow jika tersedia
- accumulation / distribution
- konsistensi akumulasi beberapa hari

## 11.1 Net Buy

Contoh:

```text
Net Buy 1 hari      +10 M
Net Buy 3 hari      +35 M
Net Buy 5 hari      +70 M
```

lebih menarik daripada hanya:

```text
Net Buy hari ini +70 M
```

karena konsistensi lebih penting.

## 11.2 Akumulasi

Cari kombinasi:

```text
Harga relatif sideways
+
Volume meningkat
+
Net Buy broker tertentu
```

Ini dapat menjadi indikasi awal accumulation.

Tetapi tidak boleh dianggap bukti pasti adanya "bandar".

---

# 12. Distribution Warning

Waspadai:

```text
Harga masih naik
Volume sangat besar
Tetapi broker dominan mulai net sell
```

atau:

```text
Harga gagal breakout
Volume besar
Net sell meningkat
```

Ini dapat menjadi warning distribusi.

---

# 13. STAGE 6 — Technical Trend

Bobot: **15**

Indikator yang digunakan:

- EMA20
- MACD
- Supertrend
- PSAR
- Support / Resistance
- Volume

## Trend Score

Contoh:

### EMA20

```text
Harga > EMA20       +3
Harga < EMA20       0
```

### MACD

```text
MACD bullish cross / histogram meningkat  +3
Netral                                    +1
Bearish                                   0
```

### Supertrend

```text
Bullish +2
Bearish  0
```

### PSAR

```text
Bullish +2
Bearish  0
```

### Structure

```text
Higher High + Higher Low    +5
Sideways                    +2
Lower High + Lower Low       0
```

---

# 14. STAGE 7 — Technical Entry

Bobot: **10**

Cari:

## Breakout

```text
Resistance ditembus
+
Volume meningkat
+
Close di atas resistance
```

## Pullback

```text
Trend bullish
+
Harga pullback ke support / EMA20
+
Volume selling mengecil
+
Buyer kembali masuk
```

Jangan mengejar candle yang sudah terlalu jauh dari entry ideal.

---

# 15. Final Score

Contoh:

```text
Fundamental Quality          13/15
Earnings Momentum             9/10
Catalyst                      12/15
Bandarmology                  22/25
Technical Trend               12/15
Technical Entry                8/10
Risk/Event Warning             8/10
-----------------------------------
TOTAL                         84/100
```

Interpretasi awal:

| Score | Status |
|---:|---|
| 85–100 | Strong candidate |
| 75–84 | Candidate |
| 65–74 | Watchlist |
| 50–64 | Weak |
| <50 | Avoid |

**Threshold ini harus diuji dengan backtest**, bukan dianggap angka final.

---

# 16. Contoh Output Screener

```text
================================================
STOCK: XYZ
DATE: 2026-10-08
================================================

TOTAL SCORE: 84/100

FUNDAMENTAL
Quality             13/15
Growth Momentum      9/10

✓ Revenue growth
✓ Profit acceleration
✓ Margin expansion
✓ Operating cash flow positive
⚠ Debt increased

CATALYST
Score               12/15

✓ New contract
✓ Capacity expansion
✓ Improving commodity price
⚠ Upcoming corporate action

BANDARMOLOGY
Score               22/25

✓ Broker accumulation 4 days
✓ Net buy increasing
✓ Volume expansion
✓ Price still near base

TECHNICAL
Score               20/25

✓ Above EMA20
✓ MACD bullish
✓ Supertrend bullish
✓ Breakout resistance
⚠ Price already +8% from breakout

RISK
Score                8/10

✓ No major negative event
⚠ Corporate action in 23 days

STATUS:
WATCH / BUY ON PULLBACK
```

---

# 17. Jangan BUY Hanya Karena Score Tinggi

Score tinggi harus tetap melewati **hard filter**.

Contoh:

```text
IF
Liquidity terlalu kecil
OR
Suspended
OR
Corporate action sangat berisiko
OR
technical breakdown
OR
distribution kuat
THEN
DO NOT BUY
```

---

# 18. Hard Filter Likuiditas

Untuk trader, likuiditas sangat penting.

Minimal screening:

- Average Daily Value
- Average Volume
- frekuensi transaksi
- bid/offer spread

Contoh:

```text
Average Daily Value > batas minimum
```

Batas harus disesuaikan modal dan strategi.

---

# 19. Early Warning System

Sistem tidak hanya menghasilkan BUY.

Sistem juga harus menghasilkan:

```text
ACCUMULATION
BREAKOUT
PULLBACK
DISTRIBUTION
EARNINGS ACCELERATION
CORPORATE ACTION
RISK EVENT
```

Contoh:

```text
XYZ

+ Earnings acceleration
+ Broker accumulation
+ Volume expansion
+ Breakout

BUT

- Right issue announcement approaching

STATUS:
WAIT / INVESTIGATE
```

---

# 20. Data Freshness

Setiap data harus memiliki timestamp.

Contoh database:

```text
financial_period
report_date
data_date
source
created_at
updated_at
```

Bedakan:

```text
Period: Q2 2026
Report Date: 25 July 2026
```

Jangan menganggap data Q2 tersedia sejak akhir Juni.

## Prinsip penting

**Market hanya boleh menggunakan informasi yang sudah tersedia pada tanggal screening.**

Ini sangat penting untuk menghindari **look-ahead bias** dalam backtest.

---

# 21. Corporate Action Timeline

Setiap event memiliki:

```text
announcement_date
cum_date
ex_date
record_date
payment_date
event_type
event_status
```

Untuk right issue:

```text
announcement
→ RUPS
→ effective registration
→ cum date
→ ex date
→ trading rights
→ subscription
→ new shares listed
```

Sistem harus memperhitungkan posisi tanggal saat membuat signal.

---

# 22. Backtesting

Jangan langsung menggunakan score 100 dan menganggapnya benar.

Backtest minimal:

```text
Data 3–5 tahun
+
Signal harian
+
Transaction fee
+
Slippage
+
Corporate action
+
Suspension
+
Delisting jika relevan
```

Untuk strategi Anda, masukkan biaya:

```text
Buy fee       = 0.15%
Sell fee      = 0.25%
Slippage      = 0.20%
```

Total round trip minimal:

```text
0.15% + 0.25% + slippage
```

Sesuaikan slippage dengan kondisi likuiditas.

---

# 23. Jangan Mengoptimalkan Score Secara Berlebihan

Bahaya:

```text
Score 83 → Profit bagus
Score 84 → Profit bagus
Score 85 → Profit sangat bagus
```

bisa saja hanya hasil overfitting.

Lebih baik menguji:

```text
Score 60+
Score 70+
Score 75+
Score 80+
```

dan lihat distribusi return masing-masing.

---

# 24. Metric Backtest

Jangan hanya melihat win rate.

Gunakan:

### Win Rate

```text
Winning Trades / Total Trades
```

### Average Win

```text
Total Profit Winning Trades
/
Jumlah Winning Trades
```

### Average Loss

```text
Total Loss
/
Jumlah Losing Trades
```

### Expectancy

```text
Expectancy =
(Win Rate × Average Win)
-
(Loss Rate × Average Loss)
```

Contoh:

```text
Win rate      45%
Average win    5%
Average loss   2%

Expectancy =
0.45 × 5% - 0.55 × 2%
= 1.15%
```

Ini jauh lebih berguna daripada sekadar:

> "Win rate saya 60%."

---

# 25. Sistem Final

Flow yang disarankan:

```text
                 UNIVERSE SAHAM
                       │
                       ↓
                 LIQUIDITY FILTER
                       │
                       ↓
              FUNDAMENTAL QUALITY
                       │
                       ↓
             EARNINGS MOMENTUM
                       │
                       ↓
              CATALYST SCANNER
                       │
                       ↓
          CORPORATE ACTION CHECK
                       │
                       ↓
            BANDARMOLOGY / FLOW
                       │
                       ↓
              TECHNICAL TREND
                       │
                       ↓
              ENTRY CONFIRMATION
                       │
                       ↓
                RISK FILTER
                       │
                       ↓
                  SCORE 0–100
                       │
              ┌────────┴────────┐
              ↓                 ↓
          WATCHLIST          BUY SIGNAL
                                │
                                ↓
                         POSITION SIZING
                                │
                                ↓
                           STOP LOSS
                                │
                                ↓
                       TAKE PROFIT / EXIT
```

---

# 26. Prinsip Utama Sistem

### Jangan menunggu fundamental sempurna.

Cari:

```text
Fundamental cukup sehat
+
fundamental mulai membaik
+
ada catalyst
+
money flow masuk
+
technical mengonfirmasi
```

### Jangan mengejar harga hanya karena score tinggi.

Score tinggi = **kandidat**.

Entry tetap harus melihat:

- harga
- volume
- support
- resistance
- risk/reward
- market condition

### Jangan percaya "bandar" secara mentah.

Broker accumulation adalah **indikator flow**, bukan bukti pasti ada satu pihak yang sedang mengendalikan harga.

### Jangan gunakan data masa depan dalam backtest.

Semua signal harus hanya menggunakan informasi yang memang sudah tersedia pada waktu tersebut.

---

# 27. Versi Ringkas

Formula konsep:

```text
FINAL SCORE =
15% Fundamental Quality
+
10% Earnings Momentum
+
15% Catalyst
+
25% Market Flow
+
15% Technical Trend
+
10% Technical Entry
+
10% Risk/Event
```

Dan konsep trading:

```text
GOOD BUSINESS
      +
IMPROVING BUSINESS
      +
CATALYST
      +
ACCUMULATION
      +
TREND
      +
GOOD ENTRY
      =
HIGH QUALITY TRADE CANDIDATE
```

**Bukan jaminan profit. Semua bobot, threshold, dan rule harus divalidasi dengan backtest dan forward test.**
