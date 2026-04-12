/* ═══════════════════════════════════════════════════════
   RECOMMEND.JS — Crop recommendation with season awareness
   ─────────────────────────────────────────────────────
   All predictions come from POST /api/recommend.
   Season-awareness logic is purely frontend (JS Date),
   so it works without any backend change.
═══════════════════════════════════════════════════════ */

/* ── Emoji map (display only) ── */
const CROP_EMOJI = {
  rice:'🌾', wheat:'🌾', maize:'🌽', chickpea:'🫘', lentil:'🫘',
  cotton:'🌸', sugarcane:'🎋', mango:'🥭', banana:'🍌',
  watermelon:'🍉', pigeonpea:'🫘', mustard:'🌻', coffee:'☕',
  coconut:'🥥', papaya:'🍈', orange:'🍊', apple:'🍎',
  grapes:'🍇', pomegranate:'🍎', jute:'🪢', kidneybeans:'🫘',
  mothbeans:'🫘',
};
function emoji(name) { return CROP_EMOJI[name.toLowerCase()] || '🌿'; }

/* ════════════════════════════════════════════════════════
   SEASON-AWARENESS ENGINE
════════════════════════════════════════════════════════ */

const MONTH_NAMES  = ['','January','February','March','April','May','June',
                      'July','August','September','October','November','December'];
const SHORT_MONTH  = ['','Jan','Feb','Mar','Apr','May','Jun',
                      'Jul','Aug','Sep','Oct','Nov','Dec'];

/* Current month 1–12, auto-detected */
const NOW_MONTH = new Date().getMonth() + 1;
const NOW_YEAR  = new Date().getFullYear();

/* Indian farming season by month */
function getIndianSeason(month) {
  if ([6,7,8,9].includes(month))
    return { name:'Kharif', icon:'🌧️', color:'#1a6b3c', desc:'Monsoon season · Jun–Sep' };
  if ([10,11,12,1,2].includes(month))
    return { name:'Rabi',   icon:'❄️',  color:'#1e40af', desc:'Winter season · Oct–Feb' };
  return   { name:'Zaid',   icon:'☀️',  color:'#b45309', desc:'Summer season · Mar–May' };
}

/*
  Returns sowing timing status for a crop in the given month.
  status values: 'ideal' | 'soon' | 'late' | 'warning' | 'perennial'
*/
function getTimingStatus(crop, month) {
  if (crop.isPerennial) {
    return {
      status:  'perennial',
      label:   '🌿 Year-round crop',
      detail:  'Can be established any time. No sowing window restriction.',
      color:   '#059669',
    };
  }

  const sow = crop.sowMonths || [];
  if (sow.length === 0) {
    return { status:'unknown', label:'', detail:'', color:'' };
  }

  /* Ideal: current month is a sowing month */
  if (sow.includes(month)) {
    return {
      status: 'ideal',
      label:  '✅ Perfect sowing time!',
      detail: `This is the ideal month to sow ${crop.name}. Your field timing is spot-on.`,
      color:  '#059669',
    };
  }

  /* Soon: sowing window starts next month */
  const nextM = month === 12 ? 1 : month + 1;
  if (sow.includes(nextM)) {
    return {
      status: 'soon',
      label:  `🕐 Sowing starts next month (${MONTH_NAMES[nextM]})`,
      detail: `Prepare your land now — the ${crop.name} sowing window opens in ${MONTH_NAMES[nextM]}.`,
      color:  '#d97706',
    };
  }

  /* Late: sowing window just closed last month */
  const prevM = month === 1 ? 12 : month - 1;
  if (sow.includes(prevM)) {
    return {
      status: 'late',
      label:  `⏰ Sowing window just closed (was ${MONTH_NAMES[prevM]})`,
      detail: `You missed the ${crop.name} sowing window by about a month. Consider one of the seasonal alternatives below.`,
      color:  '#d97706',
    };
  }

  /* Warning: outside sowing window — calculate months away */
  let minFwd = 12, bestMonth = sow[0];
  for (const m of sow) {
    const fwd = (m - month + 12) % 12;
    if (fwd < minFwd) { minFwd = fwd; bestMonth = m; }
  }

  const sowRange = sow.length > 1
    ? `${MONTH_NAMES[sow[0]]}–${MONTH_NAMES[sow[sow.length - 1]]}`
    : MONTH_NAMES[sow[0]];

  return {
    status:     'warning',
    label:      `⚠️ Not ideal for ${MONTH_NAMES[month]}`,
    detail:     `${crop.name} is best sown in ${sowRange}. That is about ${minFwd} month${minFwd > 1 ? 's' : ''} away.`,
    color:      '#dc2626',
    monthsAway: minFwd,
    sowRange,
    bestMonth,
  };
}

