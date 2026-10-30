# SisaBijak 

# Deskripsi
SisaBijak adalah platform marketplace food rescue berbasis Django yang menghubungkan toko roti dan cafe lokal dengan mahasiswa atau pekerja yang lagi nyari makanan berkualitas dengan harga miring.

# Anggota Kelompok
1. Debora Putri Dion Simamora (2506544126)
2. Jefry Acmal Dzikhrullah (2506614795)
3. Khalisha Nalani Chandra (2506625041)
4. Rafael Darius Sagala (2506584275)
5. Ghaisan Nabil Iradat (2506619051)

# Fitur

### 1. Modul Catalog
**Penanggung Jawab** : Debora Putri Dion Simamora

**Deskripsi Fitur:** 
Modul ini berfungsi sebagai etalase publik tempat pengguna dapat menjelajahi, mencari, dan memfilter berbagai penawaran makanan surplus dari mitra merchant dengan potongan harga khusus. Pengguna dapat melihat detail produk, lokasi toko, serta jadwal pengambilan sebelum melakukan pemesanan. Selain itu, modul ini menyediakan sistem ulasan dan penilaian berbasis rating bintang dari konsumen yang telah menyelesaikan transaksi pesanan.

**Models:**
* **Model Catalog (Review)**
  * `user` : Akun Consumer yang memberikan ulasan
  * `order` : Pesanan berstatus `completed` pada sistem OrderSystem yang sedang diulas (1 pesanan = 1 ulasan)
  * `product` : Paket makanan dari Merchant Product yang diulas
  * `rating` : Nilai angka ulasan yang diberikan dalam skala 1–5
  * `comment` : Isi teks ulasan yang ditulis oleh konsumen
  * `created_at` : Waktu sistem saat ulasan pertama kali dibuat
  * `updated_at` : Waktu sistem saat ulasan terakhir kali diubah

**Views (Method):**
* `catalog_list_view()` : Menampilkan halaman katalog berisi daftar produk Merchant Product yang berstatus Available
  * Auth: Guest, Consumer, Merchant, Admin
* `get_catalog_json()` : Endpoint API untuk pencarian nama produk dan filter harga diskon
  * Auth: Guest, Consumer, Merchant, Admin
* `catalog_detail_view()` : Menampilkan detail produk, daftar ulasan, dan tombol "Klaim"
  * Auth: Guest, Consumer, Merchant, Admin
* `get_reviews_json()` : Endpoint API untuk memuat daftar ulasan dan rata-rata rating suatu produk
  * Auth: Guest, Consumer, Merchant, Admin
* `review_create_view()` : Membuat ulasan baru khusus untuk pesanan yang sudah selesai
  * Auth: Consumer
* `review_update_view()` : Mengubah isi ulasan yang sudah dibuat
  * Auth: Consumer
* `review_delete_view()` : Menghapus ulasan dari sistem
  * Auth: Consumer

**Templates:**
* `catalog.html` : Halaman utama katalog dengan fitur pencarian dan daftar produk
* `catalog_detail.html` : Halaman detail produk tunggal beserta ulasan dan tombol "Klaim"
* `review_form.html` : Formulir antarmuka untuk penambahan atau pengubahan ulasan

---

### 2. Modul Merchant Product
**Penanggung Jawab** : Jefry Acmal Dzikhrullah

**Deskripsi Fitur:**
Modul ini memfasilitasi merchant untuk mengelola inventaris makanan surplus yang siap dijual kepada konsumen melalui dasbor khusus. Merchant dapat menambahkan produk baru, mengatur stok harian, menetapkan harga asli dan diskon, serta menentukan jadwal penjemputan (pickup schedule). Selain itu, merchant dapat memperbarui rincian produk, mengunggah foto makanan, maupun menonaktifkan produk yang sudah tidak tersedia.

