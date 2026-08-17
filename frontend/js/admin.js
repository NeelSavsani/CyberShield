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
  const ADMIN_API = window.CYBERSHIELD_API || localStorage.getItem('cybershield_api') ||
    (['localhost', '127.0.0.1'].includes(window.location.hostname)
      ? 'http://127.0.0.1:8000'
      : 'https://cybershield-api-docker.onrender.com');
  const getUsers = async () => {
    const currentUser = fb.auth.currentUser;
    if (!currentUser) return [];
    const authToken = await currentUser.getIdToken(true);
    const response = await fetch(`${ADMIN_API}/admin/users`, {
      headers: { Authorization: `Bearer ${authToken}` }
    });
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || `Unable to load users (${response.status})`);
    }
    return await response.json();
  };
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
  window.loadUsers = async () => {
    try {
      window.allUsers = await getUsers();
      if (typeof window.filterUsers === 'function') {
        window.filterUsers(true);
      } else {
        window.currentFilteredUsers = window.allUsers;
        document.getElementById('user-count').textContent = `${allUsers.length} user${allUsers.length === 1 ? '' : 's'}`;
        window.renderUsers?.(allUsers);
      }
    } catch (error) {
      document.getElementById('users-table').innerHTML = `<tr><td colspan="8" class="empty-state" style="color:var(--danger)">${escapeHtml(error.message)}</td></tr>`;
    }
  };
  window.loadAnalyses = async () => {
    try {
      if (!window.allUsers) window.allUsers = await getUsers();
      window.allAnalyses = await getAnalyses();
      if (typeof window.filterAnalyses === 'function') {
        window.filterAnalyses(true);
      } else {
        window.currentFilteredAnalyses = window.allAnalyses;
        document.getElementById('analyses-count').textContent = `${allAnalyses.length} record${allAnalyses.length === 1 ? '' : 's'}`;
        window.renderAnalyses?.(allAnalyses);
      }
    } catch (error) {
      document.getElementById('analyses-table').innerHTML = `<tr><td colspan="8" class="empty-state" style="color:var(--danger)">${escapeHtml(error.message)}</td></tr>`;
    }
  };
  let userPage = 1;
  const userPageSize = 10;
  window.renderUsers = users => {
    const totalPages = Math.max(1, Math.ceil(users.length / userPageSize));
    userPage = Math.min(userPage, totalPages);
    const start = (userPage - 1) * userPageSize;
    const pageUsers = users.slice(start, start + userPageSize);
    const tbody = document.getElementById('users-table');
    tbody.innerHTML = pageUsers.length ? pageUsers.map((entry, index) => {
      const label = entry.displayName || [entry.firstName, entry.lastName].filter(Boolean).join(' ') || entry.email || 'Unknown';
      const role = entry.role === 'admin' ? 'admin' : 'user';
      return `<tr><td>${start + index + 1}</td><td><strong>${escapeHtml(label)}</strong></td><td>${escapeHtml(entry.email || '—')}</td><td><span class="badge ${role === 'admin' ? 'badge-purple' : 'badge-info'}">${role}</span></td><td><span class="badge badge-success">Active</span></td><td>${formatDate(entry.createdAt)}</td><td>${formatDate(entry.lastLogin || entry.last_login)}</td><td><button class="action-btn" data-role-user="${escapeHtml(entry.id)}" data-role="${role}">${role === 'admin' ? 'Remove admin' : 'Make admin'}</button> <button class="action-btn" data-view-user="${escapeHtml(entry.id)}">View scans</button> <button class="action-btn" data-copy-email="${escapeHtml(entry.email || '')}"><i class="fa-solid fa-copy"></i></button></td></tr>`;
    }).join('') : '<tr><td colspan="8" class="empty-state">No users found.</td></tr>';
    document.getElementById('user-pagination').innerHTML = `<span>Showing ${pageUsers.length ? start + 1 : 0}–${Math.min(start + pageUsers.length, users.length)} of ${users.length}</span><button ${userPage <= 1 ? 'disabled' : ''} onclick="userPageChange(${userPage - 1})">Previous</button><span>Page ${userPage} of ${totalPages}</span><button ${userPage >= totalPages ? 'disabled' : ''} onclick="userPageChange(${userPage + 1})">Next</button>`;
    tbody.querySelectorAll('[data-role-user]').forEach(button => button.addEventListener('click', () => updateRole(button.dataset.roleUser, button.dataset.role === 'admin' ? 'user' : 'admin')));
    tbody.querySelectorAll('[data-view-user]').forEach(button => button.addEventListener('click', async () => { const account = users.find(item => item.id === button.dataset.viewUser); document.getElementById('analysis-search').value = account?.email || account?.displayName || button.dataset.viewUser; await window.switchTab('analyses'); window.filterAnalyses(); }));
    tbody.querySelectorAll('[data-copy-email]').forEach(button => button.addEventListener('click', async () => { try { await navigator.clipboard.writeText(button.dataset.copyEmail); showToast('Email copied.', 'success'); } catch { showToast('Could not copy the email.', 'warning'); } }));
  };
  window.userPageChange = page => { userPage = page; window.filterUsers(false); };
  window.clearUserSearch = () => {
    ['user-search', 'user-role-filter'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
    const sortEl = document.getElementById('user-sort');
    if (sortEl) sortEl.value = 'registered_desc';
    window.filterUsers();
  };
  window.filterUsers = (resetPage = true) => {
    if (resetPage) userPage = 1;
    const query = (document.getElementById('user-search')?.value || '').toLowerCase().trim();
    const roleFilter = document.getElementById('user-role-filter')?.value || '';
    const sort = document.getElementById('user-sort')?.value || 'registered_desc';
    const clearButton = document.getElementById('user-clear-search');
    if (clearButton) clearButton.disabled = !query && !roleFilter && sort === 'registered_desc';
    const list = (window.allUsers || []).filter(entry => {
      const role = entry.role === 'admin' ? 'admin' : 'user';
      const name = entry.displayName || [entry.firstName, entry.lastName].filter(Boolean).join(' ') || '';
      const email = entry.email || '';
      return (!roleFilter || role === roleFilter) && (!query || `${name} ${email}`.toLowerCase().includes(query));
    });
    list.sort((a, b) => {
      if (sort === 'role') return String(a.role || 'user').localeCompare(String(b.role || 'user'));
      const av = timestampMs(sort.startsWith('login') ? (a.lastLogin || a.last_login) : a.createdAt);
      const bv = timestampMs(sort.startsWith('login') ? (b.lastLogin || b.last_login) : b.createdAt);
      return sort.endsWith('asc') ? av - bv : bv - av;
    });
    window.currentFilteredUsers = list;
    const countEl = document.getElementById('user-count');
    if (countEl) {
      countEl.textContent = `${list.length} user${list.length === 1 ? '' : 's'}`;
    }
    window.renderUsers(list);
  };
  const downloadBlob = (content, filename, mimeType) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  window.closeExportModal = () => {
    const modal = document.getElementById('export-users-modal');
    if (modal) modal.hidden = true;
  };

  window.exportUsers = () => {
    const list = window.currentFilteredUsers || window.allUsers || [];
    if (!list.length) {
      if (typeof showToast === 'function') showToast('No user records match your current filter.', 'warning');
      return;
    }
    const summaryCount = document.getElementById('export-summary-count');
    if (summaryCount) {
      summaryCount.innerHTML = `<i class="fa-solid fa-users"></i> Ready to export ${list.length} user record${list.length === 1 ? '' : 's'}`;
    }
    const modal = document.getElementById('export-users-modal');
    if (modal) modal.hidden = false;
  };

  window.confirmExportUsers = () => {
    const list = window.currentFilteredUsers || window.allUsers || [];
    if (!list.length) {
      if (typeof showToast === 'function') showToast('No user records available to export.', 'warning');
      window.closeExportModal();
      return;
    }
    const selectedFormat = document.querySelector('input[name="export-format"]:checked')?.value || 'csv';
    const isFiltered = (window.allUsers && list.length !== window.allUsers.length);
    const suffix = `${isFiltered ? 'filtered_' : ''}${new Date().toISOString().slice(0, 10)}`;

    if (selectedFormat === 'csv') {
      const headers = ['Sr. No.', 'Name', 'Email', 'Role', 'Joined', 'Last Login'];
      const rows = list.map((entry, index) => {
        const name = entry.displayName || [entry.firstName, entry.lastName].filter(Boolean).join(' ') || entry.email || 'Unknown';
        const role = entry.role === 'admin' ? 'admin' : 'user';
        const joined = formatDate(entry.createdAt);
        const lastLogin = formatDate(entry.lastLogin || entry.last_login);
        return [
          index + 1,
          `"${String(name).replace(/"/g, '""')}"`,
          `"${String(entry.email || '').replace(/"/g, '""')}"`,
          `"${role}"`,
          `"${String(joined).replace(/"/g, '""')}"`,
          `"${String(lastLogin).replace(/"/g, '""')}"`
        ].join(',');
      });
      downloadBlob('\uFEFF' + [headers.join(','), ...rows].join('\r\n'), `cybershield_users_${suffix}.csv`, 'text/csv;charset=utf-8;');
    } else if (selectedFormat === 'xlsx' || selectedFormat === 'xls') {
      const rowsHtml = list.map((entry, index) => {
        const name = escapeHtml(entry.displayName || [entry.firstName, entry.lastName].filter(Boolean).join(' ') || entry.email || 'Unknown');
        const role = entry.role === 'admin' ? 'admin' : 'user';
        const joined = formatDate(entry.createdAt);
        const lastLogin = formatDate(entry.lastLogin || entry.last_login);
        return `<tr><td>${index + 1}</td><td>${name}</td><td>${escapeHtml(entry.email || '—')}</td><td>${role}</td><td>${joined}</td><td>${lastLogin}</td></tr>`;
      }).join('');
      const excelHtml = `<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40"><head><meta charset="utf-8"/><style>table{border-collapse:collapse;width:100%;}th,td{border:1px solid #cbd5e1;padding:8px 12px;text-align:left;}th{background-color:#0f172a;color:#ffffff;font-weight:bold;}</style></head><body><h2>CyberShield User Report</h2><p>Export Date: ${new Date().toLocaleString('en-IN')}</p><table><thead><tr><th>Sr. No.</th><th>Name</th><th>Email</th><th>Role</th><th>Joined</th><th>Last Login</th></tr></thead><tbody>${rowsHtml}</tbody></table></body></html>`;
      downloadBlob(excelHtml, `cybershield_users_${suffix}.${selectedFormat}`, 'application/vnd.ms-excel;charset=utf-8;');
    } else if (selectedFormat === 'json') {
      const jsonData = list.map((entry, index) => ({
        srNo: index + 1,
        name: entry.displayName || [entry.firstName, entry.lastName].filter(Boolean).join(' ') || entry.email || 'Unknown',
        email: entry.email || '',
        role: entry.role === 'admin' ? 'admin' : 'user',
        joined: formatDate(entry.createdAt),
        lastLogin: formatDate(entry.lastLogin || entry.last_login)
      }));
      downloadBlob(JSON.stringify(jsonData, null, 2), `cybershield_users_${suffix}.json`, 'application/json;charset=utf-8;');
    } else if (selectedFormat === 'txt') {
      const headers = ['Sr. No.', 'Name', 'Email', 'Role', 'Joined', 'Last Login'];
      const rows = list.map((entry, index) => {
        const name = entry.displayName || [entry.firstName, entry.lastName].filter(Boolean).join(' ') || entry.email || 'Unknown';
        const role = entry.role === 'admin' ? 'admin' : 'user';
        const joined = formatDate(entry.createdAt);
        const lastLogin = formatDate(entry.lastLogin || entry.last_login);
        return [index + 1, name, entry.email || '—', role, joined, lastLogin].join('\t');
      });
      downloadBlob([headers.join('\t'), ...rows].join('\r\n'), `cybershield_users_${suffix}.txt`, 'text/plain;charset=utf-8;');
    } else if (selectedFormat === 'pdf') {
      const rowsHtml = list.map((entry, index) => {
        const name = escapeHtml(entry.displayName || [entry.firstName, entry.lastName].filter(Boolean).join(' ') || entry.email || 'Unknown');
        const role = entry.role === 'admin' ? 'admin' : 'user';
        const joined = formatDate(entry.createdAt);
        const lastLogin = formatDate(entry.lastLogin || entry.last_login);
        return `<tr><td style="text-align:center;">${index + 1}</td><td><strong>${name}</strong></td><td>${escapeHtml(entry.email || '—')}</td><td><span class="badge ${role === 'admin' ? 'badge-admin' : 'badge-user'}">${role}</span></td><td>${joined}</td><td>${lastLogin}</td></tr>`;
      }).join('');
      const pdfWin = window.open('', '_blank');
      if (pdfWin) {
        pdfWin.document.write(`<!DOCTYPE html><html><head><title>CyberShield User Report</title><style>body{font-family:system-ui,-apple-system,sans-serif;padding:30px;color:#0f172a;}.header{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #3b82f6;padding-bottom:15px;margin-bottom:20px;}.logo{font-size:22px;font-weight:700;color:#0f172a;}.logo span{color:#3b82f6;}.meta{font-size:12px;color:#64748b;text-align:right;}table{width:100%;border-collapse:collapse;margin-top:15px;font-size:13px;}th{background:#0f172a;color:#ffffff;padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:0.05em;}td{padding:10px 12px;border-bottom:1px solid #e2e8f0;}tr:nth-child(even){background:#f8fafc;}.badge{padding:3px 8px;border-radius:6px;font-size:11px;font-weight:600;text-transform:uppercase;}.badge-admin{background:#ede9fe;color:#6d28d9;}.badge-user{background:#e0f2fe;color:#0369a1;}@media print{body{padding:0;}}</style></head><body><div class="header"><div class="logo">Cyber<span>Shield</span> — User Report</div><div class="meta"><div>Generated: ${new Date().toLocaleString('en-IN')}</div><div>Total Records: ${list.length}</div></div></div><table><thead><tr><th>#</th><th>Name</th><th>Email</th><th>Role</th><th>Joined</th><th>Last Login</th></tr></thead><tbody>${rowsHtml}</tbody></table><script>window.onload=()=>{window.print();};<\/script></body></html>`);
        pdfWin.document.close();
      }
    }

    window.closeExportModal();
    if (typeof showToast === 'function') showToast(`Exported ${list.length} record${list.length === 1 ? '' : 's'} as ${selectedFormat.toUpperCase()} successfully.`, 'success');
  };
  async function updateRole(uid, role) {
    if (uid === user.uid && role === 'user') return showToast('You cannot remove your own admin role.', 'warning');
    try { const idToken = await user.getIdToken(true); const response = await fetch(`${ADMIN_API}/admin/users/${encodeURIComponent(uid)}/role?role=${role}`, { method: 'PATCH', headers: { Authorization: `Bearer ${idToken}` } }); const body = await response.json(); if (!response.ok) throw new Error(body.detail || 'Role update failed.'); showToast(`User role changed to ${role}. Sign out and in again for the user to receive it.`, 'success'); await window.loadUsers(); } catch (error) { showToast(error.message, 'error'); }
  }
  window.renderAnalyses = analyses => {
    const totalPages = Math.max(1, Math.ceil(analyses.length / analysisPageSize));
    analysisPage = Math.min(analysisPage, totalPages);
    const start = (analysisPage - 1) * analysisPageSize;
    const pageRows = analyses.slice(start, start + analysisPageSize);
    const countEl = document.getElementById('analyses-count');
    if (countEl) {
      countEl.textContent = `${analyses.length} record${analyses.length === 1 ? '' : 's'}`;
    }
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
    const query = (document.getElementById('analysis-search')?.value || '').toLowerCase().trim();
    const verdict = document.getElementById('verdict-filter')?.value || '';
    const type = document.getElementById('type-filter')?.value || '';
    const date = document.getElementById('date-filter')?.value || '';
    const clearButton = document.getElementById('analysis-clear-search');
    if (clearButton) clearButton.disabled = !query && !verdict && !type && !date;

    const list = (window.allAnalyses || []).filter(scan => {
      const scanType = String(scan.inputType || '').toLowerCase();
      const scanDate = scan.createdAt ? new Date(timestampMs(scan.createdAt)).toISOString().slice(0, 10) : '';
      const account = (allUsers || []).find(entry => entry.id === scan.userId || entry.docId === scan.userId || entry.legacyId === scan.userId);
      const scanEmail = String(scan.userEmail || account?.email || '').toLowerCase();
      const searchable = `${scan.content || ''} ${scan.userId || ''} ${scanEmail} ${scan.userName || ''} ${userName(scan, allUsers || [])}`.toLowerCase();
      return (!verdict || String(scan.verdict).toLowerCase() === verdict) && (!type || scanType === type) && (!date || scanDate === date) && (!query || searchable.includes(query));
    });

    window.currentFilteredAnalyses = list;
    window.renderAnalyses(list);
  };

  window.closeExportAnalysesModal = () => {
    const modal = document.getElementById('export-analyses-modal');
    if (modal) modal.hidden = true;
  };

  window.exportAnalyses = () => {
    const list = window.currentFilteredAnalyses || window.allAnalyses || [];
    if (!list.length) {
      if (typeof showToast === 'function') showToast('No analysis records match your current filter.', 'warning');
      return;
    }
    const summaryCount = document.getElementById('export-analyses-summary-count');
    if (summaryCount) {
      summaryCount.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> Ready to export ${list.length} analysis record${list.length === 1 ? '' : 's'}`;
    }
    const modal = document.getElementById('export-analyses-modal');
    if (modal) modal.hidden = false;
  };

  window.confirmExportAnalyses = () => {
    const list = window.currentFilteredAnalyses || window.allAnalyses || [];
    if (!list.length) {
      if (typeof showToast === 'function') showToast('No analysis records available to export.', 'warning');
      window.closeExportAnalysesModal();
      return;
    }
    const selectedFormat = document.querySelector('input[name="export-analysis-format"]:checked')?.value || 'csv';
    const isFiltered = (window.allAnalyses && list.length !== window.allAnalyses.length);
    const suffix = `${isFiltered ? 'filtered_' : ''}${new Date().toISOString().slice(0, 10)}`;

    if (selectedFormat === 'csv') {
      const headers = ['Sr. No.', 'User', 'Type', 'Content', 'Risk Score', 'Verdict', 'Date'];
      const rows = list.map((scan, index) => [
        index + 1,
        `"${String(userName(scan, allUsers || [])).replace(/"/g, '""')}"`,
        `"${String(scan.inputType || '').replace(/"/g, '""')}"`,
        `"${String(scan.content || '').replace(/"/g, '""')}"`,
        scan.riskScore ?? '—',
        `"${String(scan.verdict || 'unknown').replace(/"/g, '""')}"`,
        `"${String(formatDate(scan.createdAt)).replace(/"/g, '""')}"`
      ].join(','));
      downloadBlob('\uFEFF' + [headers.join(','), ...rows].join('\r\n'), `cybershield_analyses_${suffix}.csv`, 'text/csv;charset=utf-8;');
    } else if (selectedFormat === 'xlsx' || selectedFormat === 'xls') {
      const rowsHtml = list.map((scan, index) => `<tr><td>${index + 1}</td><td>${escapeHtml(userName(scan, allUsers || []))}</td><td>${escapeHtml(scan.inputType || '')}</td><td>${escapeHtml(scan.content || '')}</td><td>${scan.riskScore ?? '—'}</td><td>${escapeHtml(scan.verdict || 'unknown')}</td><td>${formatDate(scan.createdAt)}</td></tr>`).join('');
      const excelHtml = `<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40"><head><meta charset="utf-8"/><style>table{border-collapse:collapse;width:100%;}th,td{border:1px solid #cbd5e1;padding:8px 12px;text-align:left;}th{background-color:#0f172a;color:#ffffff;font-weight:bold;}</style></head><body><h2>CyberShield Analysis Security Report</h2><p>Export Date: ${new Date().toLocaleString('en-IN')}</p><table><thead><tr><th>Sr. No.</th><th>User</th><th>Type</th><th>Content</th><th>Risk Score</th><th>Verdict</th><th>Date</th></tr></thead><tbody>${rowsHtml}</tbody></table></body></html>`;
      downloadBlob(excelHtml, `cybershield_analyses_${suffix}.${selectedFormat}`, 'application/vnd.ms-excel;charset=utf-8;');
    } else if (selectedFormat === 'json') {
      const jsonData = list.map((scan, index) => ({
        srNo: index + 1,
        user: userName(scan, allUsers || []),
        type: scan.inputType || '',
        content: scan.content || '',
        riskScore: scan.riskScore ?? null,
        verdict: scan.verdict || 'unknown',
        date: formatDate(scan.createdAt)
      }));
      downloadBlob(JSON.stringify(jsonData, null, 2), `cybershield_analyses_${suffix}.json`, 'application/json;charset=utf-8;');
    } else if (selectedFormat === 'txt') {
      const headers = ['Sr. No.', 'User', 'Type', 'Content', 'Risk Score', 'Verdict', 'Date'];
      const rows = list.map((scan, index) => [
        index + 1,
        userName(scan, allUsers || []),
        scan.inputType || '',
        scan.content || '',
        scan.riskScore ?? '—',
        scan.verdict || 'unknown',
        formatDate(scan.createdAt)
      ].join('\t'));
      downloadBlob([headers.join('\t'), ...rows].join('\r\n'), `cybershield_analyses_${suffix}.txt`, 'text/plain;charset=utf-8;');
    } else if (selectedFormat === 'pdf') {
      const rowsHtml = list.map((scan, index) => {
        const userLabel = escapeHtml(userName(scan, allUsers || []));
        const v = scan.verdict || 'unknown';
        const vClass = v === 'phishing' ? 'badge-danger' : v === 'suspicious' ? 'badge-warning' : 'badge-safe';
        return `<tr><td style="text-align:center;">${index + 1}</td><td><strong>${userLabel}</strong></td><td>${escapeHtml(scan.inputType || '')}</td><td style="word-break:break-all;max-width:260px;">${escapeHtml(scan.content || '')}</td><td style="text-align:center;">${scan.riskScore ?? '—'}</td><td><span class="badge ${vClass}">${v}</span></td><td>${formatDate(scan.createdAt)}</td></tr>`;
      }).join('');
      const pdfWin = window.open('', '_blank');
      if (pdfWin) {
        pdfWin.document.write(`<!DOCTYPE html><html><head><title>CyberShield Analysis Report</title><style>body{font-family:system-ui,-apple-system,sans-serif;padding:30px;color:#0f172a;}.header{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #3b82f6;padding-bottom:15px;margin-bottom:20px;}.logo{font-size:22px;font-weight:700;color:#0f172a;}.logo span{color:#3b82f6;}.meta{font-size:12px;color:#64748b;text-align:right;}table{width:100%;border-collapse:collapse;margin-top:15px;font-size:13px;}th{background:#0f172a;color:#ffffff;padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:0.05em;}td{padding:10px 12px;border-bottom:1px solid #e2e8f0;}tr:nth-child(even){background:#f8fafc;}.badge{padding:3px 8px;border-radius:6px;font-size:11px;font-weight:600;text-transform:uppercase;}.badge-danger{background:#fee2e2;color:#991b1b;}.badge-warning{background:#fef3c7;color:#92400e;}.badge-safe{background:#d1fae5;color:#065f46;}@media print{body{padding:0;}}</style></head><body><div class="header"><div class="logo">Cyber<span>Shield</span> — Analysis Report</div><div class="meta"><div>Generated: ${new Date().toLocaleString('en-IN')}</div><div>Total Records: ${list.length}</div></div></div><table><thead><tr><th>#</th><th>User</th><th>Type</th><th>Content</th><th>Risk</th><th>Verdict</th><th>Date</th></tr></thead><tbody>${rowsHtml}</tbody></table><script>window.onload=()=>{window.print();};<\/script></body></html>`);
        pdfWin.document.close();
      }
    }

    window.closeExportAnalysesModal();
    if (typeof showToast === 'function') showToast(`Exported ${list.length} record${list.length === 1 ? '' : 's'} as ${selectedFormat.toUpperCase()} successfully.`, 'success');
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
