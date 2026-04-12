/* ═══════════════════════════════════════════════════════
   GEOLOCATION.JS — Auto-fill weather AND soil nutrients
   ─────────────────────────────────────────────────────
   1. Gets browser GPS coords.
   2. Calls /api/weather → fills Temperature, Humidity, Rainfall.
   3. Calls /api/soil    → fills N, P, K, pH.
   Shows a static disclaimer element already in the HTML
   (no dynamic DOM injection that could break the grid).
═══════════════════════════════════════════════════════ */

const GEO_TIMEOUT_MS = 8000;

/* ── Show / hide the static disclaimer in the HTML ── */
function _showSoilDisclaimer(regionName) {
  const el = document.getElementById('soilEstimateDisclaimer');
  if (!el) return;
  el.textContent = '📍 Estimated soil values for ' + regionName + ' — adjust manually if you have lab results.';
  el.style.display = 'block';
}
function _hideSoilDisclaimer() {
  const el = document.getElementById('soilEstimateDisclaimer');
  if (el) el.style.display = 'none';
}

/* ── Get browser GPS coords ── */
function getBrowserCoords() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) { reject(new Error('Geolocation not supported')); return; }
    navigator.geolocation.getCurrentPosition(
      pos => resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
      err => reject(err),
      { timeout: GEO_TIMEOUT_MS, enableHighAccuracy: false }
    );
  });
}

/* ── Set input + sync its slider + update fill gradient ── */
function setField(id, value) {
  const inp = document.getElementById('inp-' + id);
  const sl  = document.getElementById('sl-'  + id);
  if (!inp) return;

  inp.value = value;

  if (sl) {
    // Clamp value to slider's own min/max before setting
    const min = parseFloat(sl.min) || 0;
    const max = parseFloat(sl.max) || 100;
    const clamped = Math.min(max, Math.max(min, parseFloat(value)));
    sl.value = clamped;

    // Update the CSS fill gradient
    const pct = Math.min(100, Math.max(0, ((clamped - min) / (max - min)) * 100));
    sl.style.setProperty('--_pct', pct.toFixed(2) + '%');
  }

  // Fire input event so any other listeners (syncSlider etc.) run
  inp.dispatchEvent(new Event('input', { bubbles: true }));
}

/* ── Fill weather fields from /api/weather ── */
async function _fillWeather(lat, lon) {
  const w = await API.weather(lat, lon);
  if (w.temperature != null) setField('T', Math.round(w.temperature));
  if (w.humidity    != null) setField('H', Math.round(w.humidity));
  if (w.rainfall    != null) {
    // Clamp to slider range 20–300
    setField('R', Math.min(300, Math.max(0, Math.round(w.rainfall))));
  }
}

/* ── Fill soil nutrient fields from /api/soil ── */
async function _fillSoil(lat, lon) {
  const s = await API.soil(lat, lon);
  if (s.N  != null) setField('N',  Math.round(s.N));
  if (s.P  != null) setField('P',  Math.round(s.P));
  if (s.K  != null) setField('K',  Math.round(s.K));
  if (s.ph != null) setField('pH', parseFloat(s.ph).toFixed(1));
  _showSoilDisclaimer(s.region || 'your region');
}

/* ── Main entry point ── */
async function autoFillWeather() {
  if (!document.getElementById('inp-T')) return;

  showToast('📍 Detecting your location…');
  let lat, lon;
  try {
    ({ lat, lon } = await getBrowserCoords());
  } catch {
    showToast('📍 Location access denied — please enter values manually.');
    return;
  }

  showToast('🌍 Fetching weather & soil data…');

  const [wRes, sRes] = await Promise.allSettled([
    _fillWeather(lat, lon),
    _fillSoil(lat, lon),
  ]);

  const wOk = wRes.status === 'fulfilled';
  const sOk = sRes.status === 'fulfilled';

  if (wOk && sOk)
    showToast('✅ All fields auto-filled from your location!');
  else if (wOk)
    showToast('✅ Climate filled. Soil estimate unavailable — enter N/P/K manually.');
  else if (sOk)
    showToast('✅ Soil estimated. Weather unavailable — enter climate values manually.');
  else
    showToast('⚠️ Auto-fill failed — please enter all values manually.');
}

/* ── Hero CTA handler ── */
function handleDetectCTA() {
  if (!Auth.requireAuth('recommend')) return;
  showPage('recommend');
  setTimeout(autoFillWeather, 300);
}
