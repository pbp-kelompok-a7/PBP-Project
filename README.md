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
Tempat pembeli (mahasiswa/pekerja) bisa ngeliat dan milih paket Mystery Box dari resto/cafe terdekat yang lagi diskon gede (50-70%) pas mau tutup toko.

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
Sistem pesanan yang bakal ngeluarin kode unik/QR Code buat ditunjukin ke kasir toko pas pembeli ngambil makanannya di lokasi.

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

