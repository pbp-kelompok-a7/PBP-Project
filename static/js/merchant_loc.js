document.addEventListener('DOMContentLoaded', function () {
    const mapEl = document.getElementById('merchant-map');
    if (!mapEl) return;

    let userLat = -6.3727;
    let userLng = 106.8267;
    let userMarker = null;

    const map = L.map('merchant-map').setView([userLat, userLng], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        referrerPolicy: 'origin',
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    function esc(text) {
        const d = document.createElement('div');
        d.textContent = text == null ? '' : text;
        return d.innerHTML;
    }

    function calcDistanceKm(lat1, lon1, lat2, lon2) {
        const R = 6371;
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                  Math.sin(dLon / 2) * Math.sin(dLon / 2);
        return (R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))).toFixed(1);
    }

    let merchants = [];
    const jsonEl = document.getElementById('merchants-data-json');
    if (jsonEl && jsonEl.textContent.trim() && jsonEl.textContent.trim() !== '""') {
        try {
            const parsed = JSON.parse(jsonEl.textContent);
            if (Array.isArray(parsed) && parsed.length > 0) {
                merchants = parsed;
            }
        } catch (e) {
            merchants = [];
        }
    }

    if (merchants.length === 0) {
        const seen = new Set();
        document.querySelectorAll('.deal-card[data-merchant]').forEach(card => {
            const id = card.dataset.merchant;
            const lat = parseFloat((card.dataset.lat || '').replace(',', '.'));
            const lng = parseFloat((card.dataset.lng || '').replace(',', '.'));
            if (id && !seen.has(id) && !isNaN(lat) && !isNaN(lng)) {
                seen.add(id);
                merchants.push({
                    id_merchant: id,
                    name_merchant: card.dataset.name || card.querySelector('h3')?.textContent || '',
                    address: card.dataset.address || '',
                    latitude: lat,
                    longitude: lng
                });
            }
        });
    }

    const markers = {};
    const bounds = [];

    merchants.forEach(m => {
        const id = String(m.id_merchant || m.id);
        const lat = parseFloat(m.latitude ?? m.lat);
        const lng = parseFloat(m.longitude ?? m.lng);
        if (isNaN(lat) || isNaN(lng)) return;

        const marker = L.marker([lat, lng]).addTo(map);
        marker.bindPopup(`
            <div class="loc-popup">
                <strong>${esc(m.name_merchant || m.name)}</strong>
                <p>${esc(m.address)}</p>
                <a href="https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}"
                   target="_blank" rel="noopener noreferrer">Buka Google Maps &rarr;</a>
            </div>`);

        marker.on('click', () => highlightCards(id));
        markers[id] = marker;
        bounds.push([lat, lng]);
    });

    if (bounds.length > 0) {
        map.fitBounds(bounds, { padding: [30, 30], maxZoom: 15 });
    }

    function highlightCards(id) {
        document.querySelectorAll('.deal-card').forEach(c =>
            c.classList.toggle('is-active', c.dataset.merchant === String(id)));
    }

    function updateDistances() {
        document.querySelectorAll('.deal-card[data-merchant]').forEach(card => {
            const id = card.dataset.merchant;
            const mk = markers[id];
            const distEl = card.querySelector('.js-distance');
            if (mk && distEl) {
                const pos = mk.getLatLng();
                distEl.textContent = calcDistanceKm(userLat, userLng, pos.lat, pos.lng) + ' km';
            }
        });
    }

    document.querySelectorAll('.deal-card[data-merchant]').forEach(card => {
        card.addEventListener('click', e => {
            if (e.target.closest('a')) return; 
            const id = card.dataset.merchant;
            const mk = markers[id];
            if (!mk) return;
            map.setView(mk.getLatLng(), 16, { animate: true });
            mk.openPopup();
            highlightCards(id);
        });
    });

    const btnMyLocation = document.getElementById('btn-my-location');
    if (btnMyLocation) {
        btnMyLocation.addEventListener('click', () => {
            if (!navigator.geolocation) {
                alert('Browser tidak mendukung Geolocation.');
                return;
            }
            navigator.geolocation.getCurrentPosition(
                pos => {
                    const { latitude: lat, longitude: lng } = pos.coords;
                    userLat = lat;
                    userLng = lng;
                    map.setView([lat, lng], 14);

                    if (userMarker) map.removeLayer(userMarker);
                    userMarker = L.circleMarker([lat, lng], {
                        radius: 8,
                        fillColor: '#2563eb',
                        color: '#fff',
                        weight: 2,
                        fillOpacity: 0.9
                    }).addTo(map).bindPopup('<b>Lokasi Anda</b>').openPopup();

                    const locLabel = document.getElementById('loc-label');
                    if (locLabel) locLabel.textContent = 'Lokasi: posisi saat ini';

                    updateDistances();
                },
                () => alert('Tidak dapat mengakses lokasi. Pastikan izin lokasi diaktifkan.')
            );
        });
    }
});