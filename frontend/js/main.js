/**
 * CyberShield — main.js
 * Shared JS loaded on every authenticated page.
 * Handles: session check, user info in sidebar, greeting, theme toggle.
 */

const API = 'http://localhost:5000';

function applySidebarAvatar(element, photo, fallback) {
  if (!element) return;
  element.replaceChildren();
  if (photo) {
    const image = document.createElement('img');
    image.src = photo;
    image.alt = 'Profile photo';
    image.style.cssText = 'width:100%;height:100%;border-radius:50%;object-fit:cover;display:block';
    element.appendChild(image);
  } else element.textContent = fallback;
}

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

  let toggle = topbar.querySelector('.sidebar-toggle');
  if (!toggle) {
    toggle = document.createElement('button');
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
  }

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

function updateAdminNavigation(isAdmin, page) {
  // The link is created only after Firebase confirms the custom claim. This
  // keeps the normal navigation clean and avoids treating a client-side field
  // as an authorization source.
  document.querySelectorAll('[data-admin-nav]').forEach(link => link.remove());
  if (!isAdmin || page === 'admin.html') return;

  const accountSection = Array.from(document.querySelectorAll('.sidebar-section'))
    .find(section => section.textContent.trim().toLowerCase() === 'account');
  if (!accountSection) return;

  const adminLink = document.createElement('a');
  adminLink.href = 'admin.html';
  adminLink.className = 'nav-item';
  adminLink.dataset.adminNav = 'true';
  adminLink.innerHTML = '<span class="nav-icon"><i class="fa-solid fa-shield-halved"></i></span>Admin Panel';
  accountSection.parentNode.insertBefore(adminLink, accountSection);
}

// ── Session check ────────────────────────────────────────────
// Firebase Authentication is the sole session source.
(async function checkSession() {
  const publicPages = ['index.html', 'login.html', 'register.html', 'forgot_password.html', 'reset_password.html'];
  const page = window.location.pathname.split('/').pop();
  const isGuest = localStorage.getItem('cs_guest') === 'true';
  if (isGuest) {
    const guestRestrictedPages = ['profile.html', 'history.html', 'reports.html', 'admin.html'];
    if (guestRestrictedPages.includes(page)) {
      window.location.replace('dashboard.html');
      return;
    }
    sessionStorage.setItem('cs_user', JSON.stringify({ id: 'guest', name: 'Guest User', email: '', role: 'guest' }));
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
  const user = fb.auth.currentUser;
  if (!user) {
    if (!publicPages.includes(page)) window.location.replace('login.html');
    return;
  }

  let isAdmin = false;
  try {
    const token = await fb.getIdTokenResult(user);
    isAdmin = token.claims.admin === true;
  } catch (error) {
    console.error('Could not verify the Firebase role claim.', error);
    if (page === 'admin.html') window.location.replace('login.html');
    return;
  }

  if (page === 'admin.html' && !isAdmin) {
    window.location.replace('dashboard.html');
    return;
  }

  updateAdminNavigation(isAdmin, page);
  if (page === 'admin.html') document.documentElement.classList.remove('admin-access-pending');

  {
    const name = user.displayName || user.email || 'User';
    const role = isAdmin ? 'admin' : 'user';
    // Keep the signed-in account's activity visible to the admin console.
    // This is best-effort so a temporary Firestore permission/network issue
    // never prevents the user from entering the application.
    fb.setDoc(fb.doc(fb.db, 'users', user.uid), {
      email: user.email,
      displayName: name,
      lastLogin: user.metadata?.lastSignInTime || new Date().toISOString()
    }, { merge: true }).catch(error => console.warn('Could not update last login:', error));
    sessionStorage.setItem('cs_user', JSON.stringify({ id: user.uid, name, email: user.email, role }));
    const avatarEl = document.getElementById('user-avatar');
    const nameEl = document.getElementById('user-name');
    const cachedAvatar = sessionStorage.getItem('cs_avatar') || '';
    applySidebarAvatar(avatarEl, cachedAvatar, name[0].toUpperCase());
    // Load the saved photo for a fresh tab/page, while keeping the sidebar
    // usable immediately from the session cache.
    fb.getDoc(fb.doc(fb.db, 'users', user.uid)).then(snapshot => {
      const photo = snapshot.exists() ? snapshot.data().photoDataUrl : null;
      if (photo) sessionStorage.setItem('cs_avatar', photo);
      applySidebarAvatar(avatarEl, photo || cachedAvatar, name[0].toUpperCase());
    }).catch(() => {});
    if (nameEl) nameEl.textContent = name;
    const roleEl = document.getElementById('user-role');
    if (roleEl) roleEl.textContent = isAdmin ? 'Administrator' : 'Free account';
  }
})();

// ── Set user info in sidebar ─────────────────────────────────
document.querySelectorAll('[data-logout]').forEach(link => link.addEventListener('click', async event => {
  event.preventDefault();
  // If an analysis is running on another page, cancel it before signing out.
  if (typeof window.csCancelActiveJob === 'function') {
    window.csCancelActiveJob();
  } else {
    // main.js is shared by every page, including pages that do not load
    // dashboard.js. Keep this unload-safe and avoid a normal fetch here.
    try {
      const raw = localStorage.getItem('cs_active_job');
      const active = raw && JSON.parse(raw);
      if (active?.jobId) {
        const payload = new Blob(['{}'], { type: 'text/plain;charset=UTF-8' });
        navigator.sendBeacon?.(`http://127.0.0.1:8000/analyze/jobs/${encodeURIComponent(active.jobId)}/cancel`, payload);
      }
    } catch (_) {}
    localStorage.removeItem('cs_active_job');
  }
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
  el.innerHTML = h < 12 ? 'Good morning ' : h < 18 ? 'Good afternoon ' : 'Good evening ';
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