/*
  Returns crops from CROPS[] that are ideal to sow this month
  (and optionally the next month as "coming up soon").
*/
function getSeasonalCrops(month) {
  if (typeof CROPS === 'undefined') return { now: [], soon: [] };
  const nextM = month === 12 ? 1 : month + 1;
  const now   = CROPS.filter(c => !c.isPerennial && (c.sowMonths || []).includes(month));
  const soon  = CROPS.filter(c => !c.isPerennial && !(c.sowMonths || []).includes(month) &&
                                   (c.sowMonths || []).includes(nextM));
  return { now, soon };
}

/* Stamp the current-season pill visible in the page header */
function stampSeasonPill() {
  const pill = document.getElementById('currentSeasonPill');
  if (!pill) return;
  const s = getIndianSeason(NOW_MONTH);
  pill.innerHTML =
    `<span class="season-pill-icon">${s.icon}</span>` +
    `<span class="season-pill-text">${MONTH_NAMES[NOW_MONTH]} · ${s.name} Season</span>`;
  pill.style.display = 'inline-flex';
}

/* ════════════════════════════════════════════════════════
   RENDER HELPERS
════════════════════════════════════════════════════════ */

function renderResult(topCrop, confidence, alternatives) {
  document.getElementById('resultEmpty').style.display = 'none';
  const out = document.getElementById('resultOutput');
  out.style.display = 'block';

  const e = emoji(topCrop);
  document.getElementById('res-crop-name').textContent = e + ' ' + topCrop;
  document.getElementById('res-score').textContent     = confidence;
  document.getElementById('res-bar').style.width       = confidence + '%';

  /* Local CROPS reference data */
  const localData = (typeof CROPS !== 'undefined')
    ? CROPS.find(c => c.name.toLowerCase() === topCrop.toLowerCase())
    : null;

  /* ── Ideal-range params ── */
  if (localData) {
    document.getElementById('r-temp').textContent = localData.T[0] + '–' + localData.T[1] + '°C';
    document.getElementById('r-rain').textContent = localData.R[0] + '–' + localData.R[1] + 'mm';
    document.getElementById('r-ph').textContent   = localData.pH[0] + '–' + localData.pH[1];
    document.getElementById('res-tip').textContent = localData.tip;

    /* ── Season card (growing season info) ── */
    const sc = document.getElementById('seasonCard');
    if (sc) {
      sc.style.display = 'flex';
      document.getElementById('seasonIcon').textContent = localData.altSeasonIcon;
      document.getElementById('seasonName').textContent = localData.altSeason + ' Season · ' + localData.name;
      document.getElementById('seasonDesc').textContent = localData.altSeasonDesc;
    }

    /* ── Season TIMING badge in result header ── */
    const timing = getTimingStatus(localData, NOW_MONTH);
    _renderTimingBadge(timing);

    /* ── Season-aware panel in result body ── */
    _renderSeasonPanel(timing, topCrop, alternatives);

  } else {
    const tipEl = document.getElementById('res-tip');
    if (tipEl) tipEl.textContent = 'Based on your soil and climate profile.';

    /* Hide season elements if no local data */
    const badge = document.getElementById('res-season-badge');
    if (badge) badge.style.display = 'none';
    const panel = document.getElementById('res-season-panel');
    if (panel) panel.style.display = 'none';
  }

  /* ── Soil-based alternatives (from ML model) ── */
  const altDiv   = document.getElementById('resAlts');
  const altChips = document.getElementById('altChips');
  if (altChips) {
    altChips.innerHTML = '';
    (alternatives || []).forEach(a => {
      const ch = document.createElement('span');
      ch.className   = 'alt-chip';
      ch.textContent = emoji(a.crop) + ' ' + a.crop + ' (' + a.confidence + '%)';
      altChips.appendChild(ch);
    });
  }
  if (altDiv) altDiv.style.display = 'block';

  /* ── Seasonal picks: what to plant THIS month ── */
  _renderSeasonalPicks();
}

