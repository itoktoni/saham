# Panduan Komprehensif Rumus Screening dan Evaluasi Kualitas Saham

Proses memilih saham di pasar modal sering kali terjebak dalam spekulasi jangka pendek, pergerakan harga tanpa arah, atau rumor pasar yang menyesatkan. Untuk mencapai konsistensi imbal hasil investasi jangka panjang, seorang investor memerlukan kerangka berpikir analitis yang sistematis untuk menyaring (*screening*) dan mengevaluasi kualitas suatu perusahaan. Sebagaimana ditegaskan oleh investor fundamental Thomas William "Thowilz" Simardjo dalam berbagai kesempatan, senjata utama seorang *value investor* bukanlah rumor atau pergerakan harga harian, melainkan analisis objektif terhadap laporan keuangan dan pemahaman terhadap realitas bisnis.

Dokumen ini menyajikan panduan terstruktur yang menggabungkan formula matematis valuasi, analisis kualitas laporan keuangan, klasifikasi jenis saham, serta konfirmasi pergerakan volume melalui metode *Volume Spread Analysis* (VSA) yang dikembangkan oleh Tom Williams.

---

## 1. Kerangka Berpikir Klasifikasi Saham

Sebelum menerapkan rumus matematika atau rasio valuasi, langkah awal yang paling krusial adalah mengklasifikasikan saham ke dalam kategori bisnis yang tepat. Kesalahan umum investor pemula adalah memperlakukan seluruh saham dengan tolok ukur yang sama. Merujuk pada kerangka kerja klasifikasi Peter Lynch yang diadopsi oleh Thowilz, strategi evaluasi harus disesuaikan dengan karakteristik operasional dan siklus bisnis perusahaan.

Tabel berikut merangkum lima klasifikasi utama saham beserta kriteria evaluasi kritis yang harus diterapkan saat melakukan *screening*:

| Kategori Saham | Karakteristik Utama | Indikator Evaluasi Kritis | Ekspektasi & Strategi Eksekusi |
| :--- | :--- | :--- | :--- |
| **Cyclical (Siklikal)** | Kinerja keuangan sangat bergantung pada harga komoditas atau siklus makro ekonomi. | Masalah pada sisi penawaran (*supply*), tingkat harga komoditas global. | Beli saat kondisi industri berada di puncak pesimisme (*bottom cycle*); jual saat laba melonjak dan valuasi terlihat sangat murah secara parsial. |
| **Stalwarts / Star Wars** | Perusahaan raksasa dengan pertumbuhan stabil namun cenderung lambat. | *Dividen yield* relatif terhadap instrumen bebas risiko (seperti obligasi pemerintah). | Ambil posisi jika estimasi *dividen yield* pesimistis lebih tinggi dibanding imbal hasil obligasi (misal 8–9% vs 6–7%). |
| **Fast Growing (Growth Stock)** | Perusahaan dengan tingkat pertumbuhan laba bersih tinggi (20%–30%+ per tahun). | *Pricing power* dan rencana ekspansi kapasitas (*capital expenditure*). | Evaluasi rasio PEG dan konsistensi margin kotor saat biaya bahan baku melonjak; hindari membayar valuasi yang terlalu eksorbitan. |
| **Turnaround** | Perusahaan yang mengalami penderitaan operasional namun menunjukkan sinyal pemulihan bisnis. | Efisiensi biaya, perbaikan segmen produk, atau restrukturisasi operasional. | Menawarkan potensi *re-rating* valuasi tertinggi saat perusahaan berhasil lepas dari kerugian menuju fase pertumbuhan kembali. |
| **Asset Play** | Perusahaan yang memiliki nilai aset riil jauh melebihi nilai kapitalisasi pasarnya. | Saldo kas murni, kepemilikan properti/tanah, dan alokasi modal manajemen. | Membutuhkan katalis aksi korporasi atau perubahan kebijakan dividen agar nilai intrinsik aset diakui oleh pasar. |

---

## 2. Rumusan Matematis & Rasio Screening Valuasi

Dalam melakukan penyaringan awal (*quantitative screening*), rasio sederhana seperti *Price to Earnings Ratio* (PER) sering kali memberikan hasil yang kurang akurat karena laba bersih akuntansi mudah dipengaruhi oleh pencatatan non-kas. Oleh karena itu, pendekatan screening modern memprioritaskan metrik yang berbasis arus kas dan nilai perusahaan secara menyeluruh (*Enterprise Value*).

