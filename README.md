# klinik-Vidia Medika

Website klinik Vidia Medika: halaman utama, profil dokter, artikel kesehatan, login, kebijakan privasi, dan panel admin.

## Isi repo

```
index.html, dokter.html, artikel.html   halaman publik
masuk.html, admin.html                  login dan panel admin
privasi.html                            kebijakan privasi
klinik-site/                            versi Cloudflare Pages
```

## klinik-site

Versi yang jalan di Cloudflare Pages, dengan Pages Functions, Workers KV untuk janji temu dan laporan, serta Workers AI untuk asisten klinik.

```bash
cd klinik-site
npm install
npm run build
npm run dev
```

Deploy pakai `npm run deploy`.
