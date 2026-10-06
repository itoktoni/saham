# Dokumentasi Spesifikasi & Panduan Pengembangan Perangkat Lunak
## Sistem Automated Stock Screening, Valuasi Nilai Intrinsik, dan Kalkulator Margin of Safety (MOS)

---

## 1. Pendahuluan & Arsitektur Sistem

Dokumen ini berisi spesifikasi teknis dan algoritma logika untuk mengembangkan aplikasi/software **Stock Screening & Intrinsic Value Valuation Engine** berbasis pendekatan *Value Investing* (Rivan Kurniawan & Metode Benjamin Graham Penyesuaian Pasar Indonesia).

### 1.1 Diagram Alir Utama & Modul Sistem
Sistem terbagi dari 4 modul utama:
1. **Data Ingestion & Normalization Module**: Mengambil data laporan keuangan emiten (RTI, Yahoo Finance, IDX, atau CSV/API) dan melakukan normalisasi/disetahunkan (*annualized*).
2. **Screening & Ranking Engine**: Memfilter emiten berdasarkan kriteria kualitatif dan kuantitatif serta melakukan pembobotan (*ranking score*).
3. **Valuation Engine**: Menghitung nilai intrinsik (harga wajar) menggunakan 6 metode valuasi fundamental.
4. **Risk & Decision Engine**: Menghitung *Margin of Safety* (MOS), menetapkan harga beli maksimal, serta memberikan sinyal eksekusi (*BUY*, *HOLD*, *TAKE PROFIT*, *CUT LOSS*).

```
[Sumber Data / API] ──> [1. Data Ingestion & Normalization]
                               │
                               ▼
                   [2. Screening & Ranking Engine]
                               │
                               ▼
                   [3. Intrinsic Value Engine]
                               │
                               ▼
                   [4. Risk & Decision Engine (MOS)]
                               │
                               ▼
                    [Output: Dashboard / Excel]
```

---

## 2. Modul Data Ingestion & Normalisasi

### 2.1 Formula Normalisasi Laporan Keuangan Kuartalan (*Annualized*)
Laporan keuangan kuartalan harus disetahunkan (*annualized*) agar perhitungan EPS, ROE, dan PER valid:

- **Kuartal 1 (Q1)**: `Annualized Factor = 4` → `Data Q1 × 4`
- **Kuartal 2 (Q2)**: `Annualized Factor = 2` → `Data Q2 × 2`
- **Kuartal 3 (Q3)**: `Annualized Factor = 4/3` → `(Data Q3 ÷ 3) × 4`
- **Kuartal 4 (Q4)**: `Annualized Factor = 1` → `Data Full Year`

---

## 3. Modul 1: Screening & Ranking Engine

### 3.1 Parameter & Threshold Screening
Filter awal menyaring ratusan emiten di bursa (IHSG / IDX) berdasarkan kriteria berikut:

| Parameter | Kriteria Utama | Bobot Ranking (*Scoring*) | Keterangan |
| :--- | :--- | :--- | :--- |
| **PBV (*Price to Book Value*)** | `PBV < 1,00` atau terdiskon historis | Ranking 1 = PBV Terkecil | Mengukur tingkat diskon aset bersih. |
| **ROE (*Return on Equity*)** | `ROE ≥ 10%` (di atas rerata industri) | Ranking 1 = ROE Terbesar | Efisiensi perusahaan menghasilkan laba. |
| **PER (*Price to Earnings*)** | Lebih rendah dari rerata industri | Ranking 1 = PER Terkecil | Valuasi relatif harga terhadap laba. |
| **DER (*Debt to Equity*)** | `DER < 1,00` (utang terkontrol) | Ranking 1 = DER Terkecil | Solvabilitas dan tingkat risiko utang. |
| **EPS Trend** | *Up Trend* / Bertumbuh konsisten | Score 1 (Up), 200 (Fluktuatif Up), 1000 (Down) | Memastikan perusahaan *profitable*. |
| **Likuiditas** | Aktif diperdagangkan (Bid/Offer rapat) | Score 1 (Likuid), 1000 (Tidak Likuid) | Kemudahan eksekusi transaksi. |
| **Dividend Track Record** | Rutin membagikan dividen | Point Bonus / Filter khusus | Indikator *cash flow* riil perusahaan. |

### 3.2 Algoritma Pembobotan Total (*Total Ranking Score*)

