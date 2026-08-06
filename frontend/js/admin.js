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

  const formatDate = value => (value?.toDate?.() || new Date()).toLocaleString('en-IN');
  const escapeHtml = value => { const div = document.createElement('div'); div.textContent = value ?? ''; return div.innerHTML; };
  const getUsers = async () => (await fb.getDocs(fb.collection(fb.db, 'users'))).docs.map(doc => ({ id: doc.id, ...doc.data() }));
  const getAnalyses = async () => (await fb.getDocs(fb.query(fb.collectionGroup(fb.db, 'analyses'), fb.orderBy('createdAt', 'desc'), fb.limit(200)))).docs.map(doc => ({ id: doc.id, userId: doc.ref.parent.parent.id, ...doc.data() }));
  const getFlags = async () => (await fb.getDocs(fb.query(fb.collection(fb.db, 'flaggedItems'), fb.orderBy('createdAt', 'desc')))).docs.map(doc => ({ id: doc.id, ...doc.data() }));
  const userName = (scan, users) => users.find(user => user.id === scan.userId)?.displayName || users.find(user => user.id === scan.userId)?.email || scan.userId.slice(0, 8);
  const badge = verdict => verdict === 'phishing' ? 'badge-danger' : verdict === 'safe' ? 'badge-success' : 'badge-warning';

  window.loadOverview = async () => {
    const [users, analyses, flags] = await Promise.all([getUsers(), getAnalyses(), getFlags()]);
    document.getElementById('total-users').textContent = users.length;
    document.getElementById('total-analyses').textContent = analyses.length;
    document.getElementById('total-phishing').textContent = analyses.filter(scan => scan.verdict === 'phishing').length;
    document.getElementById('total-flagged').textContent = flags.length;
    const rows = analyses.slice(0, 20);
    document.getElementById('overview-table').innerHTML = rows.length ? rows.map(scan => `<tr><td>${escapeHtml(userName(scan, users))}</td><td><span class="badge badge-info">${escapeHtml(scan.inputType)}</span></td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(scan.content)}</td><td>${scan.riskScore}</td><td><span class="badge ${badge(scan.verdict)}">${scan.verdict}</span></td><td>${formatDate(scan.createdAt)}</td></tr>`).join('') : '<tr><td colspan="6" class="empty-state">No analyses yet.</td></tr>';
  };
  window.loadUsers = async () => { window.allUsers = await getUsers(); document.getElementById('user-count').textContent = `${allUsers.length} users`; window.renderUsers?.(allUsers); };
  window.loadAnalyses = async () => { window.allAnalyses = await getAnalyses(); document.getElementById('analyses-count').textContent = `${allAnalyses.length} records`; window.renderAnalyses?.(allAnalyses); };
  window.renderUsers = users => { document.getElementById('users-table').innerHTML = users.length ? users.map(entry => `<tr><td><strong>${escapeHtml(entry.displayName || '—')}</strong></td><td>${escapeHtml(entry.email)}</td><td><span class="badge badge-info">user</span></td><td><span class="badge badge-success">Active</span></td><td>${formatDate(entry.createdAt)}</td><td>—</td><td>—</td></tr>`).join('') : '<tr><td colspan="7" class="empty-state">No users found.</td></tr>'; };
  window.filterUsers = () => { const query = document.getElementById('user-search').value.toLowerCase(); window.renderUsers(allUsers.filter(entry => `${entry.displayName || ''} ${entry.email || ''}`.toLowerCase().includes(query))); };
  window.renderAnalyses = analyses => { document.getElementById('analyses-table').innerHTML = analyses.length ? analyses.map(scan => `<tr><td>${escapeHtml(scan.userId.slice(0, 8))}</td><td>${escapeHtml(scan.inputType)}</td><td>${escapeHtml(scan.content)}</td><td>${scan.riskScore}</td><td><span class="badge ${badge(scan.verdict)}">${scan.verdict}</span></td><td>${formatDate(scan.createdAt)}</td><td>—</td></tr>`).join('') : '<tr><td colspan="7" class="empty-state">No analyses found.</td></tr>'; };
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
