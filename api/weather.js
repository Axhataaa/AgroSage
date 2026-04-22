/* ═══════════════════════════════════════════════════════
   WEATHER.JS — Navbar weather widget for AgroSage
   ─────────────────────────────────────────────────────
   • Geocodes city names via Open-Meteo Geocoding API (free, no key)
   • Fetches weather via existing backend GET /api/weather?lat&lon
   • Shows temperature, humidity, rainfall
   • Suggests top-3 crops that match current weather
   • "Pre-fill Advisor" button sends values to Crop Advisor form
═══════════════════════════════════════════════════════ */

/* ── Crop suggestion rules (temperature, humidity, rainfall ranges) ── */
const WEATHER_CROPS = [
  { name:'Rice',       emoji:'🌾', tMin:22, tMax:35, hMin:70, hMax:100, rMin:150, rMax:300, reason:'High humidity and rainfall make it ideal for rice paddies.' },
  { name:'Wheat',      emoji:'🌿', tMin:10, tMax:24, hMin:40, hMax:75,  rMin:50,  rMax:150, reason:'Cool temperatures and moderate moisture favour wheat growth.' },
  { name:'Maize',      emoji:'🌽', tMin:20, tMax:32, hMin:50, hMax:85,  rMin:80,  rMax:200, reason:'Warm and moderately humid conditions suit maize perfectly.' },
  { name:'Cotton',     emoji:'🌸', tMin:25, tMax:38, hMin:35, hMax:70,  rMin:50,  rMax:130, reason:'Hot, semi-dry weather is ideal for cotton bolls to open.' },
  { name:'Sugarcane',  emoji:'🍬', tMin:24, tMax:38, hMin:60, hMax:100, rMin:100, rMax:250, reason:'Warm and humid climate drives sugarcane biomass.' },
  { name:'Millet',     emoji:'🌱', tMin:25, tMax:40, hMin:25, hMax:60,  rMin:25,  rMax:100, reason:'Drought-tolerant; thrives in hot, low-rainfall conditions.' },
  { name:'Soybean',    emoji:'🫘', tMin:18, tMax:30, hMin:55, hMax:85,  rMin:90,  rMax:200, reason:'Warm temperatures with adequate moisture optimise soybean yields.' },
  { name:'Tomato',     emoji:'🍅', tMin:18, tMax:29, hMin:50, hMax:80,  rMin:50,  rMax:130, reason:'Mild, consistent warmth and moderate humidity are perfect for tomatoes.' },
  { name:'Chickpea',   emoji:'🟡', tMin:15, tMax:29, hMin:30, hMax:65,  rMin:30,  rMax:100, reason:'Tolerates low rainfall; cool-season legume ideal for current conditions.' },
  { name:'Banana',     emoji:'🍌', tMin:22, tMax:35, hMin:75, hMax:100, rMin:120, rMax:280, reason:'Tropical warmth and high humidity accelerate banana growth.' },
  { name:'Groundnut',  emoji:'🥜', tMin:22, tMax:35, hMin:40, hMax:75,  rMin:50,  rMax:130, reason:'Warm, semi-arid climate suits groundnut pod formation.' },
  { name:'Mustard',    emoji:'💛', tMin:10, tMax:25, hMin:35, hMax:70,  rMin:30,  rMax:100, reason:'Cool, dry weather is optimal for mustard seed development.' },
];

/* Score how well current weather matches a crop (0–3 points) */
function _cropScore(crop, temp, humidity, rainfall) {
  let score = 0;
  if (temp     >= crop.tMin && temp     <= crop.tMax) score++;
  if (humidity >= crop.hMin && humidity <= crop.hMax) score++;
  if (rainfall >= crop.rMin && rainfall <= crop.rMax) score++;
  return score;
}

function _getWeatherCropSuggestions(temp, humidity, rainfall) {
  return WEATHER_CROPS
    .map(c => ({ ...c, score: _cropScore(c, temp, humidity, rainfall) }))
    .filter(c => c.score >= 2)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);
}

/* ── Panel visibility ── */
let _panelOpen = false;

function toggleWeatherPanel() {
  const panel = document.getElementById('weatherPanel');
  if (!panel) return;
  _panelOpen = !_panelOpen;
  panel.classList.toggle('weather-panel--open', _panelOpen);
  if (_panelOpen) {
    // Focus the search input
    setTimeout(() => {
      const inp = document.getElementById('weatherCityInput');
      if (inp) inp.focus();
    }, 120);
  }
}

/* Close panel when clicking outside */
document.addEventListener('click', e => {
  const btn   = document.getElementById('weatherNavBtn');
  const panel = document.getElementById('weatherPanel');
  if (!panel || !_panelOpen) return;
  if (!panel.contains(e.target) && !btn.contains(e.target)) {
    _panelOpen = false;
    panel.classList.remove('weather-panel--open');
  }
});

