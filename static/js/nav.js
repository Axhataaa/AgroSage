/* ═══════════════════════════════════════════════════════
   NAVIGATION — SINGLE SOURCE OF TRUTH
   All page switching, active states, and footer behaviour
   are handled exclusively here. Do NOT duplicate this logic.
═══════════════════════════════════════════════════════ */

function showPage(id) {
  /* ── 1. Switch pages ── */
  document.querySelectorAll('.page').forEach(p => {
    p.classList.remove('active');
  });

  const target = document.getElementById('page-' + id);
  if (!target) { console.warn('[nav] Unknown page:', id); return; }
  target.classList.add('active');

  /* ── 2. Scroll to top ── */
  window.scrollTo({ top: 0, behavior: 'smooth' });

  /* ── 3. Sync nav link active states ── */
  const labelMap = {
    home:      'Home',
    recommend: 'Crop Advisor',
    soil:      'Soil Guide',
    browse:    'Explore',
    dashboard: 'Analytics',
    insights:  'Insights',
    detect:    'Disease Check'
  };

  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.toggle(
      'active',
      link.textContent.trim() === labelMap[id]
    );
  });

  /* ── 4. Footer mode ── */
  const footer = document.getElementById('footer');
  if (footer) {
    if (id === 'home') {
      footer.classList.remove('footer-compact');
      footer.classList.add('footer-full');
    } else {
      footer.classList.remove('footer-full');
      footer.classList.add('footer-compact');
    }
  }

  /* ── 5. Lazy-init feature modules ── */
  if (id === 'dashboard') initCharts();
  if (id === 'browse')    renderCropGrid('all');
}
