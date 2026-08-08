/* Firestore-backed scan history. */
let allRows = [];
const tbody = document.getElementById('history-body');
const emptyState = document.getElementById('empty-state');
const searchInput = document.getElementById('search-input');
const typeFilter = document.getElementById('type-filter');
const verdictFilter = document.getElementById('verdict-filter');
const typeIcon = { url: '<i class="fa-solid fa-link"></i>', email: '<i class="fa-solid fa-envelope"></i>', image: '<i class="fa-solid fa-image"></i>' };

// Helper to safely parse dates from Firestore objects, strings, or numbers
function parseRowDate(row) {
  const rawDate = row.createdAt || row.analyzedAt || row.timestamp;
  if (!rawDate) return new Date();
  if (rawDate.toDate && typeof rawDate.toDate === 'function') {
    return rawDate.toDate();
  }
  return new Date(rawDate);
}

function updateStatCards(rows) {
  const safeRows = Array.isArray(rows) ? rows : [];
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;

  const stats = {
    total: safeRows.length,
    threats: safeRows.filter(row => {
      const v = (row.verdict || '').toLowerCase();
      return v === 'phishing' || v === 'malicious' || v === 'suspicious';
    }).length,
    safe: safeRows.filter(row => (row.verdict || '').toLowerCase() === 'safe').length,
    week: safeRows.filter(row => parseRowDate(row).getTime() >= weekAgo).length
  };

  document.getElementById('stat-total').textContent = stats.total;
  document.getElementById('stat-threats').textContent = stats.threats;
  document.getElementById('stat-safe').textContent = stats.safe;
  document.getElementById('stat-week').textContent = stats.week;
}

const escapeHtml = value => { const el = document.createElement('div'); el.textContent = value ?? ''; return el.innerHTML; };
const badge = verdict => `<span class="badge badge-${(verdict || 'safe').toLowerCase()}">${verdict}</span>`;

function renderRows(rows) {
  emptyState.style.display = rows.length ? 'none' : 'block';
  tbody.innerHTML = rows.map(row => `<tr>
    <td>${typeIcon[row.inputType] || '<i class="fa-solid fa-file"></i>'} ${row.inputType || 'N/A'}</td>
    <td style="max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${escapeHtml(row.content)}">${escapeHtml(row.content)}</td>
    <td><strong>${row.riskScore ?? 0}</strong>/100</td>
    <td>${badge(row.verdict)}</td>
    <td>${parseRowDate(row).toLocaleString('en-IN')}</td>
    <td>
      <button class="icon-btn view-result" title="View analysis result" data-view-id="${row.id}" aria-label="View analysis result"><i class="fa-solid fa-eye"></i></button>
      <button class="icon-btn" title="Delete" onclick="deleteRow('${row.id}')" aria-label="Delete analysis"><i class="fa-solid fa-trash"></i></button>
    </td>
  </tr>`).join('');

  tbody.querySelectorAll('[data-view-id]').forEach(button => {
    button.addEventListener('click', () => openResult(button.dataset.viewId));
  });
}

function openResult(id) {
  const row = allRows.find(item => item.id === id);
  if (!row) return;

  sessionStorage.setItem('cs_result', JSON.stringify({
    risk_score: row.riskScore ?? 0,
    verdict: row.verdict || 'safe',
    indicators: row.indicators || [],
    input_type: row.inputType || 'url',
    content: row.content || '',
    analyzed_at: parseRowDate(row).toISOString(),
    features: row.features || {},
    screenshot_url: row.screenshotUrl || null,
    analysis_id: row.id
  }));
  sessionStorage.setItem('cs_result_source', 'history');
  window.location.href = 'result.html';
}

function applyFilters() {
  const q = (searchInput.value || '').toLowerCase();
  const filtered = allRows.filter(row => (!typeFilter.value || row.inputType === typeFilter.value)
    && (!verdictFilter.value || (row.verdict || '').toLowerCase() === verdictFilter.value)
    && (!q || String(row.content).toLowerCase().includes(q)));
  
  renderRows(filtered);
}

async function deleteRow(id) {
  if (!confirm('Delete this scan from your history? This cannot be undone.')) return;
  try {
    await window.csFirebase.deleteAnalysis(id);
    allRows = allRows.filter(row => row.id !== id);
    updateStatCards(allRows);
    applyFilters();
    if (typeof showToast === 'function') showToast('Scan deleted.', 'success');
  } catch (err) {
    if (typeof showToast === 'function') showToast('Could not delete scan.', 'error');
  }
}

async function loadHistory() {
  try {
    const data = await window.csFirebase.listAnalyses();
    allRows = Array.isArray(data) ? data : [];
    updateStatCards(allRows);
    applyFilters();
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px">Could not load Firestore history.</td></tr>';
    updateStatCards([]);
  }
}

searchInput.addEventListener('input', applyFilters);
typeFilter.addEventListener('change', applyFilters);
verdictFilter.addEventListener('change', applyFilters);

loadHistory();
