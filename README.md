# PBP-Project

# Deskripsi
SisaBijak adalah platform marketplace food rescue berbasis Django yang menghubungkan toko roti dan cafe lokal dengan mahasiswa atau pekerja yang lagi nyari makanan berkualitas dengan harga miring.

# Anggota Kelompok
1. Debora Putri Dion Simamora (2506544126)
2. Jefry Acmal Dzikhrullah  (2506614795)
3. Khalisha Nalani Chandra (2506625041)
4. Rafael Darius Sagala (2506584275)
5. Ghaisan Nabil Iradat (2506619051)

# Fitur
### 1. Modul Mystery Box Marketplace & Catalog
**Penanggung Jawab** : Debora Putri Dion Simamora

**Deskripsi Fitur:** Katalog tempat pembeli (mahasiswa/pekerja) bisa ngeliat, nyari, dan milih paket Mystery Box dari resto/cafe yang lagi diskon gede (50-70%) pas mau tutup toko, lengkap dengan ulasan dari pembeli yang udah ngambil pesanannya.

**Models:**
- Review
  * user : ForeignKey(User), consumer yang memberi ulasan
  * order : OneToOneField(OrderSystem), pesanan berstatus `completed` yang diulas (1 pesanan = 1 ulasan)
  * product : ForeignKey(MerchantProduct), produk Mystery Box yang diulas
  * rating : PositiveSmallIntegerField, nilai 1-5
  * comment : TextField, isi ulasan
  * created_at : DateTimeField, waktu ulasan dibuat
  * updated_at : DateTimeField, waktu ulasan terakhir diubah

**Views:**
*Guest / Consumer*
- catalog_list_view(request) : menampilkan halaman katalog berisi `MerchantProduct` berstatus `Available` dan stok > 0, diurutkan dari diskon terbesar
- get_catalog_json(request) : endpoint JSON untuk search `product_name` / nama toko dan filter `discount_price` (dipanggil via AJAX)
- catalog_detail_view(request, product_id) : detail produk (harga asli vs diskon, `product_stock`, jam pickup, alamat), daftar ulasan, dan tombol "Klaim"
- get_reviews_json(request, product_id) : endpoint JSON daftar ulasan dan rata-rata rating suatu produk

*Consumer*
- review_create_view(request, product_id) : membuat ulasan dari pesanan `completed` milik sendiri yang belum diulas (via AJAX)
- review_update_view(request, pk) : mengubah ulasan milik sendiri
- review_delete_view(request, pk) : menghapus ulasan milik sendiri (via AJAX)

**Aturan Validasi:**
- Katalog hanya menampilkan produk dengan status `Available` dan `product_stock` > 0
- Produk `Sold Out` / `Inactive` tetap bisa dibuka lewat link, tapi tombol "Klaim" diganti "Sold Out"
- Guest bisa melihat katalog dan ulasan, tapi harus login untuk klaim dan menulis ulasan
- Ulasan hanya bisa dibuat dari `OrderSystem` milik sendiri yang berstatus `completed`, dan satu pesanan hanya bisa diulas satu kali
- Consumer hanya bisa mengubah dan menghapus ulasannya sendiri

**Templates:**
- catalog.html : halaman katalog dengan search bar, filter harga, dan grid kartu produk
- catalog_detail.html : halaman detail produk beserta ulasan, form ulasan, dan tombol "Klaim"
- review_form.html : halaman edit ulasan

**Data Awal:**
- `python manage.py seed_catalog` : mengisi 50 produk Mystery Box beserta akun merchant-nya dari `catalog/data/paket_dummy.json`

**Integrasi Antar Modul:**
- Merchant Product : membaca `product_name`, `real_price`, `discount_rate` / `discount_price`, `product_stock`, `product_status`, `start_pickup`, `end_pickup`, `merchant_name`, dan `pickup_address`
- Order System : `Review` terhubung ke `OrderSystem` berstatus `completed`, dan tombol "Klaim" mengarah ke `main:checkout_product`
- Authentication : halaman yang butuh login diarahkan ke `main:login`
- Template dasar : semua halaman catalog memakai `base.html`

### 2. Modul Merchant Inventory & Pickup Manager
**Penanggung Jawab** : Jefry Acmal Dzikhrullah

**Models:**
* Merchant Inventory

  * id_inventory
  * restaurant_id
  * nama_produk
  * stok_harian
  * harga_asli
  * harga_diskon

* Pickup Manager
  * jam_mulai_pickup
  * jam_selesai_pickup
  * status (tersedia, habis, nonaktif)
  * created_at

**Views:**

* inventory_list_view() : menampilkan daftar stok sisa harian pada dashboard merchant
* inventory_create_view() : form bagi merchant untuk menginput stok/paket makanan baru
* update_inventory_view() : update jumlah stok, harga diskon, atau batas jam penjemputan
* delete_inventory_view() : menghapus atau menonaktifkan paket makanan yang sudah tidak relevan

**Templates:**

* inventory_list.html
* inventory_form.html
* merchant_dashboard.html 

### 3. Modul Order Validation & Claim System

**Penanggung Jawab** : Rafael Darius Sagala

**Deskripsi Fitur:**
Sistem pesanan yang bakal ngeluarin kode unik/QR Code buat ditunjukin ke kasir toko pas pembeli ngambil makanannya di lokasi.