/* Render the small inline badge inside the dark result header */
function _renderTimingBadge(timing) {
  const badge = document.getElementById('res-season-badge');
  if (!badge) return;
  if (!timing || !timing.label) { badge.style.display = 'none'; return; }

  badge.className = 'res-season-badge rsb-' + timing.status;
  badge.textContent = timing.label;
  badge.style.display = 'inline-flex';
}

/* Render the detailed warning/ok panel inside result body */
function _renderSeasonPanel(timing, cropName, alternatives) {
  const panel = document.getElementById('res-season-panel');
  if (!panel) return;
  if (!timing || !timing.detail) { panel.style.display = 'none'; return; }

  panel.className = 'season-aware-panel sap-' + timing.status;

  let html = `<div class="sap-message">${timing.detail}</div>`;

  /* For warning/late: suggest soil-compatible alternatives that ARE in season */
  if ((timing.status === 'warning' || timing.status === 'late') && alternatives && alternatives.length) {
    const inSeasonAlts = alternatives.filter(a => {
      const cd = (typeof CROPS !== 'undefined')
        ? CROPS.find(c => c.name.toLowerCase() === a.crop.toLowerCase())
        : null;
      if (!cd) return false;
      if (cd.isPerennial) return false;
      const t = getTimingStatus(cd, NOW_MONTH);
      return t.status === 'ideal' || t.status === 'soon';
    });

    if (inSeasonAlts.length) {
      html += `<div class="sap-alts-label">🌱 Soil-compatible crops you can sow now:</div>`;
      html += `<div class="sap-alt-chips">`;
      inSeasonAlts.forEach(a => {
        html += `<span class="alt-chip sap-alt-chip">${emoji(a.crop)} ${a.crop}</span>`;
      });
      html += `</div>`;
    }
  }

  panel.innerHTML = html;
  panel.style.display = 'block';
}

/* Module-level cache for seasonal picks tab */
let _spNow  = [];
let _spSoon = [];
let _spActiveTab = 'now';

/* Render the "What to plant this month" card below the season card */
function _renderSeasonalPicks() {
  const card  = document.getElementById('seasonalPicksCard');
  const chips = document.getElementById('sp-chips');
  const title = document.getElementById('sp-title');
  const icon  = document.getElementById('sp-season-icon');
  if (!card || !chips) return;

  const { now, soon } = getSeasonalCrops(NOW_MONTH);
  const season = getIndianSeason(NOW_MONTH);

  /* Cache for tab switching */
  _spNow  = now;
  _spSoon = soon;
  _spActiveTab = 'now';

  if (icon) icon.textContent = season.icon;
  if (title) title.textContent =
    `${MONTH_NAMES[NOW_MONTH]} · ${season.name} Season — What to sow now`;

  /* Update toggle button counts */
  _updateToggleCounts();

  /* Render default tab */
  _renderSpTab('now');

  card.style.display = 'block';
}

/* Update the count badges on each toggle button */
function _updateToggleCounts() {
  const btnNow  = document.getElementById('sp-btn-now');
  const btnSoon = document.getElementById('sp-btn-soon');
  if (btnNow) {
    const dot = btnNow.querySelector('.sp-legend-dot');
    btnNow.innerHTML = '';
    if (dot) btnNow.appendChild(dot);
    btnNow.insertAdjacentText('beforeend', 'Ideal now');
    if (_spNow.length) {
      const badge = document.createElement('span');
      badge.className = 'sp-toggle-count';
      badge.textContent = _spNow.length;
      btnNow.appendChild(badge);
    }
  }
  if (btnSoon) {
    const dot = btnSoon.querySelector('.sp-legend-dot');
    btnSoon.innerHTML = '';
    if (dot) btnSoon.appendChild(dot);
    btnSoon.insertAdjacentText('beforeend', 'Good next month');
    if (_spSoon.length) {
      const badge = document.createElement('span');
      badge.className = 'sp-toggle-count';
      badge.textContent = _spSoon.length;
      btnSoon.appendChild(badge);
    }
  }
}