/* ── Geocoding ── */
async function _geocodeCity(city) {
  const url = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(city)}&count=1&language=en&format=json`;
  const res  = await fetch(url);
  if (!res.ok) throw new Error('Geocoding request failed');
  const data = await res.json();
  if (!data.results || data.results.length === 0)
    throw new Error(`No location found for "${city}"`);
  const r = data.results[0];
  return { lat: r.latitude, lon: r.longitude, name: r.name, country: r.country };
}

/* ── Weather condition helper ── */
function _weatherIcon(temp) {
  if (temp >= 35)      return '☀️';
  if (temp >= 27)      return '🌤️';
  if (temp >= 18)      return '⛅';
  if (temp >= 10)      return '🌥️';
  return '🌨️';
}

/* ── Render weather result ── */
function _renderWeatherResult(location, weather) {
  const { temperature: temp, humidity, rainfall } = weather;
  const suggestions = _getWeatherCropSuggestions(temp, humidity, rainfall);

  const icon = _weatherIcon(temp);

  /* Weather card */
  document.getElementById('wResult').style.display = 'block';
  document.getElementById('wError').style.display  = 'none';

  document.getElementById('wLocationName').textContent = `${location.name}, ${location.country}`;
  document.getElementById('wIcon').textContent         = icon;
  document.getElementById('wTemp').textContent         = `${Math.round(temp)}°C`;
  document.getElementById('wHumidity').textContent     = `${Math.round(humidity)}%`;
  document.getElementById('wRainfall').textContent     = `${Math.round(rainfall)} mm/yr`;

  /* Crop suggestions */
  const cBox = document.getElementById('wCropSuggestions');
  if (suggestions.length === 0) {
    cBox.innerHTML = '<p class="w-no-crops">No perfect match — try the Crop Advisor for precise recommendations.</p>';
  } else {
    cBox.innerHTML = suggestions.map(c => `
      <div class="w-crop-chip">
        <span class="w-crop-emoji">${c.emoji}</span>
        <div class="w-crop-info">
          <div class="w-crop-name">${c.name}</div>
          <div class="w-crop-reason">${c.reason}</div>
        </div>
      </div>`).join('');
  }

  /* Store for pre-fill */
  document.getElementById('weatherPanel').dataset.temp     = temp;
  document.getElementById('weatherPanel').dataset.humidity = humidity;
  document.getElementById('weatherPanel').dataset.rainfall = rainfall;

  document.getElementById('wPrefillBtn').style.display = 'flex';
}

/* ── Main search function ── */
async function searchWeather() {
  const input = document.getElementById('weatherCityInput');
  const city  = (input?.value || '').trim();
  if (!city) { showToast('⚠️ Enter a city name first.'); return; }

  const btn = document.getElementById('wSearchBtn');
  btn.textContent = '…';
  btn.disabled    = true;

  document.getElementById('wResult').style.display  = 'none';
  document.getElementById('wError').style.display   = 'none';
  document.getElementById('wLoading').style.display = 'flex';

  try {
    const location = await _geocodeCity(city);
    const res      = await fetch(`/api/weather?lat=${location.lat}&lon=${location.lon}`);
    const weather  = await res.json();

    if (!weather.success) throw new Error(weather.message || 'Weather fetch failed');

    document.getElementById('wLoading').style.display = 'none';
    _renderWeatherResult(location, weather);
  } catch (err) {
    document.getElementById('wLoading').style.display = 'none';
    document.getElementById('wError').style.display   = 'block';
    document.getElementById('wErrorMsg').textContent  = err.message || 'Could not fetch weather. Please try again.';
  } finally {
    btn.textContent = '→';
    btn.disabled    = false;
  }
}

/* ── Pre-fill Crop Advisor with current weather values ── */
function prefillCropAdvisor() {
  const panel    = document.getElementById('weatherPanel');
  const temp     = parseFloat(panel.dataset.temp     || 0);
  const humidity = parseFloat(panel.dataset.humidity || 0);
  const rainfall = parseFloat(panel.dataset.rainfall || 0);

  /* Use geolocation.js setField() if available, otherwise set directly */
  if (typeof setField === 'function') {
    setField('T', Math.round(temp));
    setField('H', Math.round(humidity));
    setField('R', Math.min(300, Math.max(0, Math.round(rainfall))));
  } else {
    const setVal = (id, v) => {
      const inp = document.getElementById('inp-' + id);
      const sl  = document.getElementById('sl-'  + id);
      if (inp) inp.value = v;
      if (sl)  sl.value  = v;
    };
    setVal('T', Math.round(temp));
    setVal('H', Math.round(humidity));
    setVal('R', Math.min(300, Math.max(0, Math.round(rainfall))));
  }

  /* Navigate to Crop Advisor */
  if (typeof showPage === 'function') showPage('recommend');
  showToast('🌤️ Weather values pre-filled in Crop Advisor!');

  /* Close panel */
  _panelOpen = false;
  document.getElementById('weatherPanel').classList.remove('weather-panel--open');
}

/* ── Allow Enter key in search box ── */
document.addEventListener('DOMContentLoaded', () => {
  const inp = document.getElementById('weatherCityInput');
  if (inp) {
    inp.addEventListener('keydown', e => {
      if (e.key === 'Enter') searchWeather();
    });
  }
});
