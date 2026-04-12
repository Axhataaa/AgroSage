/* ═══════════════════════════════════════════════════════
   TOAST NOTIFICATIONS
═══════════════════════════════════════════════════════ */
let toastTimer;

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent   = msg;
  t.style.display = 'flex';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.style.display = 'none'; }, 3500);
}