**Models:**
* **Model MerchantProduct**
  * `product_id` : String id unik yang dimiliki setiap produk
  * `product_name` : Nama produk yang diunggah merchant
  * `product_stock` : Jumlah produk yang diunggah merchant
  * `product_status` : Available / Sold Out / Inactive
  * `real_price` : Harga asli produk yang diunggah merchant
  * `discount_price` : Besaran diskon yang diunggah merchant
  * `start_pickup` : Waktu produk bisa di-pickup (waktu rilis)
  * `end_pickup` : Waktu produk sudah tidak bisa di-pickup (waktu stop)
  * `product_photo` : FileField, berkas gambar/foto produk yang diunggah merchant

**Views (Method):**
* `product_view()` : View product yang diunggah merchant
  * Auth: Merchant
* `product_create()` : Create product oleh merchant
  * Auth: Merchant
* `product_update()` : Edit product yang diunggah merchant
  * Auth: Merchant
* `product_delete` : Delete product yang diunggah merchant
  * Auth: Merchant

**Templates:**
* `product_form.html` : Formulir untuk menambah atau mengedit produk merchant
* `merchant_dashboard.html` : Halaman dasbor merchant untuk mengelola daftar produk

---

### 3. Modul Order System
**Penanggung Jawab** : Rafael Darius Sagala

**Deskripsi Fitur:**
Modul ini mengatur alur transaksi pemesanan makanan mulai dari proses checkout keranjang oleh konsumen hingga pembuatan kode QR pembayaran (SisaBayarQR). Setelah pembayaran diverifikasi, sistem menerbitkan kode klaim unik dan QR Code klaim yang dapat ditukarkan konsumen langsung di kasir toko. Kasir merchant selanjutnya memvalidasi QR Code tersebut untuk menyelesaikan pesanan sekaligus mencatat pendapatan ke saldo merchant yang dapat dicairkan (disbursement).

**Models:**
* **Model OrderSystem**
  * `consumer` : Berelasi dengan model User Consumer
  * `product` : Berelasi dengan model Merchant Product yang dipesan oleh konsumen
  * `quantity` : Jumlah produk yang dipesan ke dalam keranjang
  * `unit_price` : Harga produk saat dipesan
  * `total_price` : Total tagihan konsumen
  * `payment_status` : Status pembayaran (misalnya: pending, paid, completed, expired)
  * `payment_qr_id` : ID unik yang disematkan ke dalam SisaBayarQR (Dummy QRIS)
  * `claim_qr_code` : Kode unik khusus untuk proses penukaran makanan di lokasi
  * `pickup_deadline` : Batas waktu konsumen untuk mengambil pesanan
  * `created_at` : Waktu pencatatan pesanan
* **Model MerchantWallet**
  * `merchant` : ForeignKey(User), merchant pemilik dompet saldo penjualan
  * `balance` : DecimalField, total akumulasi saldo hasil klaim pesanan yang siap dicairkan
  * `updated_at` : DateTimeField, waktu pembaruan saldo terakhir

**Views (Method):**
* `checkout_view()` : Memproses pembayaran keranjang dan men-generate SisaBayarQR
  * Auth: Consumer
* `payment_view()` : Menampilkan halaman rincian instruksi pembayaran SisaBayarQR
  * Auth: Consumer
* `payment_status_view()` : Endpoint API JSON untuk pengecekan status pembayaran pesanan secara otomatis (polling)
  * Auth: Consumer
* `simulator_bayar_view()` : Membaca unggahan gambar SisaBayarQR dan mengubah status pembayaran menjadi lunas agar sistem mengeluarkan QR Code klaim
  * Auth: Consumer, Admin
* `order_list_view()` : Menampilkan riwayat pesanan milik konsumen
  * Auth: Consumer
* `merchant_order_list_view()` : Menampilkan daftar pesanan yang harus diselesaikan oleh merchant
  * Auth: Merchant
* `validate_claim_view()` : Sistem memvalidasi kecocokan QR Code klaim yang diserahkan konsumen kepada kasir
  * Auth: Merchant