```
Total Rank = Rank_PBV + Rank_ROE + Rank_PER + Rank_DER + Rank_Likuiditas + Rank_EPS Trend
```

Emiten dengan **Total Rank terkecil** menempati posisi teratas sebagai kandidat saham *undervalued* terbaik.

---

## 4. Modul 2: Mesin Valuasi Nilai Intrinsik (*Intrinsic Value Engine*)

Sistem akan menghitung harga wajar emiten yang lolos *screening* menggunakan metode yang sesuai dengan karakteristik bisnis emiten:

### 4.1 Formula 1: Adjusted Benjamin Graham Formula (Khusus Pasar Indonesia)
Cocok untuk penilaian umum emiten dengan penyesuaian kondisi suku bunga dan risiko pasar Indonesia.

```
Nilai Intrinsik = (EPS_Annualized × (7 + 1g) × 7,8) ÷ Y
```

- **`EPS_Annualized`**: Laba bersih per lembar saham yang disetahunkan (*Normalized EPS*).
- **`7`**: Konstanta konservatif penyesuaian pasar Indonesia (diganti dari 8.5 US).
- **`1g`**: Multiplier pertumbuhan laba (*growth rate*), di mana `g` adalah CAGR Laba Bersih yang **dibatasi maksimal 15%** (`g ≤ 15`, dalam persen).
- **`7,8`**: Yield Obligasi Pemerintah Indonesia 10 Tahun (*Government Bond 10Y*, dalam persen).
- **`Y`**: Yield obligasi korporasi rating AAA di Indonesia (asumsi standar ~11,4%, dalam persen).

### 4.2 Formula 2: EPS Discounted Model (5-Year Projection)
Cocok untuk perusahaan *growth stock* dengan pertumbuhan laba yang konsisten.

- **Langkah 1**: Hitung Book Value per Share: `BVPS = Total Ekuitas ÷ Jumlah Saham Beredar`
- **Langkah 2**: Proyeksikan EPS selama 5 tahun ke depan berdasarkan CAGR laba bersih (`g`, capped at 15%):
  ```
  EPS_t = EPS_(t-1) × (1 + g)
  ```
- **Langkah 3**: Hitung Present Value (PV) dari tiap EPS menggunakan *Discount Rate* (`r = Inflasi Rerata 5% + Risk Buffer 2% = 7%`):
  ```
  Discounted EPS_t = EPS_t ÷ (1 + r)^t
  ```
- **Langkah 4**: Hitung *Intrinsic Value*:
  ```
  Nilai Intrinsik = BVPS + Σ(t=1..5) Discounted EPS_t
  ```

### 4.3 Formula 3: Equity Growth Model (Proyeksi Ekuitas)
Cocok untuk perusahaan *cyclical* atau emiten yang pertumbuhan labanya fluktuatif.

- **Langkah 1**: Hitung `BVPS_0 = Total Ekuitas ÷ Jumlah Saham Beredar`
- **Langkah 2**: Hitung `ROE = (Laba Bersih Annualized ÷ Total Ekuitas) × 100%`
- **Langkah 3**: Akumulasikan pertumbuhan ekuitas selama 5 tahun ke depan menggunakan ROE:
  ```
  Nilai Intrinsik = BVPS_0 × (1 + ROE)^5
  ```

### 4.4 Formula 4: ROE - PBV Matrix Model
Digunakan untuk menentukan PBV wajar berdasarkan kemampuan perusahaan menghasilkan ROE.

- **Aturan Dasar ROE - PBV**:
  - `ROE 10% → PBV Wajar 1,0x`
  - `ROE 15% → PBV Wajar 1,5x`
  - `ROE 20% → PBV Wajar 2,0x`
  - **Formula Umum**: `PBV Wajar = ROE ÷ 10%`
- **Nilai Intrinsik**:
  ```
  Nilai Intrinsik = BVPS × (ROE ÷ 10%)
  ```

### 4.5 Formula 5: Discounted Cash Flow (DCF) Model

```
DCF = Σ(t=1..n) FCF_t ÷ (1 + WACC)^t
Nilai Ekuitas = DCF + Kas & Setara Kas − Total Utang
Nilai Intrinsik per Lembar = Nilai Ekuitas ÷ Jumlah Saham Beredar
```

---

## 5. Modul 3: Risk & Decision Engine (Margin of Safety)

