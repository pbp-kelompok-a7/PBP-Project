document.addEventListener('DOMContentLoaded', function () {
     // 1. Reveal-up & Pop-card scroll animation observer
    const animatedEls = document.querySelectorAll('.reveal-up, .pop-card');
    if ('IntersectionObserver' in window) {
        animatedEls.forEach(function (el) {
            el.classList.remove('is-visible');
        });
        const observer = new IntersectionObserver(function (entries, obs) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    obs.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12 });
        animatedEls.forEach(function (el) {
            observer.observe(el);
        });
    } else {
        animatedEls.forEach(function (el) {
            el.classList.add('is-visible');
        });
    }
    // 2. Animasi Angka Counter (0 -> 100++ dan 0.0 -> 3.2 Ton)
    const statsCard = document.getElementById('stats-counter-card');
    const mpEl = document.getElementById('counter-marketplace');
    const co2El = document.getElementById('counter-co2');
    function runCounters() {
        if (!mpEl || !co2El || statsCard.dataset.counted === 'true') return;
        statsCard.dataset.counted = 'true';
        const duration = 1400;
        const startTime = performance.now();
        const targetMp = parseInt(mpEl.dataset.target || '100', 10);
        const targetCo2 = parseFloat(co2El.dataset.target || '3.2');
        function tick(now) {
            const progress = Math.min((now - startTime) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            mpEl.textContent = Math.round(eased * targetMp);
            co2El.textContent = (eased * targetCo2).toFixed(1);
            if (progress < 1) {
                requestAnimationFrame(tick);
            } else {
                mpEl.textContent = targetMp;
                co2El.textContent = targetCo2.toFixed(1);
            }
        }
        requestAnimationFrame(tick);
    }
    if (statsCard && 'IntersectionObserver' in window) {
        const counterObs = new IntersectionObserver(function (entries, obs) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    runCounters();
                    obs.unobserve(entry.target);
                }
            });
        }, { threshold: 0.25 });
        counterObs.observe(statsCard);
    }
    // 3. Efek Peek SISA [IKON] BIJAK dari bawah saat di-scroll
    const peekRow = document.getElementById('tgtg-peek-row');
    if (peekRow && 'IntersectionObserver' in window) {
        peekRow.classList.add('is-hidden-peek');
        const peekObs = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    peekRow.classList.remove('is-hidden-peek');
                }
            });
        }, { threshold: 0.15 });
        peekObs.observe(peekRow.parentElement);
    }

    const mapEl = document.getElementById('merchant-map');
    if (!mapEl) return;

    let userLat = -6.3727;
    let userLng = 106.8267;
    let userMarker = null;

    const map = L.map('merchant-map').setView([userLat, userLng], 13);
    L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', {
        maxZoom: 20,
        attribution: '&copy; Google Maps'
    }).addTo(map);

    const DEPOK_ADDRESS_COORDS = {
        "jl. margonda raya no. 12, depok": [-6.3912, 106.8243],
        "jl. kober no. 5, depok": [-6.3685, 106.8332],
        "jl. haji asmawi no. 8, depok": [-6.3722, 106.8148],
        "jl. sawo no. 21, depok": [-6.3642, 106.8325],
        "jl. margonda raya no. 99, depok": [-6.3755, 106.8318],
        "jl. beji timur no. 3, depok": [-6.3775, 106.8215],
        "jl. juanda no. 17, depok": [-6.3792, 106.8425],
        "jl. kukusan no. 10, depok": [-6.3698, 106.8172],
        "jl. nusantara no. 7, depok": [-6.3905, 106.8130],
        "jl. kukusan teknik no. 2, depok": [-6.3621, 106.8248],
        "jl. akses ui no. 15, depok": [-6.3551, 106.8412],
        "jl. siliwangi no. 11, depok": [-6.3980, 106.8295],
        "jl. margonda raya no. 45, depok": [-6.3840, 106.8290],
        "jl. pemuda no. 4, depok": [-6.4025, 106.8210],
        "jl. raya bogor no. 21, depok": [-6.3815, 106.8660],
        "jl. kemiri muka no. 9, depok": [-6.3828, 106.8265]
    };

    function getCoordsFromAddress(addressText, index = 0) {
        const clean = (addressText || '').toLowerCase().trim();
        if (DEPOK_ADDRESS_COORDS[clean]) {
            return DEPOK_ADDRESS_COORDS[clean];
        }

        for (const [key, coords] of Object.entries(DEPOK_ADDRESS_COORDS)) {
            const streetName = key.split(' no.')[0];
            if (clean.includes(streetName)) return coords;
        }

        return [-6.3727 + (index * 0.003), 106.8267 + (index * 0.003)];
    }

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

    const nearbyCards = document.querySelectorAll('section[aria-labelledby="nearby-title"] .deal-card');
    let merchants = [];
    const seen = new Set();

    document.querySelectorAll('section[aria-labelledby="nearby-title"] .deal-card').forEach((card, idx) => {
        const address = card.dataset.address || card.querySelector('.deal-meta span')?.textContent || '';
        const name = card.dataset.name || card.querySelector('h3')?.textContent || '';
        const id = card.dataset.merchant || address || `m-${idx}`;

        card.dataset.merchant = id; 

        let lat = parseFloat((card.dataset.lat || '').replace(',', '.'));
        let lng = parseFloat((card.dataset.lng || '').replace(',', '.'));

        if (isNaN(lat) || isNaN(lng)) {
            const [mappedLat, mappedLng] = getCoordsFromAddress(address, idx);
            lat = mappedLat;
            lng = mappedLng;
            card.dataset.lat = lat;
            card.dataset.lng = lng;
        }

        const routeBtn = card.querySelector('a.deal-btn');
        if (routeBtn) {
            const destQuery = encodeURIComponent(`${address}`);
            routeBtn.href = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}&query=${destQuery}`;
        }

        if (!seen.has(id)) {
            seen.add(id);
            merchants.push({
                id_merchant: id,
                name_merchant: name,
                address: address,
                latitude: lat,
                longitude: lng
            });
        }
    });

    const markers = {};
    const bounds = [];

    merchants.forEach(m => {
        const id = String(m.id_merchant);

        const marker = L.marker([m.latitude, m.longitude]).addTo(map);
        marker.bindPopup(`
            <div class="loc-popup">
                <strong>${esc(m.name_merchant || m.name)}</strong>
                <p>${esc(m.address)}</p>
                <a href="https://www.google.com/maps/dir/?api=1&destination=${m.latitude},${m.longitude}"
                   target="_blank" rel="noopener noreferrer">Buka Google Maps &rarr;</a>
            </div>`);

        marker.on('click', () => highlightCards(id));
        markers[id] = marker;
        bounds.push([m.latitude, m.longitude]);
    });

    if (bounds.length > 0) {
        map.fitBounds(bounds, { padding: [30, 30], maxZoom: 15 });
    }

    function highlightCards(id) {
        nearbyCards.forEach(c =>
            c.classList.toggle('is-active', c.dataset.merchant === String(id)));
    }

    function updateDistances() {
        nearbyCards.forEach(card => {
            const id = card.dataset.merchant;
            const mk = markers[id];
            const distEl = card.querySelector('.js-distance');
            if (mk && distEl) {
                const pos = mk.getLatLng();
                distEl.textContent = calcDistanceKm(userLat, userLng, pos.lat, pos.lng) + ' km';
            }
        });
    }

    updateDistances();

    nearbyCards.forEach(card => {
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
                    userLat = pos.coords.latitude;
                    userLng = pos.coords.longitude;
                    map.setView([userLat, userLng], 14);

                    if (userMarker) map.removeLayer(userMarker);
                    userMarker = L.circleMarker([userLat, userLng], {
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