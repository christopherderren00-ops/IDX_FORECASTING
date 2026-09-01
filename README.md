# IDX Forecast Data Pipeline

Script ini menarik harga historis harian & data fundamental **asli** dari
Yahoo Finance untuk saham-saham IDX, lalu mengekspornya ke `data/latest.json`
— format yang langsung bisa dibaca oleh dashboard
`stock-forecast-dashboard.jsx`.

Perhitungan SMA, EMA, RSI, MACD, dan proyeksi tren tetap dilakukan **di
dashboard** (client-side, dari data harga mentah). Script ini hanya
tanggung jawab untuk menyediakan data harga & fundamental.

---

## 1. Jalankan sekali secara manual (test lokal)

```bash
pip install -r requirements.txt
python scripts/fetch_idx_data.py
```

Kalau berhasil, kamu akan lihat `data/latest.json` berisi data 5 saham
(BBCA, BBRI, TLKM, ASII, GOTO). Tambah/kurangi ticker di
`TICKERS` dalam `scripts/fetch_idx_data.py` — cukup pakai kode saham + akhiran
`.JK` (kode Yahoo Finance untuk bursa Indonesia).

---

## 2. Pilih cara menjalankannya otomatis tiap hari

### Opsi A (direkomendasikan, gratis, tanpa server) — GitHub Actions

Ini yang membuat dashboard React (yang jalan di browser) bisa membaca data
asli tanpa kamu perlu menghosting backend sendiri:

1. Push folder ini ke repo GitHub baru (boleh publik atau private,
   asal repo publik supaya `raw.githubusercontent.com` bisa diakses
   tanpa autentikasi — untuk repo private butuh token, lebih rumit).
   ```bash
   git init
   git add .
   git commit -m "init: idx forecast pipeline"
   git branch -M main
   git remote add origin https://github.com/<username>/<repo>.git
   git push -u origin main
   ```
2. Workflow `.github/workflows/update-data.yml` sudah dikonfigurasi untuk
   jalan otomatis **setiap hari kerja jam 16:30 WIB** (30 menit setelah
   bursa tutup), dan bisa juga dipicu manual lewat tab **Actions → Update
   IDX stock data → Run workflow**.
3. Setelah workflow jalan minimal sekali, data asli akan tersedia di:
   ```
   https://raw.githubusercontent.com/<username>/<repo>/main/data/latest.json
   ```
4. Buka `stock-forecast-dashboard.jsx`, cari baris:
   ```js
   const LIVE_DATA_URL = "";
   ```
   Ganti dengan URL di atas. Dashboard akan otomatis fetch data ini setiap
   dibuka, dan ada tombol **Refresh** untuk fetch ulang kapan saja.

Catatan: repo GitHub *tidak perlu* selalu terbuka/running — GitHub Actions
yang menjalankan cron-nya di infrastruktur GitHub, gratis untuk repo publik
(2.000 menit/bulan untuk repo private, lebih dari cukup untuk job sesingkat
ini).

### Opsi B — VPS / server sendiri dengan cron

Kalau kamu punya VPS (DigitalOcean, AWS EC2, dll):

```bash
git clone https://github.com/<username>/<repo>.git
cd <repo>
pip install -r requirements.txt
crontab -e
```

Tambahkan baris berikut (jalan tiap hari kerja jam 16:30 WIB / 09:30 UTC —
sesuaikan `TZ` server kamu):

```
30 16 * * 1-5 cd /path/to/repo && /usr/bin/python3 scripts/fetch_idx_data.py >> logs/fetch.log 2>&1
```

Lalu serve `data/latest.json` lewat web server (nginx/Caddy) atau upload
otomatis ke storage yang punya CORS (S3 + CloudFront, Cloudflare R2, dll),
dan pakai URL itu sebagai `LIVE_DATA_URL`.

### Opsi C — Replit

1. Import repo ini ke Replit.
2. Buka tab **Scheduled Deployments** (fitur bawaan Replit) → set jadwal
   harian → command: `python scripts/fetch_idx_data.py`.
3. Aktifkan **hosting statis** untuk folder `data/` (atau pakai Replit DB /
   object storage) supaya `latest.json` bisa diakses via URL publik dengan
   CORS aktif, lalu pakai URL itu di `LIVE_DATA_URL`.

---

## 3. Batasan yang perlu kamu tahu

- **Orderbook tetap simulasi** di dashboard, walau harga sudah live —
  data orderbook (bid/ask real-time) adalah data proprietary broker,
  bukan data publik gratis. Untuk orderbook asli kamu butuh akses resmi
  ke data feed broker/IDX (lihat opsi seperti ICE Consolidated Feed,
  iTick, atau Invezgo yang disebut di riset sebelumnya — semuanya
  berbayar/butuh pendaftaran).
- **Data fundamental dari Yahoo Finance untuk saham IDX kadang tidak
  lengkap** (beberapa field bisa `null`) — dashboard sudah dibuat untuk
  menampilkan "N/A" pada field yang kosong daripada error.
- Yahoo Finance adalah endpoint tidak resmi (dipakai lewat library
  `yfinance`), jadi sewaktu-waktu strukturnya bisa berubah dan butuh
  update library. Untuk kebutuhan produksi/serius, pertimbangkan provider
  berbayar resmi.
