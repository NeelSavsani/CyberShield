/* Firestore-backed reports list. Use the browser print dialog from the result page to save a PDF. */
let allReports = [];
const tbody = document.getElementById('reports-body');
const emptyState = document.getElementById('empty-state');
const verdictSel = document.getElementById('verdict-filter');
const escapeHtml = value => { const el = document.createElement('div'); el.textContent = value ?? ''; return el.innerHTML; };

function render(rows) {
  emptyState.style.display = rows.length ? 'none' : 'block';
  tbody.innerHTML = rows.map(row => `<tr><td>#${row.id.slice(0, 8)}</td><td>${row.inputType}</td>
    <td style="max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(row.content)}</td>
    <td><span class="badge badge-${row.verdict}">${row.verdict}</span></td>
    <td>${new Date(row.createdAt || row.analyzedAt).toLocaleString('en-IN')}</td>
    <td><button class="action-btn-lg btn-report" data-report="${row.id}"><i class="fa-solid fa-eye"></i> View</button></td></tr>`).join('');
  document.querySelectorAll('[data-report]').forEach(button => button.addEventListener('click', () => {
    const row = allReports.find(entry => entry.id === button.dataset.report);
    sessionStorage.setItem('cs_result', JSON.stringify({
      risk_score: row.riskScore,
      verdict: row.verdict,
      indicators: row.indicators,
      input_type: row.inputType,
      content: row.content,
      analyzed_at: row.analyzedAt || row.createdAt,
      features: row.features || {},
      screenshot_url: row.screenshotUrl || null,
      analysis_id: row.id
    }));
    window.location.href = 'result.html';
  }));
}
function applyFilter() { render(verdictSel.value ? allReports.filter(row => row.verdict === verdictSel.value) : allReports); }
async function loadReports() {
  try {
    allReports = await window.csFirebase.listAnalyses();
    document.getElementById('sum-total').textContent = allReports.length;
    document.getElementById('sum-safe').textContent = allReports.filter(row => row.verdict === 'safe').length;
    document.getElementById('sum-phishing').textContent = allReports.filter(row => row.verdict === 'phishing').length;
    document.getElementById('sum-suspicious').textContent = allReports.filter(row => row.verdict === 'suspicious').length;
    applyFilter();
  } catch { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px">Could not load Firestore reports.</td></tr>'; }
}
verdictSel.addEventListener('change', applyFilter);
loadReports();