### A. Formula Enterprise Value (EV)

*Enterprise Value* mencerminkan total harga akuisisi teoritis suatu perusahaan dengan memperhitungkan seluruh struktur modal, baik ekuitas maupun kewajiban utang, dikurangi dengan kas yang dimiliki.

$$EV = \text{Market Capitalization} + \text{Total Debt} - \text{Cash and Cash Equivalents}$$

Di mana:
- $\text{Market Capitalization} = \text{Harga Saham} \times \text{Jumlah Saham Beredar}$
- $\text{Total Debt} = \text{Seluruh Kewajiban Berbunga (Utang Bank, Obligasi, Utang Finansial Jangka Pendek \& Panjang)}$
- $\text{Cash and Cash Equivalents} = \text{Kas dan Setara Kas Bebas}$

Sebagaimana dijelaskan oleh Thowilz, penggunaan EV jauh lebih adil daripada sekadar Kapitalisasi Pasar karena memperhitungkan beban utang yang harus ditanggung atau kas bebas yang dapat langsung diserap oleh pembeli bisnis.

### B. Rasio EV terhadap Arus Kas Operasional (EV/CFO) dan Arus Kas Bebas (EV/FCF)

Laba bersih pada laporan laba rugi mencakup item non-kas seperti depresiasi, amortisasi, serta penyesuaian nilai wajar. Untuk memastikan perusahaan menghasilkan uang tunai riil dari kegiatan operasinya, EV dibandingkan dengan Arus Kas Operasional (*Cash Flow from Operations* / CFO) atau Arus Kas Bebas (*Free Cash Flow* / FCF).

$$\text{Rasio EV/CFO} = \frac{EV}{\text{Cash Flow from Operations (CFO)}}$$

$$\text{Rasio EV/FCF} = \frac{EV}{\text{Free Cash Flow (FCF)}}$$

Di mana Arus Kas Bebas dihitung sebagai:

$$\text{Free Cash Flow (FCF)} = \text{Cash Flow from Operations (CFO)} - \text{Capital Expenditures (CapEx)}$$

> **Kriteria Screening**: Saham dianggap sangat menarik jika memiliki rasio $\text{EV/CFO}$ atau $\text{EV/FCF}$ yang rendah relatif terhadap rata-rata industri dan tingkat pertumbuhan historisnya, menandakan harga perusahaan dijual murah dibanding kapasitas penciptaan kas riilnya.

### C. Price to Earnings Growth (PEG) Ratio

Untuk menilai apakah *Price to Earnings Ratio* (PER) suatu saham sepadan dengan tingkat pertumbuhannya, digunakan indikator *Price to Earnings Growth* (PEG) Ratio yang diperkenalkan oleh Peter Lynch.

$$\text{PEG Ratio} = \frac{\text{Price to Earnings Ratio (PER)}}{\text{Tingkat Pertumbuhan Laba Bersih (\%)}}$$

Secara matematis, jika suatu perusahaan memiliki PER sebesar 10x dan konsisten menumbuhkan laba bersihnya sebesar 30% per tahun, maka perhitungan PEG Ratio adalah:

$$\text{PEG Ratio} = \frac{10}{30} = 0{,}33$$

> **Kriteria Screening**: 
> - $\text{PEG Ratio} < 1{,}0$: Saham terindikasi *undervalued* relatif terhadap potensi pertumbuhannya.
> - $\text{PEG Ratio} > 1{,}5$: Saham berisiko kemahalan (*overvalued*), di mana ekspektasi pertumbuhan sudah terlalu banyak diantisipasi oleh harga pasar.

### D. Analisis Kritis PER vs. Price to Book Value (PBV)

Dalam evaluasi valuasi, investor sering kali membandingkan PER dan PBV. Berdasarkan penjelasan Thowilz, pemegang saham minoritas di pasar modal sebaiknya tidak terlalu berpatokan pada PBV. Nilai Buku (*Book Value*) mengukur aset bersih perusahaan, namun pemegang saham publik tidak memiliki hak atau kemampuan untuk melikuidasi atau menjual aset fisik tersebut. 

Sebaliknya, PER dan rasio berbasis arus kas mengukur kapasitas operasional bisnis dalam menghasilkan laba dan dividen yang dapat dinikmati secara riil oleh pemegang saham minoritas.

---

## 3. Analisis Kualitas Laporan Keuangan: Membedakan Saham Bagus vs. Jelek