### 5.1 Kalkulasi Margin of Safety (MOS)

```
MOS (%) = ((Nilai Intrinsik − Harga Pasar) ÷ Nilai Intrinsik) × 100%
```

### 5.2 Target MOS & Harga Beli Maksimal
- **Saham Normal / Fundamental Stabil**: Minimal Target MOS = **30%**.
- **Saham Cyclical / Utang Tinggi / Volatilitas Tinggi**: Minimal Target MOS = **50%**.

```
Harga Beli Maksimal = Nilai Intrinsik × (1 − Target MOS)
```

### 5.3 Logika Matriks Keputusan Otomatis

```
IF Harga Pasar <= Harga Beli Maksimal THEN
    SIGNAL = "STRONG BUY" (Beli bertahap)
ELSE IF Harga Pasar > Harga Beli Maksimal AND Harga Pasar < Nilai Intrinsik THEN
    SIGNAL = "HOLD / WATCHLIST" (Tunggu diskon / Simpan)
ELSE IF Harga Pasar >= Nilai Intrinsik THEN
    SIGNAL = "TAKE PROFIT" (Harga sudah wajar / overvalued)
END IF
```

---

## 6. Modul 4: Skema Data & Implementasi Kode Python Reference

### 6.1 Contoh Kode Python (Screening, Valuation, & Decision Engine)

```python
import numpy as np
import pandas as pd

class StockValuationEngine:
    def __init__(self, eps, bvps, roe, cagr_growth, current_price, is_cyclical=False):
        self.eps = eps
        self.bvps = bvps
        self.roe = roe / 100.0  # Convert percentage
        self.g = min(cagr_growth / 100.0, 0.15)  # Cap growth at 15%
        self.current_price = current_price
        self.is_cyclical = is_cyclical

    def benjamin_graham_adjusted(self, bond_yield_10y=0.078, corporate_bond_aaa=0.114):
        # Formula: (EPS * (7 + 1g) * 7.8) / Y
        g_percent = self.g * 100.0
        intrinsic_val = (self.eps * (7.0 + 1.0 * g_percent) * (bond_yield_10y * 100.0)) / (corporate_bond_aaa * 100.0)
        return round(intrinsic_val, 2)

    def eps_discounted_model(self, discount_rate=0.07):
        # 5-Year Future EPS, diskon PER TAHUN (sesuai formula §4.2)
        curr_eps = self.eps
        discounted_sum = 0.0
        for t in range(1, 6):
            curr_eps = curr_eps * (1 + self.g)
            discounted_sum += curr_eps / ((1 + discount_rate) ** t)
        intrinsic_val = self.bvps + discounted_sum
        return round(intrinsic_val, 2)

    def equity_growth_model(self):
        # 5-Year Equity Growth via ROE
        future_bvps = self.bvps * ((1 + self.roe) ** 5)
        return round(future_bvps, 2)

    def roe_pbv_model(self):
        # Fair PBV = ROE / 10%
        fair_pbv = self.roe / 0.10
        intrinsic_val = self.bvps * fair_pbv
        return round(intrinsic_val, 2)

    def evaluate_investment(self):
        if self.is_cyclical:
            val = self.equity_growth_model()
            target_mos = 0.50  # 50% for cyclical
        else:
            val = self.benjamin_graham_adjusted()
            target_mos = 0.30  # 30% for standard

        mos = ((val - self.current_price) / val) * 100.0
        max_buy_price = val * (1.0 - target_mos)

        if self.current_price <= max_buy_price:
            signal = "STRONG BUY"
        elif self.current_price < val:
            signal = "HOLD / WATCHLIST"
        else:
            signal = "TAKE PROFIT / OVERVALUED"

        return {
            "Nilai Intrinsik": val,
            "Harga Pasar": self.current_price,
            "Target MOS (%)": int(target_mos * 100),
            "MOS Actual (%)": round(mos, 2),
            "Harga Beli Maksimal": round(max_buy_price, 2),
            "Signal": signal
        }

# --- Contoh Penggunaan ---
# Saham PTBA (LK Contoh)
stock_ptba = StockValuationEngine(
    eps=503.8, bvps=2200, roe=22.5, cagr_growth=9.4, current_price=2600, is_cyclical=True
)
print("Evaluasi PTBA:", stock_ptba.evaluate_investment())
```

---

## 7. Contoh Hitungan Langkah demi Langkah (Studi Kasus)