* `withdraw_funds_view()` : Memproses merchant yang mengajukan pencairan dana penjualan ke SisaBijak
  * Auth: Merchant, Admin

**Templates:**
* `checkout_payment.html` : Halaman konfirmasi pembayaran yang menampilkan SisaBayarQR (Dummy QRIS)
* `simulator_bayar.html` : Halaman web rahasia untuk mengunggah gambar SisaBayarQR
* `order_list.html` : Halaman yang memuat QR Code klaim dan riwayat pesanan konsumen
* `merchant_orders.html` : Halaman dasbor untuk melihat pesanan masuk di sisi merchant
* `validate_claim.html` : Halaman bagi kasir merchant untuk memproses dan menyelesaikan pesanan

---

### 4. Modul Consumer Profile
**Penanggung Jawab** : Khalisha Nalani Chandra

**Deskripsi Fitur:**
Modul ini menyediakan dasbor personal bagi konsumen untuk memantau ringkasan aktivitas transaksi yang telah dilakukan. Selain itu, modul ini juga memfasilitasi konsumen untuk mengelola data akun pribadi, memperbarui nomor kontak, dan memperbarui password akun.

**Models:**
* **Model ConsumerProfile**
  * `user` : Akun Consumer pemilik profil ini
  * `phone_number` : Nomor telepon akun konsumen
  * `total_orders_completed` : Jumlah total pesanan yang sudah berhasil diselesaikan konsumen
  * `total_money_saved` : Total akumulasi uang yang dihemat (selisih harga asli dan diskon)
  * `total_co2_prevented` : Total akumulasi gas emisi karbon yang berhasil dicegah dari makanan sisa

**Views (Method):**
* `consumer_dashboard_view()` : Menampilkan halaman utama profil beserta statistik uang dihemat dan emisi karbon yang dicegah
  * Auth: Consumer
* `edit_profile_view()` : Menampilkan form bagi konsumen untuk mengubah nomor telepon atau sandi
  * Auth: Consumer
* `order_history_view()` : Menampilkan seluruh riwayat pesanan (termasuk yang menunggu pembayaran, lunas/siap klaim, dan selesai)
  * Auth: Consumer

**Templates:**
* `consumer_dashboard_view.html` (`consumer_dashboard.html`) : Halaman profil utama yang memuat statistik akun
* `edit_profile_view.html` (`edit_profile.html`) : Formulir untuk mengedit data diri
* `order_history_view.html` (`order_history.html`) : Halaman riwayat pesanan tempat pengguna bisa melihat SisaBayarQR atau QR Klaim

---

### 5. Modul Merchant Location Integrator
**Penanggung Jawab** : Ghaisan Nabil Iradat

**Deskripsi Fitur:**
Modul ini menyajikan peta interaktif untuk membantu konsumen menemukan lokasi restoran, kafe, dan toko roti mitra SisaBijak terdekat secara visual. Pengguna dapat mencari merchant berdasarkan nama toko atau kata kunci alamat serta mengecek titik koordinat lokasi secara presisi. Integrasi ini memudahkan konsumen dalam merencanakan rute penjemputan makanan surplus secara langsung ke gerai merchant.

**Models:**
* **Model MerchantLocationIntegrator**
  * `id_merchant` : String id unik yang dimiliki setiap merchant
  * `name_merchant` : String nama merchant
  * `address` : String alamat merchant
  * `longitude` : Koordinat bujur merchant
  * `latitude` : Koordinat lintang merchant

**Views (Method):**
* `merchant_location()` : Mengambil data untuk rendering
  * Auth: Guest, Consumer, Merchant, Admin

**Template:**
* `merchant_loc.html` : Halaman integrasi lokasi peta interaktif merchant

---

### 6. Modul Authentication & Authorization
**Penanggung Jawab** : Jefry Acmal Dzikhrullah

