# 📱 SisaBijak Flutter — Navigasi Antar Halaman

## 🔵 GUEST

| Modul | Halaman | Button | Ke Halaman |
|---|---|---|---|
| **Landing Page** | Landing Page | Login | Login |
| | | Daftar / Register | Register |
| | | Klik kartu produk | Detail Produk (read-only) |
| | | Lihat Semua Produk | Katalog (read-only) |
| **Authentication** | Login | Login ✅ | Beranda (sesuai role) |
| | | Belum punya akun? Daftar | Register |
| | Register | Daftar ✅ | Login |
| | | Sudah punya akun? Login | Login |

---

## 🟢 CONSUMER — Bottom Nav: `Beranda · Katalog · Pesanan · Profil`

| Modul | Halaman | Button | Ke Halaman |
|---|---|---|---|
| **Landing Page** | Beranda | Klik kartu daily deal | Detail Produk |
| | | Lihat Semua → | Katalog |
| | | Buka Peta | Peta Merchant |
| **Catalog** | Katalog | Search bar / filter chip | (reload Katalog) |
| | | Klik kartu produk | Detail Produk |
| | Detail Produk | Pesan Sekarang | Keranjang |
| | | Tulis Review *(jika eligible)* | (bottom sheet form) |
| | | Hapus Review *(milik sendiri)* | (dialog konfirmasi, reload) |
| **Order System** | Keranjang | ➕ ➖ qty / Hapus item | (reload Keranjang) |
| | | Checkout ✅ | Halaman Pembayaran |
| | | ← Kembali | Katalog |
| | Halaman Pembayaran | Polling otomatis saat lunas → | Pesanan Saya |
| | | ← Batalkan | Keranjang |
| | Pesanan Saya | Tab Aktif / Riwayat | (switch tab) |
| | | Klik pesanan PAID → lihat QR Klaim | (bottom sheet QR) |
| | | Klik pesanan COMPLETED → review | Detail Produk |
| **Consumer Profile** | Profil Consumer | Edit Profil | Edit Profil |
| | | Logout | Landing Page |
| | Edit Profil | Simpan Profil ✅ | Profil Consumer |
| | | Ubah Password ✅ | Profil Consumer |
| | | ← Kembali | Profil Consumer |
| **Merchant Location** | Peta Merchant | Tap marker | (bottom sheet info merchant) |
| | | Search nama / alamat | (reload peta) |
| | | ← Kembali | Beranda |

---

## 🟠 MERCHANT — Bottom Nav: `Produk Saya · Pesanan Masuk · Profil`

| Modul | Halaman | Button | Ke Halaman |
|---|---|---|---|
| **Merchant Product** | Produk Saya | ＋ Tambah Produk (FAB) | Form Tambah Produk |
| | | Tap produk → Edit | Form Edit Produk |
| | | Tap produk → Hapus | (dialog konfirmasi, reload) |
| | Form Tambah Produk | Simpan ✅ | Produk Saya |
| | | ← Batal | Produk Saya |
| | Form Edit Produk | Simpan ✅ | Produk Saya |
| | | ← Batal | Produk Saya |
| **Order System** | Pesanan Masuk | Tab Incoming / History | (switch tab) |
| | | Tap pesanan → detail | (expand / bottom sheet) |
| | | Scan / Validasi QR Klaim | Halaman Validasi QR |
| | | Cairkan Saldo ✅ | (dialog konfirmasi, reload) |
| | Halaman Validasi QR | Buka Kamera Scanner | (kamera scan QR) |
| | | Konfirmasi Klaim ✅ | Pesanan Masuk |
| | | ← Kembali | Pesanan Masuk |
| **Authentication** | Profil Merchant | Logout | Landing Page |

---

## 🔴 ADMIN — Bottom Nav: `Simulator Bayar · Profil`

| Modul | Halaman | Button | Ke Halaman |
|---|---|---|---|
| **Order System** | Simulator Bayar | Upload gambar QR → Scan ✅ | (preview detail di halaman yang sama) |
| | | Konfirmasi Bayar ✅ | (reload Simulator, sukses) |
| **Authentication** | Profil Admin | Logout | Landing Page |