Seluruh angka di bawah memakai data contoh PTBA dari kode §6.1:
`EPS = 503,8` · `BVPS = 2.200` · `ROE = 22,5%` · `CAGR = 9,4%` · `Harga = 2.600` · sifat *cyclical*.

### 7.1 Annualisasi (§2.1)
Laba kuartalan Q3 sebesar Rp300 miliar → annualized = `(300 ÷ 3) × 4 = Rp400 miliar`.

### 7.2 Total Ranking (§3.2)
Tiga emiten, masing-masing diberi peringkat per kriteria (1 = terbaik):

| Emiten | Rank PBV | Rank ROE | Rank PER | Rank DER | Rank Likuiditas | Rank EPS Trend | **Total Rank** |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 1 | 1 | 2 | 1 | 1 | 1 | **7** (teratas) |
| B | 2 | 2 | 1 | 3 | 1 | 1 | **10** |
| C | 3 | 3 | 3 | 2 | 1 | 200 | **212** (tertahan EPS fluktuatif) |

Emiten A menempati posisi 1 karena Total Rank terkecil.

### 7.3 Lima Formula Valuasi (§4.1–§4.5)
Pertama, `g = min(9,4%; 15%) = 9,4%`.

**1) Adjusted Graham:**
`503,8 × (7 + 9,4) × 7,8 ÷ 11,4 = 503,8 × 16,4 × 7,8 ÷ 11,4 = 64.446,1 ÷ 11,4 ≈ **5.653**`

**2) EPS Discounted (r = 7%):**

| t | EPS_t | Diskonto (1,07^t) | PV |
| ---: | ---: | ---: | ---: |
| 1 | 551,16 | 1,0700 | 515,10 |
| 2 | 602,97 | 1,1449 | 526,66 |
| 3 | 659,65 | 1,2250 | 538,47 |
| 4 | 721,66 | 1,3108 | 550,54 |
| 5 | 789,49 | 1,4026 | 562,89 |
| | | **Σ PV** | **2.693,66** |

`Nilai = BVPS + Σ PV = 2.200 + 2.693,66 ≈ **4.894**`

**3) Equity Growth:** `2.200 × (1,225)^5 = 2.200 × 2,75855 ≈ **6.069**`

**4) ROE–PBV:** `PBV wajar = 22,5 ÷ 10 = 2,25x` → `2.200 × 2,25 = **4.950**`

**5) DCF (angka ilustrasi):** FCF stabil Rp3 triliun/tahun, WACC 10%, n = 5 → faktor annuitas `(1 − 1,1^−5) ÷ 0,1 = 3,7908` → `DCF = 3.000 × 3,7908 = Rp11.372 miliar`; + kas Rp1.000 miliar − utang Rp500 miliar = Rp11.872 miliar; ÷ 10 miliar lembar ≈ **Rp1.187/lembar**.

**Varian median (gaya aplikasi):** median dari 4 metode utama = median(4.894, 4.950, 5.653, 6.069) = `(4.950 + 5.653) ÷ 2 = 5.301,5`.

### 7.4 MOS & Sinyal Keputusan (§5)
Karena PTBA *cyclical*, pakai **Equity Growth** (sesuai §6.1) dengan `Target MOS = 50%`:

- `MOS = ((6.069 − 2.600) ÷ 6.069) × 100% ≈ **57,2%**` (≥ target 50% ✓)
- `Harga Beli Maksimal = 6.069 × (1 − 0,50) = **3.034**`
- Harga pasar 2.600 ≤ 3.034 → sinyal **STRONG BUY** (beli bertahap)

Bila memakai varian median 5.301,5: `MOS ≈ 51,0%`, `Harga Beli Maks = 5.301,5 × 0,5 = 2.651` — harga 2.600 masih ≤ 2.651, sinyal tetap **STRONG BUY** (tipis, jadi bertahap).

---

## 8. Kesimpulan & Roadmap Pengembangan
1. **Fase 1**: Data Fetching dari API / Web Scraping (Yahoo Finance / IDX / RTI Data).
2. **Fase 2**: Implementasi Filter & Ranking Scoring otomatis ke dalam Database / DataFrame.
3. **Fase 3**: Eksekusi Multi-Model Valuasi & Perhitungan MOS Otomatis.
4. **Fase 4**: Export Hasil ke Excel / JSON & Dashboard Visualisasi Interaktif.