Setelah menyaring saham berdasarkan kriteria kuantitatif awal, langkah berikutnya adalah membedakan perusahaan berkualitas tinggi dari perusahaan yang tampak murah namun menyimpan risiko sistemik (*value trap*).

### A. Prioritas Utama: Utamakan Neraca (Balance Sheet)

Jika seorang investor hanya diperbolehkan membaca satu komponen laporan keuangan, pilihan utama jatuh pada **Neraca (*Balance Sheet*)**. Laporan Laba Rugi kerap diatur atau dimanipulasi dari bawah ke atas melalui pengakuan pendapatan atau penundaan beban, sedangkan Neraca menyimpan kebenaran struktur keuangan perusahaan.

Berikut adalah kriteria eksplisit untuk membedakan saham berkualitas bagus dari saham bermasalah:

#### Indikator Saham Bagus (Quality Indicators):
1. **Struktur Neraca Sehat**: Beban utang berbunga terkendali, rasio kas memadai, dan beban bunga dapat tertutup dengan mudah oleh laba operasional.
2. **Arus Kas Operasional Selaras dengan Laba**: Laba bersih diimbangi oleh arus kas masuk dari aktivitas operasi secara konsisten dari tahun ke tahun.
3. **Memiliki Pricing Power & Operating Leverage**: Perusahaan mampu menaikkan harga jual saat inflasi bahan baku naik tanpa kehilangan pangsa pasar, sehingga margin kotor (*Gross Profit Margin*) tetap stabil atau meningkat.
4. **Alokasi Modal (*Capital Allocation*) Efektif**: Manajemen memanfaatkan kas retained earnings untuk ekspansi kapasitas produktif (*CapEx*) yang menghasilkan imbal hasil tinggi (*Return on Invested Capital*).

#### Tanda-Tanda Saham Jelek & Berisiko (Red Flags):
1. **Laba Semu dengan Utang Membengkak**: Laba bersih tampak tumbuh pada laporan laba rugi, tetapi utang bank/obligasi terus membengkak setiap tahun untuk membiayai operasional, sementara arus kas operasional bernilai negatif.
2. **Valuasi Eksorbitan / Absurd**: Memiliki PER sangat tinggi (misalnya 50x–100x), di mana pertumbuhan laba 30%–50% per tahun selama satu dekade pun tidak cukup untuk mengejar harga valuasinya.
3. **Margin Tergerus Akibat Persaingan**: Perusahaan gagal meneruskan kenaikan biaya input kepada konsumen karena tidak memiliki keunggulan kompetitif.
4. **Alokasi Modal Buruk**: Kas perusahaan diendapkan pada investasi tidak produktif atau digunakan untuk transaksi pihak berelasi yang merugikan pemegang saham minoritas.

---

## 4. Konfirmasi Teknikal Berbasis Volume Spread Analysis (VSA)

Setelah saham memenuhi kriteria fundamental dan valuasi, penentuan waktu transaksi (*timing*) disempurnakan menggunakan metodologi *Volume Spread Analysis* (VSA) yang dikembangkan oleh Tom Williams dalam bukunya *Mastering The Markets* dan *Undeclared Stockmarket Secrets*. VSA menguji hubungan antara tiga variabel utama: **Volume Transaksi**, **Rentang Harga (*Price Spread*)**, dan **Harga Penutupan (*Closing Price*)**.

Tujuannya adalah mengidentifikasi aktivitas pelaku pasar profesional (*Smart Money* atau *Composite Operator*) saat melakukan akumulasi atau distribusi.

### A. Sinyal Kekuatan (Sign of Strength - SOS)

Sinyal SOS mengindikasikan bahwa pasokan saham (*supply*) mulai habis diserap oleh *Smart Money*, menandakan persiapan pergerakan naik (*markup*).

1. **No Selling Pressure / No Supply**:
   - *Karakteristik*: Bar harga turun (*down-bar*) dengan rentang harga sempit (*narrow spread*) dan volume transaksi yang lebih rendah dibanding 2–3 bar sebelumnya.
   - *Interpretasi*: Menunjukkan tidak ada tekanan jual dari pelaku pasar profesional. Pasokan saham telah mengering di area harga tersebut.
2. **Stopping Volume / Absorption**:
   - *Karakteristik*: Bar harga turun tajam dengan volume sangat tinggi (*ultra-high volume*), namun harga ditutup di bagian tengah atau atas rentang bar.
   - *Interpretasi*: Menandakan institusi profesional melakukan pembelian besar-besaran untuk menyerap seluruh aksi jual publik, menghentikan tren penurunan (*markdown*).
