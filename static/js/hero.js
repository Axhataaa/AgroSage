/* ═══════════════════════════════════════════════════════
   HERO — FLOATING LEAVES ANIMATION
═══════════════════════════════════════════════════════ */
(function initLeaves() {
  const canvas = document.getElementById('heroCanvas');
  const emojis = ['🌿', '🍃', '🌾', '🌱', '🍀', '🌻'];
  for (let i = 0; i < 18; i++) {
    const el = document.createElement('div');
    el.className = 'leaf-float';
    el.textContent = emojis[Math.floor(Math.random() * emojis.length)];
    el.style.left              = Math.random() * 100 + '%';
    el.style.animationDuration = (12 + Math.random() * 18) + 's';
    el.style.animationDelay    = (-Math.random() * 30) + 's';
    el.style.fontSize          = (1 + Math.random() * 1.5) + 'rem';
    canvas.appendChild(el);
  }
})();
