# DHealth di klinik.xianzing.my.id

Situs DHealth versi publik untuk Cloudflare Pages: halaman statis + Pages Functions untuk Asisten AI (Cloudflare Workers AI, gratis), penyimpanan janji/laporan bug/permintaan demo (Workers KV), dan login petugas.

## Isi folder

| Path | Fungsi |
|---|---|
| `public/` | Halaman situs (`index.html`, `artikel.html`, `dokter.html`, `admin.html`), foto, dan `dh-runtime.js` |
| `public/dh-runtime.js` | Penghubung halaman ke server: asisten, database, unduhan tiket, login petugas |
| `functions/api/chat.js` | `POST /api/chat` — Asisten AI lewat Workers AI (model SEA-LION v4 27B, fasih bahasa Indonesia; aturan dipaksa di server) |
| `functions/api/data.js` | `GET/PUT /api/data` — data form di KV. Pengunjung hanya bisa membaca/menulis datanya sendiri; daftar semua data khusus petugas |
| `functions/api/staff.js` | `POST /api/staff` — tukar kata sandi petugas dengan token |
| `tools/gen_admin.py` | Membuat `admin.html` (Dasbor Klinik di `/admin`) dari gaya dan data dokter beranda |
| `tools/build.py` | Menyalin halaman terbaru dari folder artifact (satu tingkat di atas) ke `public/` |
| `wrangler.toml` | Konfigurasi Pages + binding KV `DH_KV` + binding Workers AI `AI` |

## Deploy pertama kali

Jalankan dari folder ini.

1. Login ke akun Cloudflare Anda (membuka browser):
   ```bash
   npx wrangler login
   ```
2. Buat penyimpanan KV, lalu salin `id` yang muncul ke `wrangler.toml` (ganti `PASTE_KV_NAMESPACE_ID_HERE`):
   ```bash
   npx wrangler kv namespace create DH_KV
   ```
3. Buat proyek Pages:
   ```bash
   npx wrangler pages project create devhealth-klinik --production-branch main
   ```
4. Simpan kata sandi petugas (kata sandi baru buatan Anda; diketik di terminal, tidak disimpan di file):
   ```bash
   npx wrangler pages secret put STAFF_PASSWORD --project-name devhealth-klinik
   ```
   Asisten AI tidak butuh API key: Workers AI sudah termasuk akun Cloudflare dengan jatah gratis 10.000 neuron per hari. Bila jatah habis, asisten otomatis memakai jawaban topik tetap sampai jatah reset.
5. Deploy:
   ```bash
   npm run deploy
   ```
6. Pasang subdomain: Cloudflare Dashboard → **Workers & Pages** → `devhealth-klinik` → **Custom domains** → **Set up a custom domain** → `klinik.xianzing.my.id`. Karena `xianzing.my.id` sudah di Cloudflare, record DNS dibuat otomatis. HTTPS aktif dalam beberapa menit.

## Memperbarui situs

Setelah halaman diubah di artifact:
```bash
npm run build
```
```bash
npm run deploy
```

## Petugas klinik (admin & dokter)

- Buka **https://klinik.xianzing.my.id/admin**, isi kata sandi petugas (`STAFF_PASSWORD`). Di sana ada semua janji pasien, jadwal per dokter, permintaan demo, dan laporan bug.
- Halaman publik tidak punya tautan atau kotak kata sandi petugas sama sekali; alamat `/admin` hanya dibagikan ke admin dan dokter.
- Keluar: tombol **Keluar** di kanan atas `/admin`.
- Mengganti `STAFF_PASSWORD` membuat semua petugas otomatis keluar.

## Uji lokal

`.dev.vars` berisi kata sandi petugas untuk uji lokal saja (tidak ikut deploy). Asisten di uji lokal tetap memanggil Workers AI di akun Anda (memakai jatah gratis).
```bash
npm run dev
```

## Batasan yang perlu diketahui

- "Akun" pengunjung adalah ID acak per browser. Janji yang dibuat di satu HP tidak terlihat di perangkat lain, dan hilang bila data browser dihapus.
- Data diperbarui tiap 20 detik di Dasbor Klinik (tidak real-time).
- Batas pemakaian: 8 pertanyaan asisten per menit dan 5 percobaan login per menit per alamat IP.
- Jatah gratis Workers AI 10.000 neuron per hari (cukup untuk ratusan pertanyaan pendek). Di atas itu perlu paket Workers Paid.
