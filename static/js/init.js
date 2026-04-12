/* ═══════════════════════════════════════════════════════
   APP INIT — boot sequence
   nav.js must be loaded before this file.
═══════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  /* Boot to Home — showPage handles footer + active nav state */
  showPage('home');
});
