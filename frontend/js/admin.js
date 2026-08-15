/* Firestore-backed admin console. Access requires Firebase custom claim: admin=true. */
(async () => {
  const fb = await window.firebaseReady;
  await new Promise(resolve => fb.onAuthStateChanged(fb.auth, resolve));
  const user = fb.auth.currentUser;
  const token = user && await user.getIdTokenResult(true);
  if (!token?.claims.admin) {
    document.querySelector('.main').innerHTML = '<header class="topbar"><span class="topbar-title">Access denied</span></header><div class="content"><div class="panel"><div class="panel-body">This page requires a Firebase administrator account.</div></div></div>';
    return;
  }

  const formatDate = value => {
    const date = value?.toDate ? value.toDate() : new Date(value);
    return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('en-IN');
  };
  const timestampMs = value => {
    if (value?.toDate) return value.toDate().getTime();
    const ms = new Date(value || 0).getTime();
    return Number.isNaN(ms) ? 0 : ms;
  };
  const escapeHtml = value => { const div = document.createElement('div'); div.textContent = value ?? ''; return div.innerHTML; };
  const getUsers = async () => (await fb.getDocs(fb.collection(fb.db, 'users'))).docs.map(doc => ({
    ...doc.data(),
    docId: doc.id,
    id: doc.id,
    legacyId: doc.data().legacyId || doc.data().legacy_id || doc.data().id || null,
    // Firebase Web exposes metadata for the currently signed-in account.
    // Use it as a fallback until that user's next login writes lastLogin.
    lastLogin: doc.id === user.uid ? (doc.data().lastLogin || user.metadata?.lastSignInTime || null) : doc.data().lastLogin
  }));
  const getAnalyses = async () => (await fb.getDocs(fb.query(fb.collectionGroup(fb.db, 'analyses'), fb.limit(200)))).docs.map(doc => {
    const data = doc.data();
    const owner = doc.ref.parent?.parent;
    const pathParts = doc.ref.path.split('/');
    // Expected path: users/{uid}/analyses/{analysisId}. The path fallback
    // also handles documents returned by older SDKs without parent refs.
    const pathOwner = pathParts.length >= 4 && pathParts[0] === 'users' ? pathParts[1] : null;
    return {
      ...data,
      id: doc.id,
      userId: owner?.id || pathOwner || data.userId || data.user_id || data.uid || 'unknown',
      userEmail: data.userEmail || data.user_email || data.ownerEmail || data.owner_email || data.email || null,
      userName: data.userName || data.user_name || data.ownerName || data.owner_name || data.name || (typeof data.user === 'string' ? data.user : null),
      inputType: data.inputType || data.input_type || 'URL',
      riskScore: data.riskScore ?? data.risk_score ?? data.score ?? null,
      createdAt: data.createdAt || data.created_at || data.analyzedAt || data.analyzed_at || null
    };
  }).sort((a, b) => timestampMs(b.createdAt) - timestampMs(a.createdAt));
  const getFlags = async () => (await fb.getDocs(fb.collection(fb.db, 'flaggedItems'))).docs.map(doc => ({ id: doc.id, ...doc.data() }));
  const userName = (scan, users) => {
    if (scan.userId === 'guest') return 'Guest';
    if (scan.userName || scan.userEmail) return scan.userName || scan.userEmail;
    const account = users.find(entry => entry.id === scan.userId || entry.docId === scan.userId || entry.userId === scan.userId || entry.legacyId === scan.userId || String(entry.accountId || '') === String(scan.userId))
      || users.find(entry => entry.email && entry.email.toLowerCase() === String(scan.userEmail || '').toLowerCase());
    if (!account) return String(scan.userId || 'Unknown').slice(0, 8);
    return account.displayName || [account.firstName, account.lastName].filter(Boolean).join(' ') || account.email || 'Unknown';
  };
  const badge = verdict => verdict === 'phishing' ? 'badge-danger' : verdict === 'safe' ? 'badge-success' : 'badge-warning';
  let analysisPage = 1;
  const analysisPageSize = 10;

  window.switchTab = async name => {
    const tabs = ['overview', 'users', 'analyses', 'flagged', 'logs'];
    document.querySelectorAll('.admin-tab').forEach((tab, index) => tab.classList.toggle('active', tabs[index] === name));
    document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.toggle('active', pane.id === `tab-${name}`));
    if (name === 'users') await window.loadUsers();
    if (name === 'analyses') await window.loadAnalyses();
    if (name === 'flagged') await window.loadFlagged();
    if (name === 'logs') await window.loadLogs();
  };

  window.loadOverview = async () => {
    try {
    const [users, analyses, flags] = await Promise.all([getUsers(), getAnalyses(), getFlags()]);
    document.getElementById('total-users').textContent = users.length;
    document.getElementById('total-analyses').textContent = analyses.length;
    document.getElementById('total-phishing').textContent = analyses.filter(scan => scan.verdict === 'phishing').length;
    document.getElementById('total-flagged').textContent = flags.length;
    const rows = analyses.slice(0, 20);
    document.getElementById('overview-table').innerHTML = rows.length ? rows.map((scan, index) => `<tr><td>${index + 1}</td><td>${escapeHtml(userName(scan, users))}</td><td><span class="badge badge-info">${escapeHtml(scan.inputType)}</span></td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(scan.content)}</td><td>${scan.riskScore}</td><td><span class="badge ${badge(scan.verdict)}">${scan.verdict}</span></td><td>${formatDate(scan.createdAt)}</td></tr>`).join('') : '<tr><td colspan="7" class="empty-state">No analyses yet.</td></tr>';
    } catch (error) {
      document.getElementById('overview-table').innerHTML = `<tr><td colspan="7" class="empty-state" style="color:var(--danger)">${escapeHtml(error.message)}</td></tr>`;
    }
  };
  window.loadUsers = async () => { window.allUsers = await getUsers(); document.getElementById('user-count').textContent = `${allUsers.length} users`; window.renderUsers?.(allUsers); };
  window.loadAnalyses = async () => { try { if (!window.allUsers) window.allUsers = await getUsers(); window.allAnalyses = await getAnalyses(); document.getElementById('analyses-count').textContent = `${allAnalyses.length} records`; window.renderAnalyses?.(allAnalyses); } catch (error) { document.getElementById('analyses-table').innerHTML = `<tr><td colspan="8" class="empty-state" style="color:var(--danger)">${escapeHtml(error.message)}</td></tr>`; } };
  window.renderUsers = users => {
    const tbody = document.getElementById('users-table');
    tbody.innerHTML = users.length ? users.map(entry => {
      const isCurrentAdmin = entry.id === user.uid && token?.claims.admin === true;
      const label = entry.displayName || [entry.firstName, entry.lastName].filter(Boolean).join(' ') || entry.email || 'Unknown';
      return `<tr><td><strong>${escapeHtml(label)}</strong></td><td>${escapeHtml(entry.email || '—')}</td><td><span class="badge ${isCurrentAdmin ? 'badge-purple' : 'badge-info'}">${isCurrentAdmin ? 'admin' : 'user'}</span></td><td><span class="badge badge-success">Active</span></td><td>${formatDate(entry.createdAt)}</td><td>${formatDate(entry.lastLogin || entry.last_login)}</td><td><button class="action-btn" data-view-user="${escapeHtml(entry.id)}" title="View this user's analyses">View scans</button> <button class="action-btn" data-copy-email="${escapeHtml(entry.email || '')}" title="Copy email"><i class="fa-solid fa-copy"></i></button></td></tr>`;
    }).join('') : '<tr><td colspan="7" class="empty-state">No users found.</td></tr>';
    tbody.querySelectorAll('[data-view-user]').forEach(button => button.addEventListener('click', () => {
      const account = users.find(item => item.id === button.dataset.viewUser);
      document.getElementById('analysis-search').value = account?.email || account?.displayName || button.dataset.viewUser;
      window.switchTab('analyses');
      window.filterAnalyses();
    }));
    tbody.querySelectorAll('[data-copy-email]').forEach(button => button.addEventListener('click', async () => {
      try { await navigator.clipboard.writeText(button.dataset.copyEmail); showToast('Email copied.', 'success'); } catch { showToast('Could not copy the email.', 'warning'); }
    }));
  };
  let userPage = 1;
  const userPageSize = 10;
  const ADMIN_API = localStorage.getItem('cybershield_api') || 'https://cybershield-api-pkqa.onrender.com';
  window.renderUsers = users => {
    const totalPages = Math.max(1, Math.ceil(users.length / userPageSize));
    userPage = Math.min(userPage, totalPages);
    const start = (userPage - 1) * userPageSize;
    const pageUsers = users.slice(start, start + userPageSize);
    const tbody = document.getElementById('users-table');
    tbody.innerHTML = pageUsers.length ? pageUsers.map((entry, index) => {
      const isCurrentAdmin = entry.id === user.uid && token?.claims.admin === true;
      const label = entry.displayName || [entry.firstName, entry.lastName].filter(Boolean).join(' ') || entry.email || 'Unknown';
      const role = entry.role || (isCurrentAdmin ? 'admin' : 'user');
      return `<tr><td>${start + index + 1}</td><td><strong>${escapeHtml(label)}</strong></td><td>${escapeHtml(entry.email || '—')}</td><td><span class="badge ${role === 'admin' ? 'badge-purple' : 'badge-info'}">${role}</span></td><td><span class="badge badge-success">Active</span></td><td>${formatDate(entry.createdAt)}</td><td>${formatDate(entry.lastLogin || entry.last_login)}</td><td><button class="action-btn" data-role-user="${escapeHtml(entry.id)}" data-role="${role}">${role === 'admin' ? 'Remove admin' : 'Make admin'}</button> <button class="action-btn" data-view-user="${escapeHtml(entry.id)}">View scans</button> <button class="action-btn" data-copy-email="${escapeHtml(entry.email || '')}"><i class="fa-solid fa-copy"></i></button></td></tr>`;
    }).join('') : '<tr><td colspan="8" class="empty-state">No users found.</td></tr>';
    document.getElementById('user-pagination').innerHTML = `<span>Showing ${pageUsers.length ? start + 1 : 0}–${Math.min(start + pageUsers.length, users.length)} of ${users.length}</span><button ${userPage <= 1 ? 'disabled' : ''} onclick="userPageChange(${userPage - 1})">Previous</button><span>Page ${userPage} of ${totalPages}</span><button ${userPage >= totalPages ? 'disabled' : ''} onclick="userPageChange(${userPage + 1})">Next</button>`;
    tbody.querySelectorAll('[data-role-user]').forEach(button => button.addEventListener('click', () => updateRole(button.dataset.roleUser, button.dataset.role === 'admin' ? 'user' : 'admin')));
    tbody.querySelectorAll('[data-view-user]').forEach(button => button.addEventListener('click', async () => { const account = users.find(item => item.id === button.dataset.viewUser); document.getElementById('analysis-search').value = account?.email || account?.displayName || button.dataset.viewUser; await window.switchTab('analyses'); window.filterAnalyses(); }));
    tbody.querySelectorAll('[data-copy-email]').forEach(button => button.addEventListener('click', async () => { try { await navigator.clipboard.writeText(button.dataset.copyEmail); showToast('Email copied.', 'success'); } catch { showToast('Could not copy the email.', 'warning'); } }));
  };
  window.userPageChange = page => { userPage = page; window.filterUsers(false); };
  window.filterUsers = (resetPage = true) => {
    if (resetPage) userPage = 1;
    const query = document.getElementById('user-search').value.toLowerCase();
    const roleFilter = document.getElementById('user-role-filter')?.value || '';
    const sort = document.getElementById('user-sort')?.value || 'registered_desc';
    const list = allUsers.filter(entry => { const role = entry.role || (entry.id === user.uid && token?.claims.admin === true ? 'admin' : 'user'); return (!roleFilter || role === roleFilter) && `${entry.displayName || ''} ${entry.email || ''}`.toLowerCase().includes(query); });
    list.sort((a, b) => { if (sort === 'role') return String(a.role || 'user').localeCompare(String(b.role || 'user')); const av = timestampMs(sort.startsWith('login') ? a.lastLogin : a.createdAt); const bv = timestampMs(sort.startsWith('login') ? b.lastLogin : b.createdAt); return sort.endsWith('asc') ? av - bv : bv - av; });
    window.renderUsers(list);
  };
  async function updateRole(uid, role) {
    if (uid === user.uid && role === 'user') return showToast('You cannot remove your own admin role.', 'warning');
    try { const idToken = await user.getIdToken(); const response = await fetch(`${ADMIN_API}/admin/users/${encodeURIComponent(uid)}/role?role=${role}`, { method: 'PATCH', headers: { Authorization: `Bearer ${idToken}` } }); const body = await response.json(); if (!response.ok) throw new Error(body.detail || 'Role update failed.'); showToast(`User role changed to ${role}. Sign out and in again for the user to receive it.`, 'success'); await window.loadUsers(); } catch (error) { showToast(error.message, 'error'); }
  }
  window.renderAnalyses = analyses => {
    const totalPages = Math.max(1, Math.ceil(analyses.length / analysisPageSize));
    analysisPage = Math.min(analysisPage, totalPages);
    const start = (analysisPage - 1) * analysisPageSize;
    const pageRows = analyses.slice(start, start + analysisPageSize);
    document.getElementById('analyses-table').innerHTML = pageRows.length ? pageRows.map((scan, index) => `<tr><td>${start + index + 1}</td><td>${escapeHtml(userName(scan, allUsers || []))}</td><td>${escapeHtml(scan.inputType)}</td><td>${escapeHtml(scan.content)}</td><td>${scan.riskScore ?? '—'}</td><td><span class="badge ${badge(scan.verdict)}">${escapeHtml(scan.verdict || 'unknown')}</span></td><td>${formatDate(scan.createdAt)}</td><td>—</td></tr>`).join('') : '<tr><td colspan="8" class="empty-state">No analyses found.</td></tr>';
    const pager = document.getElementById('analysis-pagination');
    pager.innerHTML = `<span>Showing ${pageRows.length ? start + 1 : 0}–${Math.min(start + pageRows.length, analyses.length)} of ${analyses.length}</span><button ${analysisPage <= 1 ? 'disabled' : ''} onclick="analysisPageChange(${analysisPage - 1})">Previous</button><span>Page ${analysisPage} of ${totalPages}</span><button ${analysisPage >= totalPages ? 'disabled' : ''} onclick="analysisPageChange(${analysisPage + 1})">Next</button>`;
  };
  window.analysisPageChange = page => { analysisPage = page; window.filterAnalyses(false); };
  window.clearAnalysisSearch = () => {
    ['analysis-search', 'date-filter'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
    ['type-filter', 'verdict-filter'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
    window.filterAnalyses();
  };
  window.filterAnalyses = (resetPage = true) => {
    if (resetPage) analysisPage = 1;
    const query = document.getElementById('analysis-search').value.toLowerCase();
    const verdict = document.getElementById('verdict-filter').value;
    const type = document.getElementById('type-filter').value;
    const date = document.getElementById('date-filter').value;
    const clearButton = document.getElementById('analysis-clear-search');
    if (clearButton) clearButton.disabled = !query && !verdict && !type && !date;
    window.renderAnalyses(allAnalyses.filter(scan => {
      const scanType = String(scan.inputType || '').toLowerCase();
      const scanDate = scan.createdAt ? new Date(timestampMs(scan.createdAt)).toISOString().slice(0, 10) : '';
      const account = (allUsers || []).find(entry => entry.id === scan.userId || entry.docId === scan.userId || entry.legacyId === scan.userId);
      const scanEmail = String(scan.userEmail || account?.email || '').toLowerCase();
      const searchable = `${scan.content || ''} ${scan.userId || ''} ${scanEmail} ${scan.userName || ''} ${userName(scan, allUsers || [])}`.toLowerCase();
      return (!verdict || String(scan.verdict).toLowerCase() === verdict) && (!type || scanType === type) && (!date || scanDate === date) && (!query || searchable.includes(query));
    }));
  };
  window.loadFlagged = async () => {
    const flags = await getFlags(); document.getElementById('flagged-count').textContent = `${flags.length} items`;
    document.getElementById('flagged-table').innerHTML = flags.length ? flags.map(item => `<tr><td><span class="badge ${item.reportType === 'phishing' ? 'badge-danger' : item.reportType === 'safe' ? 'badge-success' : 'badge-info'}">${escapeHtml(item.reportType || 'database')}</span></td><td>${escapeHtml(item.type)}</td><td>${escapeHtml(item.value)}</td><td style="max-width:300px">${escapeHtml(item.reason)}</td><td>${escapeHtml(item.reporterEmail || item.addedBy || 'Admin')}</td><td>${formatDate(item.createdAt)}</td><td><button class="action-btn" data-flag="${item.id}">Delete</button></td></tr>`).join('') : '<tr><td colspan="7" class="empty-state">No reports or flagged items.</td></tr>';
    document.querySelectorAll('[data-flag]').forEach(button => button.addEventListener('click', async () => { await fb.deleteDoc(fb.doc(fb.db, 'flaggedItems', button.dataset.flag)); loadFlagged(); loadOverview(); }));
  };
  window.addFlaggedItem = async () => { const type = document.getElementById('flag-type').value; const value = document.getElementById('flag-value').value.trim(); const reason = document.getElementById('flag-reason').value.trim(); if (!value) return alert('Enter a value to flag.'); await fb.addDoc(fb.collection(fb.db, 'flaggedItems'), { type, value, reason, createdAt: fb.serverTimestamp(), addedBy: user.uid }); document.getElementById('flag-value').value = ''; document.getElementById('flag-reason').value = ''; loadFlagged(); loadOverview(); };
  window.loadLogs = async () => { const logs = (await fb.getDocs(fb.query(fb.collection(fb.db, 'systemLogs'), fb.orderBy('createdAt', 'desc'), fb.limit(100)))).docs.map(doc => doc.data()); document.getElementById('logs-count').textContent = `${logs.length} entries`; document.getElementById('logs-table').innerHTML = logs.length ? logs.map(log => `<tr><td>${escapeHtml(log.level || 'info')}</td><td>${escapeHtml(log.source || 'app')}</td><td>${escapeHtml(log.message)}</td><td>${formatDate(log.createdAt)}</td></tr>`).join('') : '<tr><td colspan="4" class="empty-state">No log entries yet.</td></tr>'; };
  window.refreshAll = async () => {
    const button = document.getElementById('admin-refresh-btn');
    if (button) { button.disabled = true; button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Refreshing…'; }
    try {
      window.allUsers = null;
      await Promise.all([window.loadOverview(), window.loadUsers(), window.loadAnalyses(), window.loadFlagged(), window.loadLogs()]);
      if (typeof showToast === 'function') showToast('Admin data refreshed.', 'success');
    } finally {
      if (button) { button.disabled = false; button.innerHTML = '<i class="fa-solid fa-rotate"></i> Refresh'; }
    }
  };
  window.refreshAll();
})().catch(error => { console.error(error); document.getElementById('overview-table').innerHTML = `<tr><td colspan="6" class="empty-state">${error.message}</td></tr>`; });
