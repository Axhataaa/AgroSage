/* ═══════════════════════════════════════════════════════
   SLIDER ↔ INPUT SYNC  +  visual fill tracking
   ─────────────────────────────────────────────────────
   All sliders now use real-value ranges — pH uses
   min="3.5" max="9.5" step="0.1" directly.
   The syncInputPH() ×10 workaround is gone.

   _updateSliderFill() writes --_pct to the slider so the
   CSS two-colour gradient tracks the thumb position.
═══════════════════════════════════════════════════════ */

function _updateSliderFill(sl) {
  if (!sl) return;
  const min = parseFloat(sl.min) || 0;
  const max = parseFloat(sl.max) || 100;
  const val = parseFloat(sl.value);
  const pct = Math.min(100, Math.max(0, ((val - min) / (max - min)) * 100));
  sl.style.setProperty('--_pct', pct.toFixed(2) + '%');
}

/* number input → slider */
function syncSlider(id) {
  const inp = document.getElementById('inp-' + id);
  const sl  = document.getElementById('sl-'  + id);
  if (!sl || !inp) return;
  sl.value = inp.value;
  _updateSliderFill(sl);
}

/* slider → number input */
function syncInput(id) {
  const sl  = document.getElementById('sl-'  + id);
  const inp = document.getElementById('inp-' + id);
  if (!sl || !inp) return;
  // For decimal sliders (pH, future) preserve step precision
  const step = parseFloat(sl.step) || 1;
  inp.value = step < 1 ? parseFloat(sl.value).toFixed(1) : sl.value;
  _updateSliderFill(sl);
}

/* Wire up T, H, R climate sliders and init all fills on load */
document.addEventListener('DOMContentLoaded', () => {
  ['T', 'H', 'R'].forEach(id => {
    const inp = document.getElementById('inp-' + id);
    const sl  = document.getElementById('sl-'  + id);
    if (inp && sl) {
      inp.addEventListener('input', () => { sl.value = inp.value; _updateSliderFill(sl); });
      sl.addEventListener('input',  () => { inp.value = sl.value; _updateSliderFill(sl); });
    }
  });

  // Init fill gradient for every slider at page-load values
  document.querySelectorAll('.param-slider').forEach(_updateSliderFill);
});