**Deskripsi Fitur:**
Modul ini menangani sistem pendaftaran akun, autentikasi masuk, dan manajemen sesi login pengguna secara aman. Otorisasi diterapkan berbasis peran (role-based access control) untuk membedakan hak akses dan fungsi antara Guest, Consumer, Merchant, dan Admin. Setiap pengguna diarahkan secara otomatis ke alur kerja dan antarmuka yang sesuai dengan hak akses perannya di dalam platform.

**Models:**
* **Model UserProfile**
  * `user` : OneToOneField(User), relasi satu-ke-satu ke model bawaan Django User
  * `role` : CharField, peran pengguna (`consumer` atau `merchant`)
* **Base Roles:**
  * `Guest` : AnonymousUser
  * `Consumer` : Akun consumer, self register via web
  * `Merchant` : Akun merchant, register manual by contact Admin
  * `Admin` : SuperUser

**Views (Method):**
* `register()` : Registrasi akun baru untuk pengguna bertipe Consumer
  * Auth: Guest
* `login_user()` : Autentikasi dan login ke dalam sistem
  * Auth: Guest, Consumer, Merchant, Admin
* `logout_user()` : Mengakhiri sesi login pengguna
  * Auth: Consumer, Merchant, Admin
* `profile()` / `account_profile_view()` : Mengarahkan pengguna ke halaman profil sesuai peran akun
  * Auth: Consumer, Merchant, Admin

**Templates:**
* `register.html` : Formulir pendaftaran akun consumer baru
* `login.html` : Formulir masuk ke dalam sistem
* `logout.html` : Halaman konfirmasi / redirect keluar akun
* `profile.html` : Halaman profil pengguna / akun

---

### 7. Modul Landing Page & Base Platform
**Penanggung Jawab** : Ghaisan Nabil Iradat

**Deskripsi Fitur:**
Modul ini berfungsi sebagai gerbang utama platform SisaBijak. Halaman ini menyajikan penawaran makanan surplus harian (daily deals) dengan diskon terbesar serta cuplikan peta gerai mitra terdekat. Selain itu, modul ini menyediakan kerangka tata letak (base layout) dan navigasi sesuai dengan role pengguna.

**Models:**
* Mengintegrasikan data dari:
  * `MerchantProduct` : Mengambil produk berstatus *Available* dengan potongan harga tertinggi untuk ditampilkan pada section *daily deals*.
  * `MerchantLocationIntegrator` : Mengambil data koordinat dan alamat toko mitra untuk ditampilkan pada peta interaktif Leaflet.

**Views (Method):**
* `show_main()` : Menyiapkan dan menampilkan halaman utama landing page lengkap dengan daftar deals surplus, statistik ticker, dan data merchant terdekat
  * Auth: Guest, Consumer, Merchant, Admin

**Templates:**
* `index.html` : Halaman depan / landing page interaktif SisaBijak
* `base.html` : Kerangka layout dasar (navbar adaptif sesuai role pengguna, area pesan notifikasi/flash, dan footer)

---

# Roles
- `Guest` : AnonymousUser
- `Consumer` : Akun consumer, self register via web
- `Merchant` : Akun merchant, register manual by contact Admin
- `Admin` : SuperUser

# Pembagian Job Desk
- `Project Manager`: Jefry Acmal Dzikhrullah
- `Modul Catalog` : Debora Putri Dion Simamora
- `Seeding data merchant & product` : Debora Putri Dion Simamora
- `Modul Order System` : Rafael Darius Sagala
- `Dummy Payment Gateway` : Rafael Darius Sagala
- `Modul Merchant Product` : Jefry Acmal Dzikhrullah
- `Authentication & Authorization` : Jefry Acmal Dzikhrullah
- `Modul Merchant Location Integrator` : Ghaisan Nabil Iradat
- `Landing Page & Base Platform` : Ghaisan Nabil Iradat
- `Modul Consumer Profile` : Khalisha Nalani Chandra
- `Web Design Coordinator` : Khalisha Nalani Chandra