/* ═══════════════════════════════════════════════════════
   WEATHER.JS — AgroSage
   ─────────────────────────────────────────────────────
   1. Inline weather widget embedded inside Crop Advisor
      (not a navbar dropdown — it lives where it's useful)
   2. Dynamic season insight card on the Insights page
═══════════════════════════════════════════════════════ */

/* ── Crop matching rules ── */
const WEATHER_CROPS = [
  { name:'Rice',      emoji:'🌾', tMin:22, tMax:35, hMin:70, hMax:100, rMin:150, rMax:300, reason:'High humidity and rainfall suit rice paddies.' },
  { name:'Wheat',     emoji:'🌿', tMin:10, tMax:24, hMin:40, hMax:75,  rMin:50,  rMax:150, reason:'Cool temperatures and moderate moisture favour wheat.' },
  { name:'Maize',     emoji:'🌽', tMin:20, tMax:32, hMin:50, hMax:85,  rMin:80,  rMax:200, reason:'Warm, moderately humid conditions suit maize.' },
  { name:'Cotton',    emoji:'🌸', tMin:25, tMax:38, hMin:35, hMax:70,  rMin:50,  rMax:130, reason:'Hot, semi-dry weather is ideal for cotton bolls.' },
  { name:'Sugarcane', emoji:'🍬', tMin:24, tMax:38, hMin:60, hMax:100, rMin:100, rMax:250, reason:'Warm and humid climate drives sugarcane biomass.' },
  { name:'Millet',    emoji:'🌱', tMin:25, tMax:40, hMin:25, hMax:60,  rMin:25,  rMax:100, reason:'Drought-tolerant; thrives in hot, low-rainfall conditions.' },
  { name:'Soybean',   emoji:'🫘', tMin:18, tMax:30, hMin:55, hMax:85,  rMin:90,  rMax:200, reason:'Warm temperature with adequate moisture optimises yield.' },
  { name:'Tomato',    emoji:'🍅', tMin:18, tMax:29, hMin:50, hMax:80,  rMin:50,  rMax:130, reason:'Mild warmth and moderate humidity are perfect for tomatoes.' },
  { name:'Chickpea',  emoji:'🟡', tMin:15, tMax:29, hMin:30, hMax:65,  rMin:30,  rMax:100, reason:'Tolerates low rainfall; ideal cool-season legume.' },
  { name:'Banana',    emoji:'🍌', tMin:22, tMax:35, hMin:75, hMax:100, rMin:120, rMax:280, reason:'Tropical warmth and high humidity accelerate banana growth.' },
  { name:'Groundnut', emoji:'🥜', tMin:22, tMax:35, hMin:40, hMax:75,  rMin:50,  rMax:130, reason:'Warm, semi-arid climate suits groundnut pod formation.' },
  { name:'Mustard',   emoji:'💛', tMin:10, tMax:25, hMin:35, hMax:70,  rMin:30,  rMax:100, reason:'Cool, dry weather is optimal for mustard seed development.' },
];

function _cropScore(c, t, h, r) {
  let s = 0;
  if (t >= c.tMin && t <= c.tMax) s++;
  if (h >= c.hMin && h <= c.hMax) s++;
  if (r >= c.rMin && r <= c.rMax) s++;
  return s;
}

function _getWeatherCropSuggestions(temp, humidity, rainfall) {
  return WEATHER_CROPS
    .map(c => ({ ...c, score: _cropScore(c, temp, humidity, rainfall) }))
    .filter(c => c.score >= 2)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);
}

function _weatherIcon(temp) {
  if (temp >= 35) return '☀️';
  if (temp >= 27) return '🌤️';
  if (temp >= 18) return '⛅';
  return '🌥️';
}

