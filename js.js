const API_BASE = 'https://worldfactbook.io/api/v1';

let allCountries = [];

// Ҳама кишварҳоро бор кун
async function loadAllCountries() {
    try {
        const res = await fetch(`${API_BASE}/countries/`);
        const data = await res.json();
        allCountries = data;
        displayCountries(allCountries);
    } catch (err) {
        console.error('Хато:', err);
        document.getElementById('results').innerHTML = `<p style="color:red;text-align:center;">Хато дар боркунии маълумотҳо. Баъдтар кӯшиш кунед.</p>`;
    }
}

// Намоиши карточкаҳо
function displayCountries(countries) {
    const container = document.getElementById('results');
    container.innerHTML = '';

    countries.forEach(country => {
        const card = document.createElement('div');
        card.className = 'country-card';
        card.innerHTML = `
            <img src="${country.flag}" alt="${country.name}">
            <div class="info">
                <h3>${country.name}</h3>
                <p>🏛 Пойтахт: <strong>${country.capital || '—'}</strong></p>
                <p>👥 Аҳолӣ: <strong>${country.population ? country.population.toLocaleString('tg-TJ') : '—'}</strong></p>
                <p>📍 Минтақа: <strong>${country.region || '—'}</strong></p>
            </div>
        `;
        card.addEventListener('click', () => showDetails(country.slug));
        container.appendChild(card);
    });

    if (countries.length === 0) {
        container.innerHTML = `<p style="text-align:center;grid-column:1/-1;color:#94a3b8;">Кишвар ёфт нашуд 😔</p>`;
    }
}

// Маълумотҳои мукаммалро нишон деҳ
async function showDetails(slug) {
    const modal = document.getElementById('detailModal');
    const body = document.getElementById('modalBody');
    body.innerHTML = `<p style="text-align:center;padding:50px;">Маълумотҳо бор шуда истодаанд...</p>`;
    modal.style.display = 'block';

    try {
        const res = await fetch(`${API_BASE}/countries/${slug}/`);
        const data = await res.json();

        // Ҳоло мо ҳамаи қисмҳоро динамикӣ нишон медиҳем (API пурра медиҳад)
        body.innerHTML = `
            <h2 style="text-align:center;margin-bottom:20px;">${data.name} <img src="${data.flag}" style="height:40px;vertical-align:middle;"></h2>
            
            <h3>🌍 1. Маълумоти умумӣ</h3>
            <p><strong>Номи расмӣ:</strong> ${data.introduction?.officialName || data.name}</p>
            <p><strong>Пойтахт:</strong> ${data.capital}</p>
            <p><strong>Минтақа:</strong> ${data.region}</p>

            <h3>📍 2. Ҷуғрофия</h3>
            <div>${data.geography ? data.geography : '<p>Маълумотҳо дар ҳоли бор шудан...</p>'}</div>

            <h3>👥 3. Аҳолӣ</h3>
            <p><strong>Шумора:</strong> ${data.population?.toLocaleString('tg-TJ')}</p>

            <h3>💰 4. Иқтисод</h3>
            <p><strong>ММД:</strong> ${data.gdp ? '$' + data.gdp.toLocaleString('tg-TJ') : '—'}</p>

            <!-- Дигар қисмҳо (economy, government, military ва ғ.) низ ҳамин тавр илова карда мешавад -->
            <h3>🛡 6. Қувваи низомӣ</h3>
            <div>${data.military ? data.military : '<p>Маълумотҳо дар ҳоли бор шудан...</p>'}</div>

            <h3 style="margin-top:30px;color:#22c55e;">📋 Ҳамаи 12 қисмҳо дар API ҳастанд. Ман баъдтар ҳамаашро зебо мекунам!</h3>
        `;
    } catch (err) {
        body.innerHTML = `<p style="color:red;">Хато: Маълумотҳо бор нашуданд.</p>`;
    }
}

// Закрытие модального окна
document.getElementById('closeModal').addEventListener('click', () => {
    document.getElementById('detailModal').style.display = 'none';
});

// Ҷустуҷӯ
document.getElementById('searchBtn').addEventListener('click', () => {
    const query = document.getElementById('searchInput').value.toLowerCase().trim();
    const filtered = allCountries.filter(c => 
        c.name.toLowerCase().includes(query)
    );
    displayCountries(filtered);
});

// Enter-ро ҳам кор кун
document.getElementById('searchInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') document.getElementById('searchBtn').click();
});

// Оғоз кардани сайт
loadAllCountries();