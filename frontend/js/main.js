/**
 * CyberShield — main.js
 * Shared JS loaded on every authenticated page.
 * Handles: session check, user info in sidebar, greeting, theme toggle.
 */

const API = 'http://localhost:5000';

// ── Dark mode toggle ─────────────────────────────────────────
// Applies/removes data-theme="dark" on <html>, which the CSS in
// css/style.css uses to swap the content-area color tokens (see
// the [data-theme="dark"] block there). Persisted in localStorage
// so it stays applied across pages and reloads.
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  const icon = document.getElementById('theme-icon');
  if (icon) {
    icon.classList.remove('fa-moon', 'fa-sun');
    icon.classList.add(theme === 'dark' ? 'fa-sun' : 'fa-moon');
  }
}

function toggleTheme() {
  const current = localStorage.getItem('cs_theme') || 'light';
  const next    = current === 'dark' ? 'light' : 'dark';
  localStorage.setItem('cs_theme', next);
  applyTheme(next);
}

// Apply saved theme immediately (before other init) to avoid a
// flash of the wrong theme on page load.
applyTheme(localStorage.getItem('cs_theme') || 'light');

function initSidebarToggle() {
  const topbar = document.querySelector('.topbar');
  const sidebar = document.querySelector('.sidebar');
  if (!topbar || !sidebar) return;

  const toggle = document.createElement('button');
  toggle.type = 'button';
  toggle.className = 'sidebar-toggle';
  toggle.setAttribute('aria-label', 'Toggle navigation menu');
  toggle.setAttribute('aria-expanded', 'true');
  toggle.innerHTML = '<i class="fa-solid fa-bars"></i>';

  const right = topbar.querySelector('.topbar-right');
  let left = topbar.querySelector('.topbar-left');
  if (!left) {
    const title = topbar.querySelector('.topbar-title');
    left = document.createElement('div');
    left.className = 'topbar-left';
    topbar.insertBefore(left, right || topbar.firstChild);
    if (title) left.appendChild(title);
  }
  left.prepend(toggle);

  const backdrop = document.createElement('button');
  backdrop.type = 'button';
  backdrop.className = 'sidebar-backdrop';
  backdrop.setAttribute('aria-label', 'Close navigation menu');
  document.body.appendChild(backdrop);

  const isMobile = () => window.matchMedia('(max-width: 660px)').matches;
  const closeMobileMenu = () => document.documentElement.classList.remove('sidebar-mobile-open');
  const syncButton = () => {
    const expanded = isMobile()
      ? document.documentElement.classList.contains('sidebar-mobile-open')
      : !document.documentElement.classList.contains('sidebar-collapsed');
    toggle.setAttribute('aria-expanded', String(expanded));
  };

  if (localStorage.getItem('cs_sidebar_collapsed') === 'true' && !isMobile()) {
    document.documentElement.classList.add('sidebar-collapsed');
  }
  syncButton();
  toggle.addEventListener('click', () => {
    if (isMobile()) {
      document.documentElement.classList.toggle('sidebar-mobile-open');
    } else {
      document.documentElement.classList.toggle('sidebar-collapsed');
      localStorage.setItem('cs_sidebar_collapsed', String(document.documentElement.classList.contains('sidebar-collapsed')));
    }
    syncButton();
  });
  backdrop.addEventListener('click', () => { closeMobileMenu(); syncButton(); });
  window.addEventListener('resize', () => { closeMobileMenu(); syncButton(); });
}

initSidebarToggle();

// ── Session check ────────────────────────────────────────────
// Firebase Authentication is the sole session source.
(async function checkSession() {
  const publicPages = ['index.html', 'login.html', 'register.html', 'forgot_password.html', 'reset_password.html'];
  const page = window.location.pathname.split('/').pop();
  const isGuest = localStorage.getItem('cs_guest') === 'true';
  if (isGuest) {
    const guestRestrictedPages = ['profile.html', 'history.html', 'reports.html'];
    if (guestRestrictedPages.includes(page)) {
      window.location.replace('dashboard.html');
      return;
    }
    sessionStorage.setItem('cs_user', JSON.stringify({ id: 'guest', name: 'Guest User', email: '' }));
    const avatarEl = document.getElementById('user-avatar');
    const nameEl = document.getElementById('user-name');
    if (avatarEl) avatarEl.textContent = 'G';
    if (nameEl) nameEl.textContent = 'Guest User';
    document.querySelectorAll(
      'a[href="profile.html"], a[href="history.html"], a[href="reports.html"]'
    ).forEach(link => {
      link.setAttribute('aria-disabled', 'true');
      link.style.opacity = '.45';
      link.style.pointerEvents = 'none';
      link.title = 'This section is unavailable for guest users';
    });
    return;
  }
  const fb = await window.firebaseReady;
  await new Promise(resolve => fb.onAuthStateChanged(fb.auth, resolve));
  if (!fb.auth.currentUser && !publicPages.includes(page)) window.location.href = 'login.html';
  if (fb.auth.currentUser) {
    const name = fb.auth.currentUser.displayName || fb.auth.currentUser.email || 'User';
    sessionStorage.setItem('cs_user', JSON.stringify({ id: fb.auth.currentUser.uid, name, email: fb.auth.currentUser.email }));
    const avatarEl = document.getElementById('user-avatar');
    const nameEl = document.getElementById('user-name');
    if (avatarEl) avatarEl.textContent = name[0].toUpperCase();
    if (nameEl) nameEl.textContent = name;
  }
})();

// ── Set user info in sidebar ─────────────────────────────────
document.querySelectorAll('[data-logout]').forEach(link => link.addEventListener('click', async event => {
  event.preventDefault();
  localStorage.removeItem('cs_guest');
  const fb = await window.firebaseReady;
  await fb.signOut(fb.auth);
  sessionStorage.removeItem('cs_user');
  window.location.href = 'login.html';
}));

// ── Greeting ─────────────────────────────────────────────────
(function setGreeting() {
  const el = document.getElementById('greeting');
  if (!el) return;
  const h = new Date().getHours();
  el.innerHTML = h < 12 ? 'Good morning <i class="fa-solid fa-hand"></i>' : h < 18 ? 'Good afternoon <i class="fa-solid fa-hand"></i>' : 'Good evening <i class="fa-solid fa-hand"></i>';
})();

// ── Utility: show toast notification ────────────────────────
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  const colors = { info: '#0891B2', success: '#059669', error: '#DC2626', warning: '#D97706' };
  toast.style.cssText = `
    position:fixed; bottom:24px; right:24px; z-index:9999;
    background:${colors[type] || colors.info}; color:white;
    padding:12px 20px; border-radius:10px; font-size:14px;
    font-family:'Inter',sans-serif; font-weight:500;
    box-shadow:0 8px 24px rgba(0,0,0,0.15);
    animation: slideIn .3s ease;
  `;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

// ── Utility: format date ─────────────────────────────────────
function formatDate(isoString) {
  if (!isoString) return '—';
  return new Date(isoString).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
}

// ── Utility: risk class from score ───────────────────────────
function riskClass(score) {
  return score >= 70 ? 'risk-high' : score >= 40 ? 'risk-medium' : 'risk-low';
}
