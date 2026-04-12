/* ═══════════════════════════════════════════════════════
   AUTH.JS — Authentication state + nav rendering
   ─────────────────────────────────────────────────────
   Reads JWT / user from API (localStorage).
   api.js must be loaded before this file.

   FIXES APPLIED:
     • requireAuth  → redirects to '/login'   (was 'login.html')
     • navLoginBtn  → navigates to '/login'   (was 'login.html')
     • navSignupBtn → navigates to '/signup'  (was 'signup.html')
═══════════════════════════════════════════════════════ */

const Auth = (() => {

  function getUser()    { return API.getStoredUser(); }
  function isLoggedIn() { return API.isLoggedIn(); }

  /* ── Redirect guard: send unauthenticated users to login ── */
  function requireAuth(intendedAction) {
    if (!isLoggedIn()) {
      sessionStorage.setItem('agrosage_after_login', intendedAction || 'recommend');
      // FIX: Was 'login.html' — must use Flask page route
      window.location.href = '/login';
      return false;
    }
    return true;
  }

  /* ── Resume the page the user originally wanted ── */
  function resumeAfterLogin() {
    const dest = sessionStorage.getItem('agrosage_after_login') || 'recommend';
    sessionStorage.removeItem('agrosage_after_login');
    return dest;
  }

  async function login(email, password)        { return API.login(email, password); }
  async function signup(name, email, password) { return API.signup(name, email, password); }
  function logout()                            { return API.logout(); }

  return { getUser, isLoggedIn, requireAuth, resumeAfterLogin, login, signup, logout };

})();

/* ═══════════════════════════════════════════════════════
   NAV AUTH RENDERING
═══════════════════════════════════════════════════════ */
function renderNavAuth() {
  const container = document.getElementById('navAuth');
  if (!container) return;

  if (Auth.isLoggedIn()) {
    const user     = Auth.getUser();
    const initials = user && user.name ? user.name.charAt(0).toUpperCase() : '?';
    const name     = user ? user.name : 'User';
    container.innerHTML = `
      <div class="nav-user-chip" id="navUserChip" title="Click to sign out">
        <div class="nav-user-avatar">${initials}</div>
        <span class="nav-user-name">${name}</span>
      </div>`;
    document.getElementById('navUserChip')
      .addEventListener('click', () => Auth.logout());
  } else {
    container.innerHTML = `
      <button class="nav-btn-login"  id="navLoginBtn">Log In</button>
      <button class="nav-btn-signup" id="navSignupBtn">Sign Up</button>`;
    // FIX: Was 'login.html' / 'signup.html' — use Flask page routes
    document.getElementById('navLoginBtn')
      .addEventListener('click', () => { window.location.href = '/login'; });
    document.getElementById('navSignupBtn')
      .addEventListener('click', () => { window.location.href = '/signup'; });
  }
}

/* ── Hero CTA: require login then go to recommend page ── */
function handleDetectCTA() {
  if (Auth.requireAuth('recommend')) {
    showPage('recommend');
  }
}

document.addEventListener('DOMContentLoaded', renderNavAuth);
