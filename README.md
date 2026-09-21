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
Dashboard analisis buat ngeliat statistik total makanan yang berhasil diselamatkan plus estimasi emisi CO2 yang berhasil dicegah (pake API).

### 5. Modul Merchant Location Integrator
Peta lokasi interaktif buat nampilin titik-titik cafe/toko mitra. terdekat dari posisi pengguna.

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

