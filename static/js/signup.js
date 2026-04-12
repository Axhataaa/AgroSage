/* ═══════════════════════════════════════════════════════
   SIGNUP PAGE CONTROLLER
   ─────────────────────────────────────────────────────
   FIXES:
     • Redirect for already-logged-in users: '/' (was 'index.html')
     • Post-signup redirect: '/'              (was 'index.html')
═══════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {

  // FIX: Was 'index.html' — use Flask route
  if (Auth.isLoggedIn()) { window.location.href = '/'; return; }

  const form     = document.getElementById('signupForm');
  const nameEl   = document.getElementById('signupName');
  const emailEl  = document.getElementById('signupEmail');
  const passEl   = document.getElementById('signupPassword');
  const toggleEl = document.getElementById('toggleSignupPass');
  const btnEl    = document.getElementById('signupBtn');
  const btnText  = document.getElementById('signupBtnText');
  const errorEl  = document.getElementById('signupError');

  /* Password visibility toggle */
  if (toggleEl) {
    toggleEl.addEventListener('click', () => {
      const hidden     = passEl.type === 'password';
      passEl.type      = hidden ? 'text' : 'password';
      toggleEl.textContent = hidden ? 'Hide' : 'Show';
    });
  }

  function showError(msg) {
    errorEl.textContent = msg;
    errorEl.classList.add('visible');
  }
  function clearError() {
    errorEl.textContent = '';
    errorEl.classList.remove('visible');
  }
  function setLoading(on) {
    btnEl.disabled      = on;
    btnText.textContent = on ? 'Creating account…' : 'Create Account →';
    btnEl.style.opacity = on ? '0.75' : '1';
  }
  function isValidEmail(v) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v); }

  if (!form) return;

  form.addEventListener('submit', async e => {
    e.preventDefault();
    clearError();

    const name     = nameEl.value.trim();
    const email    = emailEl.value.trim();
    const password = passEl.value;

    if (!name)                { showError('Please enter your full name.');            nameEl.focus();  return; }
    if (!isValidEmail(email)) { showError('Please enter a valid email address.');     emailEl.focus(); return; }
    if (password.length < 6)  { showError('Password must be at least 6 characters.'); passEl.focus(); return; }

    setLoading(true);
    try {
      await Auth.signup(name, email, password);
      // FIX: Was 'index.html' — use Flask route '/'
      window.location.href = '/';
    } catch (err) {
      showError(err.message || 'Sign up failed. Please try again.');
      setLoading(false);
    }
  });
});