3. **Successful Test**:
   - *Karakteristik*: Harga ditekan turun secara cepat mendekati area *support* atau bekas area akumulasi, lalu berbalik naik dan ditutup di dekat level tertinggi dengan volume sangat tipis.
   - *Interpretasi*: Mengonfirmasi bahwa pasokan penjual sudah benar-benar habis di pasar, membuka jalan bagi kenaikan harga tanpa hambatan.

### B. Sinyal Kelemahan (Sign of Weakness - SOW)

Sinyal SOW mengindikasikan bahwa permintaan (*demand*) mulai hilang dan *Smart Money* sedang mengalirkan pasokan saham ke publik (distribusi).

1. **No Demand**:
   - *Karakteristik*: Bar harga naik (*up-bar*) with rentang harga sempit dan volume transaksi yang sangat rendah dibanding bar-bar sebelumnya.
   - *Interpretasi*: Menunjukkan pelaku pasar profesional tidak tertarik untuk mendorong harga lebih tinggi lagi. Kenaikan harga bersifat semu (*trap up-move*).
2. **Upthrust Bar**:
   - *Karakteristik*: Bar harga melonjak naik pada awal sesi dengan rentang lebar dan volume tinggi, tetapi diakhiri dengan penutupan di dekat level terendah bar.
   - *Interpretasi*: Menandakan jebakan pembeli (*buyer's trap*) di mana profesional memanfaatkan antusiasme publik untuk melakukan penjualan massal (*distribution*).

---

## 5. Checklist Eksekusi Keputusan Investasi

Sebelum mengambil keputusan transaksi di pasar modal, berikut adalah empat pilar checklist terpadu yang harus diverifikasi secara berurutan:

1. **Klasifikasi & Tesis Bisnis**:
   - Kategori saham teridentifikasi dengan jelas (Cyclical, Stalwart, Growth, Turnaround, atau Asset Play).
   - Tesis pertumbuhan bisnis logis, mudah dijelaskan, dan didukung oleh data penyebaran produk atau ekspansi kapasitas riil.
   - Manajemen memiliki rekam jejak tata kelola perusahaan (GCG) dan alokasi modal yang transparan.

2. **Valuasi & Screening Kuantitatif**:
   - Rasio $\text{EV/CFO}$ atau $\text{EV/FCF}$ berada di area terdiskon relatif terhadap histori dan industri.
   - Rasio PEG $< 1{,}0$ untuk saham pertumbuhan (*Fast Growing*).
   - Estimasi *Dividen Yield* lebih tinggi dibanding imbal hasil obligasi pemerintah bebas risiko untuk saham kategori *Stalwart*.

3. **Kesehatan Laporan Keuangan**:
   - Neraca (*Balance Sheet*) dalam kondisi sehat dengan tingkat utang berbunga yang terkendali.
   - Arus Kas Operasional bernilai positif dan tumbuh sejalan dengan kenaikan laba bersih.
   - Perusahaan memiliki *pricing power* yang dibuktikan dengan kestabilan margin kotor saat biaya bahan baku naik.

4. **Konfirmasi Timing VSA**:
   - Muncul sinyal kekuataan (*Sign of Strength* / SOS) seperti *No Selling Pressure*, *Stopping Volume*, atau *Test* pada area *support*.
   - Tidak ada sinyal kelemahan utama (*Sign of Weakness* / SOW) seperti *No Demand* atau *Upthrust Bar* di area puncaknya.

### Kriteria Keputusan Jual (Exit Strategy)

Seorang *value investor* harus bersikap rasional dan disiplin dalam mengakhiri posisi investasi. Keputusan jual dieksekusi berdasarkan tiga kondisi utama:
1. **Kerusakan Tesis Bisnis**: Terdapat kesalahan analisis awal atau perubahan fundamental permanen di mana perusahaan tidak lagi mampu tumbuh sesuai perkiraan.
2. **Valuasi Absurd**: Harga saham melejit hingga mencapai level valuasi yang tidak masuk akal (misalnya PER melonjak ke 100x), di mana pertumbuhan kinerja belasan tahun pun tidak mampu mengejar harganya.
3. **Adanya Peluang Alternatif yang Jauh Lebih Menarik**: Ditemukan peluang investasi lain dengan tingkat risiko yang lebih terukur serta potensi imbal hasil (*upside*) yang jauh lebih tinggi.
