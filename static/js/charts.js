/* ═══════════════════════════════════════════════════════
   ANALYTICS DASHBOARD — CHARTS
   ─────────────────────────────────────────────────────
   All parameter-influence data is fetched from the backend
   GET /api/importance  (no hardcoded values).
   The three crop charts use static agronomic reference data
   which rarely changes and doesn't need to be dynamic.
═══════════════════════════════════════════════════════ */
let chartsInit = false;

function initCharts() {
  if (chartsInit) return;
  chartsInit = true;

  /* ── Chart 1: Nitrogen Requirements by Crop ── */
  new Chart(document.getElementById('chartNitrogen'), {
    type: 'bar',
    data: {
      labels: ['Rice', 'Wheat', 'Maize', 'Cotton', 'Sugarcane', 'Chickpea', 'Mustard', 'Banana'],
      datasets: [
        {
          label: 'Min N (kg/ha)',
          data: [60, 50, 60, 60, 80, 15, 40, 80],
          backgroundColor: 'rgba(140,197,160,0.5)',
          borderColor: 'rgba(90,138,106,0.8)',
          borderWidth: 2,
          borderRadius: 6
        },
        {
          label: 'Max N (kg/ha)',
          data: [100, 90, 120, 120, 140, 40, 80, 140],
          backgroundColor: 'rgba(201,146,58,0.5)',
          borderColor: 'rgba(201,146,58,0.8)',
          borderWidth: 2,
          borderRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { labels: { color: 'rgba(247,242,232,0.8)', font: { family: 'DM Sans' } } }
      },
      scales: {
        x: { ticks: { color: 'rgba(247,242,232,0.6)' }, grid: { color: 'rgba(247,242,232,0.05)' } },
        y: {
          ticks: { color: 'rgba(247,242,232,0.6)' },
          grid:  { color: 'rgba(247,242,232,0.05)' },
          title: { display: true, text: 'N (kg/ha)', color: 'rgba(247,242,232,0.5)' }
        }
      }
    }
  });

  /* ── Chart 2: Rainfall Requirements by Crop ── */
  new Chart(document.getElementById('chartRainfall'), {
    type: 'bar',
    data: {
      labels: ['Rice', 'Banana', 'Sugarcane', 'Maize', 'Cotton', 'Wheat', 'Mustard', 'Chickpea'],
      datasets: [{
        label: 'Annual Rainfall (mm)',
        data: [225, 150, 175, 140, 105, 75, 50, 60],
        backgroundColor: [
          'rgba(140,197,160,0.7)', 'rgba(232,184,75,0.7)',  'rgba(90,138,106,0.7)',
          'rgba(201,146,58,0.7)',  'rgba(139,94,60,0.7)',   'rgba(200,200,150,0.7)',
          'rgba(180,200,130,0.7)', 'rgba(220,180,120,0.7)'
        ],
        borderRadius: 8,
        borderSkipped: false
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: 'rgba(247,242,232,0.6)' }, grid: { color: 'rgba(247,242,232,0.05)' } },
        y: { ticks: { color: 'rgba(247,242,232,0.6)' }, grid: { color: 'rgba(247,242,232,0.05)' } }
      }
    }
  });

  /* ── Chart 3: pH Preference (Radar) ── */
  new Chart(document.getElementById('chartPH'), {
    type: 'radar',
    data: {
      labels: ['Rice', 'Wheat', 'Maize', 'Chickpea', 'Sugarcane', 'Cotton', 'Mango'],
      datasets: [{
        label: 'Ideal pH Midpoint',
        data: [6.25, 6.75, 6.65, 7.25, 7.25, 6.9, 6.5],
        backgroundColor: 'rgba(140,197,160,0.25)',
        borderColor: 'rgba(140,197,160,0.8)',
        pointBackgroundColor: 'rgba(232,184,75,0.9)',
        pointBorderColor: 'rgba(247,242,232,0.8)',
        borderWidth: 2,
        pointRadius: 5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { labels: { color: 'rgba(247,242,232,0.8)', font: { family: 'DM Sans' } } }
      },
      scales: {
        r: {
          ticks:       { color: 'rgba(247,242,232,0.5)', backdropColor: 'transparent', stepSize: 1 },
          grid:        { color: 'rgba(247,242,232,0.08)' },
          angleLines:  { color: 'rgba(247,242,232,0.08)' },
          pointLabels: { color: 'rgba(247,242,232,0.7)', font: { family: 'DM Sans' } },
          min: 5.5,
          max: 8
        }
      }
    }
  });

  /* ── Parameter Influence Bars — backend-driven ── */
  loadParameterInfluence();
}

/* ── Colour palette for influence bars ── */
const PI_COLORS = {
  ph:          'var(--gold)',
  N:           'var(--mint)',
  temperature: 'var(--amber)',
  rainfall:    '#7EC8E3',
  P:           'var(--sage)',
  humidity:    '#B8D4C8',
  K:           'var(--earth)',
};

function _renderInfluenceBars(features, source) {
  const cont = document.getElementById('piRows');
  if (!cont) return;

  cont.innerHTML = '';

  /* Source badge */
  const badge = document.createElement('p');
  badge.style.cssText = 'font-size:0.72rem;color:rgba(247,242,232,0.4);margin:0 0 0.8rem;text-transform:uppercase;letter-spacing:0.05em;';
  badge.textContent = source === 'model'
    ? '⚙️ Computed from trained RandomForest model'
    : '📚 Reference values (model not loaded)';
  cont.appendChild(badge);

  features.forEach(f => {
    const color = PI_COLORS[f.key] || 'var(--mint)';
    const row   = document.createElement('div');
    row.className = 'pi-row';
    row.innerHTML = `
      <div class="pi-name">${f.label}</div>
      <div class="pi-bar-bg">
        <div class="pi-bar-fill" style="width:${f.pct}%;background:${color};transition:width 0.8s ease"></div>
      </div>
      <div class="pi-pct">${f.pct}%</div>`;
    cont.appendChild(row);

    /* Animate bar in after a frame */
    requestAnimationFrame(() => {
      const fill = row.querySelector('.pi-bar-fill');
      if (fill) { fill.style.width = '0'; setTimeout(() => { fill.style.width = f.pct + '%'; }, 50); }
    });
  });
}

async function loadParameterInfluence() {
  const cont = document.getElementById('piRows');
  if (!cont) return;

  /* Loading state */
  cont.innerHTML = '<p style="color:rgba(247,242,232,0.4);font-size:0.85rem;padding:0.5rem 0">Loading feature importance…</p>';

  try {
    const data = await API.importance();
    _renderInfluenceBars(data.features, data.source);
  } catch (err) {
    /* Graceful degradation: show static fallback with error note */
    console.warn('Could not load feature importance from backend:', err.message);
    const fallback = [
      { key:'ph',          label:'Soil pH',      pct:82 },
      { key:'N',           label:'Nitrogen',      pct:78 },
      { key:'temperature', label:'Temperature',   pct:76 },
      { key:'rainfall',    label:'Rainfall',      pct:68 },
      { key:'P',           label:'Phosphorus',    pct:65 },
      { key:'humidity',    label:'Humidity',      pct:54 },
      { key:'K',           label:'Potassium',     pct:50 },
    ];
    _renderInfluenceBars(fallback, 'fallback');
  }
}