/* ── Geocoding ── */
async function _geocodeCity(city) {
  const url = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(city)}&count=1&language=en&format=json`;
  const res  = await fetch(url);
  if (!res.ok) throw new Error('Geocoding failed');
  const data = await res.json();
  if (!data.results || !data.results.length) throw new Error(`No location found for "${city}"`);
  const r = data.results[0];
  return { lat: r.latitude, lon: r.longitude, name: r.name, country: r.country };
}

/* ══════════════════════════════════════════════════════
   INLINE WEATHER WIDGET (lives inside Crop Advisor)
══════════════════════════════════════════════════════ */
let _inlineWeatherData = null;

function _setWic(zone, show) {
  const ids = { loading:'wicLoading', error:'wicError', result:'wicResult' };
  const el  = document.getElementById(ids[zone]);
  if (el) el.style.display = show ? (zone === 'result' ? 'block' : 'flex') : 'none';
}

function _setEl(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function _renderInlineResult(location, weather) {
  const { temperature: temp, humidity, rainfall } = weather;
  _setEl('wicIcon',         _weatherIcon(temp));
  _setEl('wicTemp',         `${Math.round(temp)}°C`);
  _setEl('wicLocationName', `${location.name}, ${location.country}`);
  _setEl('wicHumidity',     `${Math.round(humidity)}%`);
  _setEl('wicRainfall',     `${Math.round(rainfall)} mm/yr`);

  const chips       = document.getElementById('wicCropChips');
  const suggestions = _getWeatherCropSuggestions(temp, humidity, rainfall);
  if (chips) {
    chips.innerHTML = suggestions.length
      ? suggestions.map(c => `<span class="wic-chip" title="${c.reason}">${c.emoji} ${c.name}</span>`).join('')
      : '<span style="color:var(--text-muted);font-size:0.8rem">No strong match — try the full Crop Advisor.</span>';
  }
}

async function searchWeatherInline() {
  const input = document.getElementById('wicCityInput');
  const city  = (input?.value || '').trim();
  if (!city) { showToast('⚠️ Enter a city name.'); return; }

  const btn = document.getElementById('wicSearchBtn');
  btn.textContent = '…';
  btn.disabled    = true;

  _setWic('loading', true);
  _setWic('error',   false);
  _setWic('result',  false);

  try {
    const location = await _geocodeCity(city);
    const res      = await fetch(`/api/weather?lat=${location.lat}&lon=${location.lon}`);
    const weather  = await res.json();
    if (!weather.success) throw new Error(weather.message || 'Weather fetch failed');

    _inlineWeatherData = { location, weather };
    _renderInlineResult(location, weather);
    _setWic('loading', false);
    _setWic('result',  true);
  } catch (err) {
    _setWic('loading', false);
    _setWic('error',   true);
    _setEl('wicErrorMsg', err.message || 'Could not fetch weather.');
  } finally {
    btn.textContent = 'Search';
    btn.disabled    = false;
  }
}

function prefillFromInlineWeather() {
  if (!_inlineWeatherData) return;
  const { temperature: temp, humidity, rainfall } = _inlineWeatherData.weather;
  const fill = typeof setField === 'function'
    ? (id, v) => setField(id, v)
    : (id, v) => {
        const i = document.getElementById('inp-' + id);
        const s = document.getElementById('sl-'  + id);
        if (i) i.value = v; if (s) s.value = v;
      };
  fill('T', Math.round(temp));
  fill('H', Math.round(humidity));
  fill('R', Math.min(300, Math.max(0, Math.round(rainfall))));
  document.getElementById('inp-T')?.scrollIntoView({ behavior:'smooth', block:'center' });
  showToast('🌤️ Climate fields filled from live weather!');
}

document.addEventListener('DOMContentLoaded', () => {
  const inp = document.getElementById('wicCityInput');
  if (inp) inp.addEventListener('keydown', e => { if (e.key === 'Enter') searchWeatherInline(); });
});

/* ══════════════════════════════════════════════════════
   DYNAMIC SEASON INSIGHT CARD
   Reads the actual current month and updates the first
   card in Insights so it is never wrong/stale.
══════════════════════════════════════════════════════ */
const SEASON_DATA = {
  kharif: {
    icon:  '🌧️',
    title: 'Kharif Season · Monsoon Crops',
    desc:  'Monsoon months are prime time for rice, maize, cotton, soybean, and groundnut. Ensure field drainage to prevent waterlogging. Nitrogen top-dressing at the tillering stage improves yield by 15–20%.',
  },
  rabi: {
    icon:  '❄️',
    title: 'Rabi Season · Winter Crops',
    desc:  'Cool temperatures (10–24°C) favour wheat, mustard, and chickpea. Maintain phosphorus above 40 kg/ha before sowing. Timely irrigation at crown root initiation is critical for wheat yield.',
  },
  zaid: {
    icon:  '☀️',
    title: 'Zaid Season · Summer Crops',
    desc:  'Short summer season suits cucumbers, watermelons, and fodder crops like cowpea. High temperatures (30–40°C) increase water demand — irrigate every 4–5 days. Good time to prepare soil with green manuring for kharif.',
  },
};

function _getCurrentSeason() {
  const m = new Date().getMonth() + 1;
  if (m >= 6 && m <= 10) return 'kharif';
  if (m >= 11 || m <= 3) return 'rabi';
  return 'zaid';
}

function _updateSeasonInsight() {
  const data = SEASON_DATA[_getCurrentSeason()];
  if (!data) return;
  _setEl('insightSeasonIcon',  data.icon);
  _setEl('insightSeasonTitle', data.title);
  _setEl('insightSeasonDesc',  data.desc);
}

document.addEventListener('DOMContentLoaded', _updateSeasonInsight);
