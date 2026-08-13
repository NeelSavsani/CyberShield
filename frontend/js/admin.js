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
  const escapeHtml = value => { const div = document.createElement('div'); div.textContent = value ?? ''; return div.innerHTML; };
  const getUsers = async () => (await fb.getDocs(fb.collection(fb.db, 'users'))).docs.map(doc => ({
    ...doc.data(),
    docId: doc.id,
    id: doc.id,
    legacyId: doc.data().legacyId || doc.data().legacy_id || doc.data().id || null
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
  });
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

  window.switchTab = name => {
    const tabs = ['overview', 'users', 'analyses', 'flagged', 'logs'];
    document.querySelectorAll('.admin-tab').forEach((tab, index) => tab.classList.toggle('active', tabs[index] === name));
    document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.toggle('active', pane.id === `tab-${name}`));
    if (name === 'users') window.loadUsers();
    if (name === 'analyses') window.loadAnalyses();
    if (name === 'flagged') window.loadFlagged();
    if (name === 'logs') window.loadLogs();
  };

  window.loadOverview = async () => {
    try {
    const [users, analyses, flags] = await Promise.all([getUsers(), getAnalyses(), getFlags()]);
    document.getElementById('total-users').textContent = users.length;
    document.getElementById('total-analyses').textContent = analyses.length;
    document.getElementById('total-phishing').textContent = analyses.filter(scan => scan.verdict === 'phishing').length;
    document.getElementById('total-flagged').textContent = flags.length;
    const rows = analyses.slice(0, 20);
    document.getElementById('overview-table').innerHTML = rows.length ? rows.map(scan => `<tr><td>${escapeHtml(userName(scan, users))}</td><td><span class="badge badge-info">${escapeHtml(scan.inputType)}</span></td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(scan.content)}</td><td>${scan.riskScore}</td><td><span class="badge ${badge(scan.verdict)}">${scan.verdict}</span></td><td>${formatDate(scan.createdAt)}</td></tr>`).join('') : '<tr><td colspan="6" class="empty-state">No analyses yet.</td></tr>';
    } catch (error) {
      document.getElementById('overview-table').innerHTML = `<tr><td colspan="6" class="empty-state" style="color:var(--danger)">${escapeHtml(error.message)}</td></tr>`;
    }
  };
  window.loadUsers = async () => { window.allUsers = await getUsers(); document.getElementById('user-count').textContent = `${allUsers.length} users`; window.renderUsers?.(allUsers); };
  window.loadAnalyses = async () => { try { window.allAnalyses = await getAnalyses(); document.getElementById('analyses-count').textContent = `${allAnalyses.length} records`; window.renderAnalyses?.(allAnalyses); } catch (error) { document.getElementById('analyses-table').innerHTML = `<tr><td colspan="7" class="empty-state" style="color:var(--danger)">${escapeHtml(error.message)}</td></tr>`; } };
  window.renderUsers = users => { document.getElementById('users-table').innerHTML = users.length ? users.map(entry => { const isCurrentAdmin = entry.id === user.uid && token?.claims.admin === true; return `<tr><td><strong>${escapeHtml(entry.displayName || '—')}</strong></td><td>${escapeHtml(entry.email)}</td><td><span class="badge ${isCurrentAdmin ? 'badge-purple' : 'badge-info'}">${isCurrentAdmin ? 'admin' : 'user'}</span></td><td><span class="badge badge-success">Active</span></td><td>${formatDate(entry.createdAt)}</td><td>—</td><td>—</td></tr>`; }).join('') : '<tr><td colspan="7" class="empty-state">No users found.</td></tr>'; };
  window.filterUsers = () => { const query = document.getElementById('user-search').value.toLowerCase(); window.renderUsers(allUsers.filter(entry => `${entry.displayName || ''} ${entry.email || ''}`.toLowerCase().includes(query))); };
  window.renderAnalyses = analyses => { document.getElementById('analyses-table').innerHTML = analyses.length ? analyses.map(scan => `<tr><td>${escapeHtml(String(scan.userId || 'Unknown').slice(0, 8))}</td><td>${escapeHtml(scan.inputType)}</td><td>${escapeHtml(scan.content)}</td><td>${scan.riskScore ?? '—'}</td><td><span class="badge ${badge(scan.verdict)}">${escapeHtml(scan.verdict || 'unknown')}</span></td><td>${formatDate(scan.createdAt)}</td><td>—</td></tr>`).join('') : '<tr><td colspan="7" class="empty-state">No analyses found.</td></tr>'; };
  window.filterAnalyses = () => { const query = document.getElementById('analysis-search').value.toLowerCase(); const verdict = document.getElementById('verdict-filter').value; window.renderAnalyses(allAnalyses.filter(scan => (!verdict || scan.verdict === verdict) && `${scan.content} ${scan.userId}`.toLowerCase().includes(query))); };
  window.loadFlagged = async () => {
    const flags = await getFlags(); document.getElementById('flagged-count').textContent = `${flags.length} items`;
    document.getElementById('flagged-table').innerHTML = flags.length ? flags.map(item => `<tr><td>${escapeHtml(item.type)}</td><td>${escapeHtml(item.value)}</td><td>${escapeHtml(item.reason)}</td><td>${formatDate(item.createdAt)}</td><td><button class="action-btn" data-flag="${item.id}">Delete</button></td></tr>`).join('') : '<tr><td colspan="5" class="empty-state">No flagged items.</td></tr>';
    document.querySelectorAll('[data-flag]').forEach(button => button.addEventListener('click', async () => { await fb.deleteDoc(fb.doc(fb.db, 'flaggedItems', button.dataset.flag)); loadFlagged(); loadOverview(); }));
  };
  window.addFlaggedItem = async () => { const type = document.getElementById('flag-type').value; const value = document.getElementById('flag-value').value.trim(); const reason = document.getElementById('flag-reason').value.trim(); if (!value) return alert('Enter a value to flag.'); await fb.addDoc(fb.collection(fb.db, 'flaggedItems'), { type, value, reason, createdAt: fb.serverTimestamp(), addedBy: user.uid }); document.getElementById('flag-value').value = ''; document.getElementById('flag-reason').value = ''; loadFlagged(); loadOverview(); };
  window.loadLogs = async () => { const logs = (await fb.getDocs(fb.query(fb.collection(fb.db, 'systemLogs'), fb.orderBy('createdAt', 'desc'), fb.limit(100)))).docs.map(doc => doc.data()); document.getElementById('logs-count').textContent = `${logs.length} entries`; document.getElementById('logs-table').innerHTML = logs.length ? logs.map(log => `<tr><td>${escapeHtml(log.level || 'info')}</td><td>${escapeHtml(log.source || 'app')}</td><td>${escapeHtml(log.message)}</td><td>${formatDate(log.createdAt)}</td></tr>`).join('') : '<tr><td colspan="4" class="empty-state">No log entries yet.</td></tr>'; };
  window.refreshAll = () => { window.loadOverview(); window.loadUsers(); window.loadAnalyses(); window.loadFlagged(); window.loadLogs(); };
  window.refreshAll();
})().catch(error => { console.error(error); document.getElementById('overview-table').innerHTML = `<tr><td colspan="6" class="empty-state">${error.message}</td></tr>`; });
