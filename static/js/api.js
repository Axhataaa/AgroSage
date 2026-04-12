/* ═══════════════════════════════════════════════════════
   API.JS — Central API client
   ─────────────────────────────────────────────────────
   • BASE_URL auto-detects the correct Flask origin.
     - If served by Flask (port 5000/5001): same-origin.
     - Otherwise (Live Server, file://): -> localhost:5000.
   • Stores JWT in localStorage
   • Attaches Authorization header automatically
   • Normalises all errors into a consistent shape
   • Must be the FIRST script loaded
═══════════════════════════════════════════════════════ */

const API = (() => {

  /* ── Config ────────────────────────────────────────── */
  // Auto-detect: if the page is served by Flask (port 5000/5001),
  // use same-origin requests. If opened via VS Code Live Server,
  // file://, or any other port, point directly at Flask on :5000.
  const FLASK_PORT = '5000';
  const BASE_URL   = (window.location.port === FLASK_PORT ||
                      window.location.port === '5001')
                     ? ''
                     : `http://localhost:${FLASK_PORT}`;
  const TOKEN_KEY = 'agrosage_token';
  const USER_KEY  = 'agrosage_user';

  /* ── Token helpers ─────────────────────────────────── */
  function getToken()        { return localStorage.getItem(TOKEN_KEY); }
  function setToken(t)       { localStorage.setItem(TOKEN_KEY, t); }
  function clearToken()      { localStorage.removeItem(TOKEN_KEY); }

  function getStoredUser() {
    try { return JSON.parse(localStorage.getItem(USER_KEY)); }
    catch { return null; }
  }
  function setStoredUser(u)  { localStorage.setItem(USER_KEY, JSON.stringify(u)); }
  function clearStoredUser() { localStorage.removeItem(USER_KEY); }

  /* ── Core fetch wrapper ────────────────────────────── */
  async function request(method, path, body = null, isFormData = false) {
    const headers = {};
    if (!isFormData) headers['Content-Type'] = 'application/json';

    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const opts = { method, headers };
    if (body) {
      opts.body = isFormData ? body : JSON.stringify(body);
    }

    let res;
    try {
      res = await fetch(`${BASE_URL}${path}`, opts);
    } catch (networkErr) {
      throw { message: 'Cannot reach the server. Is Flask running on port 5000?', code: 'NETWORK_ERROR' };
    }

    /* Token expired / invalid → clear and redirect to login */
    if (res.status === 401) {
      clearToken();
      clearStoredUser();
      // FIX: Was 'login.html' — must use Flask route '/login'
      sessionStorage.setItem('agrosage_after_login', window._currentPage || 'recommend');
      window.location.href = '/login';
      return;
    }

    let data;
    try { data = await res.json(); }
    catch { data = { success: false, message: `Server returned ${res.status}` }; }

    if (!res.ok) {
      const msg = data.message
        || (data.errors ? Object.values(data.errors)[0] : null)
        || `Request failed (${res.status})`;
      throw { message: msg, errors: data.errors || null, status: res.status };
    }

    return data;
  }

  /* ── Convenience methods ───────────────────────────── */
  const get      = (path)         => request('GET',  path);
  const post     = (path, body)   => request('POST', path, body);
  const postForm = (path, fd)     => request('POST', path, fd, true);

  /* ── Auth calls ────────────────────────────────────── */
  async function login(email, password) {
    const data = await post('/api/auth/login', { email, password });
    setToken(data.token);
    setStoredUser(data.user);
    return data.user;
  }

  async function signup(name, email, password) {
    const data = await post('/api/auth/signup', { name, email, password });
    setToken(data.token);
    setStoredUser(data.user);
    return data.user;
  }

  async function logout() {
    clearToken();
    clearStoredUser();
    // FIX: Was 'index.html' — must use Flask route '/'
    window.location.href = '/';
  }

  async function fetchMe() {
    try {
      const data = await get('/api/auth/me');
      setStoredUser(data.user);
      return data.user;
    } catch {
      clearToken();
      clearStoredUser();
      return null;
    }
  }

  /* ── Feature calls ─────────────────────────────────── */
  async function recommend(params) {
    return post('/api/recommend', params);
  }

  async function history(page = 1) {
    return get(`/api/history?page=${page}`);
  }

  async function detect(imageFile) {
    const fd = new FormData();
    fd.append('image', imageFile);
    return postForm('/api/detect', fd);
  }

  async function weather(lat, lon) {
    return get(`/api/weather?lat=${lat}&lon=${lon}`);
  }

  async function soil(lat, lon) {
    return get(`/api/soil?lat=${lat}&lon=${lon}`);
  }

  async function importance() {
    return get('/api/importance');
  }

  async function health() {
    return get('/api/health');
  }

  /* ── Public surface ────────────────────────────────── */
  return {
    getToken, getStoredUser, isLoggedIn: () => !!getToken(),
    login, signup, logout, fetchMe,
    recommend, history, detect, weather, soil, importance, health,
  };

})();
