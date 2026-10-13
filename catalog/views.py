from django.http import Http404, JsonResponse
from django.shortcuts import render

# data dummy dulu, nanti diganti pake MerchantInventory punya jefry
# nama field sengaja disamain sama README biar nanti gampang gantinya
DUMMY_PAKET = [
    {
        "id": 1,
        "nama_produk": "Bread Surprise Box",
        "nama_toko": "Roti Kita Bakery",
        "alamat": "Jl. Margonda Raya No. 12, Depok",
        "harga_asli": 40000,
        "harga_diskon": 15000,
        "stok_harian": 3,
        "jam_mulai_pickup": "20:00",
        "jam_selesai_pickup": "21:00",
        "status": "tersedia",
        "deskripsi": "Campuran roti dan pastry yang belum laku hari ini, masih fresh dan enak.",
    },
    {
        "id": 2,
        "nama_produk": "Pastry & Coffee Box",
        "nama_toko": "Kopi Senja Cafe",
        "alamat": "Jl. Kober No. 5, Depok",
        "harga_asli": 55000,
        "harga_diskon": 22000,
        "stok_harian": 5,
        "jam_mulai_pickup": "21:00",
        "jam_selesai_pickup": "22:00",
        "status": "tersedia",
        "deskripsi": "Pastry pilihan plus satu kopi susu literan buat begadang.",
    },
    {
        "id": 3,
        "nama_produk": "Cake Slice Box",
        "nama_toko": "Sweet Crumbs",
        "alamat": "Jl. Haji Asmawi No. 8, Depok",
        "harga_asli": 70000,
        "harga_diskon": 25000,
        "stok_harian": 2,
        "jam_mulai_pickup": "19:30",
        "jam_selesai_pickup": "20:30",
        "status": "tersedia",
        "deskripsi": "Beberapa potong kue dengan rasa random, bisa cheesecake, brownies, atau red velvet.",
    },
    {
        "id": 4,
        "nama_produk": "Healthy Meal Box",
        "nama_toko": "Dapur Hijau",
        "alamat": "Jl. Sawo No. 21, Depok",
        "harga_asli": 45000,
        "harga_diskon": 18000,
        "stok_harian": 4,
        "jam_mulai_pickup": "20:00",
        "jam_selesai_pickup": "21:00",
        "status": "tersedia",
        "deskripsi": "Menu sehat sisa hari ini, biasanya salad, nasi merah, dan lauk panggang.",
    },
    {
        "id": 5,
        "nama_produk": "Donut Mix Box",
        "nama_toko": "Bakeri Margonda",
        "alamat": "Jl. Margonda Raya No. 99, Depok",
        "harga_asli": 35000,
        "harga_diskon": 12000,
        "stok_harian": 6,
        "jam_mulai_pickup": "21:00",
        "jam_selesai_pickup": "21:30",
        "status": "tersedia",
        "deskripsi": "Isi 6 donat dengan topping campur.",
    },
    {
        "id": 6,
        "nama_produk": "Rice Box Surprise",
        "nama_toko": "Warung Rasa",
        "alamat": "Jl. Beji Timur No. 3, Depok",
        "harga_asli": 35000,
        "harga_diskon": 15000,
        "stok_harian": 3,
        "jam_mulai_pickup": "20:30",
        "jam_selesai_pickup": "21:30",
        "status": "tersedia",
        "deskripsi": "Nasi plus lauk rumahan yang tersisa hari ini.",
    },
    {
        "id": 7,
        "nama_produk": "Croissant Box",
        "nama_toko": "Croissant Corner",
        "alamat": "Jl. Juanda No. 17, Depok",
        "harga_asli": 60000,
        "harga_diskon": 20000,
        "stok_harian": 2,
        "jam_mulai_pickup": "21:00",
        "jam_selesai_pickup": "22:00",
        "status": "tersedia",
        "deskripsi": "Croissant butter, cokelat, dan almond, isinya tergantung sisa hari itu.",
    },
    {
        "id": 8,
        "nama_produk": "Toast Combo Box",
        "nama_toko": "Teh & Toast",
        "alamat": "Jl. Kukusan No. 10, Depok",
        "harga_asli": 40000,
        "harga_diskon": 16000,
        "stok_harian": 7,
        "jam_mulai_pickup": "20:00",
        "jam_selesai_pickup": "21:00",
        "status": "tersedia",
        "deskripsi": "Roti bakar aneka rasa plus teh manis.",
    },
    {
        # yang ini sengaja habis, buat ngetes kalau paket habis ga muncul di katalog
        "id": 9,
        "nama_produk": "Brownies Box",
        "nama_toko": "Sweet Crumbs",
        "alamat": "Jl. Haji Asmawi No. 8, Depok",
        "harga_asli": 50000,
        "harga_diskon": 20000,
        "stok_harian": 0,
        "jam_mulai_pickup": "19:30",
        "jam_selesai_pickup": "20:30",
        "status": "habis",
        "deskripsi": "Brownies panggang potong.",
    },
]


def format_rupiah(angka):
    # 15000 -> Rp15.000
    return "Rp{:,}".format(angka).replace(",", ".")


def siapin_paket(paket):
    # nambahin data yang dibutuhin template: persen diskon & harga yang udah rapi
    data = dict(paket)
    data["diskon_persen"] = round((1 - paket["harga_diskon"] / paket["harga_asli"]) * 100)
    data["harga_asli_str"] = format_rupiah(paket["harga_asli"])
    data["harga_diskon_str"] = format_rupiah(paket["harga_diskon"])
    return data


def ambil_paket_tersedia():
    # cuma ambil yang statusnya tersedia & stoknya masih ada
    hasil = []
    for paket in DUMMY_PAKET:
        if paket["status"] == "tersedia" and paket["stok_harian"] > 0:
            hasil.append(siapin_paket(paket))
    # urutin dari diskon paling gede
    hasil.sort(key=lambda p: p["diskon_persen"], reverse=True)
    return hasil


def filter_paket(paket_list, keyword, harga):
    hasil = []
    for paket in paket_list:
        # filter search: cocokin ke nama produk atau nama toko
        if keyword:
            teks = (paket["nama_produk"] + " " + paket["nama_toko"]).lower()
            if keyword not in teks:
                continue

        # filter harga diskon
        h = paket["harga_diskon"]
        if harga == "lt15" and not h < 15000:
            continue
        if harga == "15to25" and not (15000 <= h <= 25000):
            continue
        if harga == "gt25" and not h > 25000:
            continue

        hasil.append(paket)
    return hasil


def catalog_list_view(request):
    paket_list = ambil_paket_tersedia()
    context = {
        "paket_list": paket_list,
        "jumlah": len(paket_list),
    }
    return render(request, "catalog/catalog.html", context)


def get_catalog_json(request):
    # dipanggil lewat AJAX pas user ngetik search atau klik filter harga
    keyword = request.GET.get("q", "").strip().lower()
    harga = request.GET.get("harga", "all")
    paket_list = filter_paket(ambil_paket_tersedia(), keyword, harga)
    return JsonResponse({"jumlah": len(paket_list), "data": paket_list})


def catalog_detail_view(request, inventory_id):
    for paket in DUMMY_PAKET:
        if paket["id"] == inventory_id:
            return render(request, "catalog/catalog_detail.html", {"paket": siapin_paket(paket)})
    raise Http404("Paket tidak ditemukan")