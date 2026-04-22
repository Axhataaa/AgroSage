/* ═══════════════════════════════════════════════════════
   CROP BROWSE GRID
═══════════════════════════════════════════════════════ */
function renderCropGrid(filter) {
  const grid = document.getElementById('cropGrid');
  grid.innerHTML = '';

  const filtered = filter === 'all'
    ? CROPS
    : CROPS.filter(c => c.season === filter || c.type === filter);

  filtered.forEach(c => {
    const card = document.createElement('div');
    card.className = 'crop-card';
    card.style.animationDelay = (filtered.indexOf(c) * 0.05) + 's';

    card.innerHTML = `
      <div class="crop-thumb" style="background:${c.bg}">${c.emoji}</div>
      <div class="crop-card-body">
        <div class="crop-card-name">${c.name}</div>
        <div class="crop-card-season">📅 ${c.altSeason || c.season}</div>
        <div class="crop-card-tags">
          <span class="crop-tag tag-${c.season}">${c.season.charAt(0).toUpperCase() + c.season.slice(1)}</span>
          <span class="crop-tag tag-soil">pH ${c.pH[0]}–${c.pH[1]}</span>
          <span class="crop-tag tag-climate">${c.T[0]}–${c.T[1]}°C</span>
        </div>
      </div>`;

    /* Clicking a crop card pre-fills the recommendation form */
    card.onclick = () => {
      const midVal = (arr) => Math.round((arr[0] + arr[1]) / 2);
      const setAndSync = (id, val) => {
        const inp = document.getElementById('inp-' + id);
        if (inp) { inp.value = val; if (typeof syncSlider === 'function') syncSlider(id); }
      };
      setAndSync('N',  midVal(c.N));
      setAndSync('P',  midVal(c.P));
      setAndSync('K',  midVal(c.K));
      setAndSync('pH', ((c.pH[0] + c.pH[1]) / 2).toFixed(1));
      setAndSync('T',  midVal(c.T));
      setAndSync('H',  midVal(c.H));
      setAndSync('R',  midVal(c.R));
      showToast('🌾 Parameters set for ' + c.name);
      showPage('recommend');
    };

    grid.appendChild(card);
  });
}

function filterCrops(filter, btn) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderCropGrid(filter);
}