**Models:**
* Order
  * consumer : ForeignKey(User), pembeli yang melakukan klaim
  * inventory : ForeignKey(MerchantInventory), paket Mystery Box yang diklaim
  * quantity : PositiveIntegerField, jumlah paket
  * unit_price : DecimalField, snapshot harga diskon saat pesanan dibuat
  * total_price : DecimalField, unit_price × quantity
  * claim_code : CharField (unique), kode klaim 8 karakter yang dibuat otomatis
  * status : CharField, pilihan `pending`, `completed`, `cancelled`, `expired`
  * pickup_deadline : DateTimeField, batas waktu penjemputan (dari jam selesai pickup paket)
  * created_at : DateTimeField, waktu pesanan dibuat
  * picked_up_at : DateTimeField, waktu pesanan divalidasi kasir
  * validated_by : ForeignKey(User, null=True), akun Restaurant yang memvalidasi

**Views:**
*Consumer*
* claim_create_view(request, inventory_id) : konfirmasi dan pembuatan pesanan, dengan pengurangan stok atomik
* order_list_view(request) : daftar riwayat pesanan milik consumer
* order_detail_view(request, pk) : detail pesanan beserta QR Code dan kode klaim
* order_cancel_view(request, pk) : membatalkan pesanan `pending` dan mengembalikan stok

*Restaurant / Kasir*
* merchant_order_list_view(request) : daftar pesanan masuk (menunggu diambil) dan riwayat toko
* validate_order_view(request) : input kode atau scan QR, tampilkan detail pesanan, lalu konfirmasi pengambilan

**Aturan Validasi:**
* Satu kode hanya bisa divalidasi satu kali
* Restaurant hanya bisa memvalidasi pesanan untuk paket miliknya sendiri
* Pesanan yang melewati `pickup_deadline` ditolak dan berstatus `expired`
* Stok dan status paket (`tersedia` / `habis`) ikut diperbarui saat klaim dan pembatalan

**Templates:**
* claim_form.html : halaman konfirmasi klaim Mystery Box
* order_list.html : riwayat pesanan consumer
* order_detail.html : detail pesanan dengan QR Code dan kode klaim
* merchant_orders.html : dashboard pesanan masuk untuk Restaurant
* validate_order.html : halaman validasi kode/QR untuk kasir

**Integrasi Antar Modul:**
* Modul Marketplace & Catalog : tombol "Klaim" mengarah ke `main:checkout_product`
* Modul Merchant Inventory : membaca dan memperbarui `stok_harian` serta status paket
* Modul Impact Analytics : `Order` dipakai sebagai relasi `ImpactLog`, dan signal `order_completed` dikirim saat pesanan divalidasi

### 4. Modul Carbon & Food Rescue Impact Analytics

**Penanggung Jawab** : Khalisha Nalani Chandra

**Deskripsi Fitur:**
Interactive Gamified Analytics Dashboard & Eco-Impact Tracker untuk memvisualisasikan statistik penyelamatan makanan, mengkalkulasi milestone badges (gamifikasi), dan menampilkan estimasi pengurangan emisi CO₂ secara real-time (via AJAX / External API).

**Models:**
* UserEcoProfile
  * user : OneToOneField(User), terhubung ke Consumer / Restaurant / Admin
  * rescue_streak : IntegerField, jumlah hari berturut-turut melakukan aksi rescue
  * eco_points : IntegerField, poin gamifikasi yang dikumpulkan pengguna
  * sustainability_tier : CharField, level/gelar pengguna (misal: 'Eco Seed', 'Food Savior', 'Planet Hero')

* ImpactLog
  * user : ForeignKey(User), pengguna yang melakukan aksi penyelamatan makanan
  * order : ForeignKey(Order, null=True), relasi ke transaksi Mystery Box yang berhasil diselamatkan
  * weight_saved_kg : DecimalField, berat total makanan yang diselamatkan (kg)
  * co2_prevented_kg : DecimalField, hasil kalkulasi reduksi emisi CO₂
  * tree_equivalent : FloatField, metrik ekivalensi dampak (misal: setara menanam X pohon)
  * created_at : DateTimeField, catatan waktu transaksi/aksi

**Views & Endpoints:**

* render_impact_hub(request) : menampilkan halaman utama dashboard analitik interaktif berisi visualisasi grafik, progres streak pengguna, dan lencana pencapaian (badges)
* get_community_impact_stats_json(request) : endpoint JSON publik untuk data agregat komunitas secara real-time (total makanan diselamatkan & total CO₂ yang dicegah seluruh pengguna)
* get_personal_analytics_json(request) : endpoint JSON terautentikasi untuk data time-series grafik mingguan/bulanan (render via Chart.js / ApexCharts)

**Templates & Components:**

* impact_hub.html : halaman utama dashboard dengan counter animasi, grafik tren Chart.js, dan infografis ekivalensi dampak karbon
* components/eco_badge_modal.html : modal pop-up untuk merayakan pencapaian level/badge baru pengguna
* components/impact_summary_widget.html : widget ringkasan dampak pribadi yang reusable, bisa ditempatkan di halaman profil Consumer atau Dashboard Merchant
  
### 5. Modul Merchant Location Integrator
**Penanggung Jawab** : Ghaisan Nabil Iradat

**Models:**
* merchant location integrator
  * id_merchant
  * name_merchant
  * address
  * longitude
  * latitude

**Views:**

* merchant_location() : Sebagai penghubung, mengambil data untuk rendering

**Template:**
* merchant_loc.html

# Roles
- `Guest`
- `Consumer`
- `Restaurant`
- `Admin`

# Pembagian Job Desk
-`Mystery Box Marketplace & Catalog` : Debora Putri Dion Simamora
-`Merchant Inventory & Pickup Manager` : Jefry Acmal Dzikhrullah
-`Order Validation & Claim System` : Rafael Darius Sagala
-`Carbon & Food Rescue Impact Analytics` : Khalisha Nalani Chandra
-`Merchant Location Integrator` : Ghaisan Nabil Iradat