/* Render chips for the given tab ('now' | 'soon') */
function _renderSpTab(tab) {
  const chips    = document.getElementById('sp-chips');
  const emptyMsg = document.getElementById('sp-empty-msg');
  if (!chips) return;

  const list = tab === 'now' ? _spNow : _spSoon;
  chips.innerHTML = '';

  if (list.length === 0) {
    chips.style.display = 'none';
    if (emptyMsg) {
      const nextM    = NOW_MONTH === 12 ? 1 : NOW_MONTH + 1;
      emptyMsg.textContent = tab === 'now'
        ? 'No major sowing crops ideal for this month. Try "Good next month" or check perennials like Banana, Papaya, or Coconut.'
        : `No additional sowing crops lined up for ${MONTH_NAMES[nextM]}. Check back closer to the season.`;
      emptyMsg.style.display = 'block';
    }
    return;
  }

  if (emptyMsg) emptyMsg.style.display = 'none';
  chips.style.display = 'flex';

  list.forEach(c => {
    const ch = document.createElement('span');
    ch.className   = tab === 'now'
      ? 'alt-chip sp-chip sp-chip-now'
      : 'alt-chip sp-chip sp-chip-soon';
    ch.title       = c.altSeasonDesc || '';
    ch.textContent = (c.emoji || '🌿') + ' ' + c.name;
    chips.appendChild(ch);
  });
}

/* Public: called by the toggle buttons in HTML */
function spSetTab(tab) {
  if (tab === _spActiveTab) return;
  _spActiveTab = tab;

  const btnNow  = document.getElementById('sp-btn-now');
  const btnSoon = document.getElementById('sp-btn-soon');

  if (btnNow)  btnNow.classList.toggle('active',  tab === 'now');
  if (btnSoon) btnSoon.classList.toggle('active',  tab === 'soon');

  _renderSpTab(tab);
}

/* ════════════════════════════════════════════════════════
   ERROR HELPER
════════════════════════════════════════════════════════ */
function showRecommendError(message) {
  const overlay = document.getElementById('loadingOverlay');
  if (overlay) overlay.classList.remove('active');
  showToast('❌ ' + message);
}

/* ════════════════════════════════════════════════════════
   MAIN FUNCTION  (called by Analyse button)
════════════════════════════════════════════════════════ */
async function runRecommendation() {
  if (!API.isLoggedIn()) {
    showToast('🔒 Please log in to use the Crop Advisor.');
    setTimeout(() => { window.location.href = '/login'; }, 1200);
    return;
  }

  const N  = parseFloat(document.getElementById('inp-N').value);
  const P  = parseFloat(document.getElementById('inp-P').value);
  const K  = parseFloat(document.getElementById('inp-K').value);
  const pH = parseFloat(document.getElementById('inp-pH').value);
  const T  = parseFloat(document.getElementById('inp-T').value);
  const H  = parseFloat(document.getElementById('inp-H').value);
  const R  = parseFloat(document.getElementById('inp-R').value);

  const invalids = [];
  if (isNaN(N) || N < 0   || N > 150)  invalids.push('Nitrogen (0–150)');
  if (isNaN(P) || P < 0   || P > 80)   invalids.push('Phosphorus (0–80)');
  if (isNaN(K) || K < 0   || K > 120)  invalids.push('Potassium (0–120)');
  if (isNaN(pH)|| pH < 0  || pH > 14)  invalids.push('pH (0–14)');
  if (isNaN(T) || T < 0   || T > 50)   invalids.push('Temperature (0–50°C)');
  if (isNaN(H) || H < 0   || H > 100)  invalids.push('Humidity (0–100%)');
  if (isNaN(R) || R < 0   || R > 300)  invalids.push('Rainfall (0–300mm)');

  if (invalids.length) {
    showToast('⚠️ Invalid values: ' + invalids.join(', '));
    return;
  }

  const overlay = document.getElementById('loadingOverlay');
  if (overlay) overlay.classList.add('active');

  try {
    const data = await API.recommend({ N, P, K, ph: pH, temperature: T, humidity: H, rainfall: R });
    if (overlay) overlay.classList.remove('active');
    renderResult(data.top_crop, data.confidence, data.alternatives);
    showToast('✅ Best match: ' + data.top_crop + ' (' + data.confidence + '%)');
  } catch (err) {
    if (overlay) overlay.classList.remove('active');
    if (err.status === 503) {
      showRecommendError('ML model not ready. Run: python models/train_crop.py --synthetic');
    } else if (err.status === 422 && err.errors) {
      showRecommendError(Object.values(err.errors)[0]);
    } else {
      showRecommendError(err.message || 'Recommendation failed. Please try again.');
    }
  }
}

/* Stamp season pill when the recommend page becomes visible */
document.addEventListener('DOMContentLoaded', () => {
  stampSeasonPill();
});
