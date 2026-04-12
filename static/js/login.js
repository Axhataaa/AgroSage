/* ═══════════════════════════════════════════════════════
   LOGIN PAGE CONTROLLER
   ─────────────────────────────────────────────────────
   FIXES:
     • Redirect for already-logged-in users: '/' (was 'index.html')
     • Post-login redirect: '/'              (was 'index.html')
═══════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {

  // FIX: Was 'index.html' — use Flask route
  if (Auth.isLoggedIn()) { window.location.href = '/'; return; }

  const form     = document.getElementById('loginForm');
  const emailEl  = document.getElementById('loginEmail');
  const passEl   = document.getElementById('loginPassword');
  const toggleEl = document.getElementById('toggleLoginPass');
  const btnEl    = document.getElementById('loginBtn');
  const btnText  = document.getElementById('loginBtnText');
  const errorEl  = document.getElementById('loginError');

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
    btnText.textContent = on ? 'Logging in…' : 'Log In →';
    btnEl.style.opacity = on ? '0.75' : '1';
  }

  if (!form) return;

  form.addEventListener('submit', async e => {
    e.preventDefault();
    clearError();

    const email    = emailEl.value.trim();
    const password = passEl.value;

    if (!email)    { showError('Please enter your email address.'); emailEl.focus(); return; }
    if (!password) { showError('Please enter your password.');       passEl.focus();  return; }

    setLoading(true);
    try {
      await Auth.login(email, password);
      // After login, go to the page they originally wanted, or home
      const dest = Auth.resumeAfterLogin();  // e.g. 'recommend', 'detect'
      // FIX: Was 'index.html' — use Flask route '/'
      window.location.href = '/';
    } catch (err) {
      showError(err.message || 'Login failed. Please check your credentials.');
      setLoading(false);
    }
  });
});
