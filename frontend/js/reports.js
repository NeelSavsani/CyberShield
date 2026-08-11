/* Firestore-backed reports list with search, filters, and PDF downloads. */
let allReports = [];
const tbody = document.getElementById('reports-body');
const emptyState = document.getElementById('empty-state');
const searchInput = document.getElementById('search-input');
const typeSel = document.getElementById('type-filter');
const verdictSel = document.getElementById('verdict-filter');
const escapeHtml = value => { const el = document.createElement('div'); el.textContent = value ?? ''; return el.innerHTML; };

function render(rows) {
  emptyState.style.display = rows.length ? 'none' : 'block';
  tbody.innerHTML = rows.map(row => `<tr><td>#${row.id.slice(0, 8)}</td><td>${row.inputType}</td>
    <td style="max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(row.content)}</td>
    <td><span class="badge badge-${row.verdict}">${row.verdict}</span></td>
    <td>${new Date(row.createdAt || row.analyzedAt).toLocaleString('en-IN')}</td>
    <td><button class="action-btn-lg btn-report" data-report="${row.id}"><i class="fa-solid fa-download"></i> Download</button></td></tr>`).join('');
  document.querySelectorAll('[data-report]').forEach(button => button.addEventListener('click', () => {
    const row = allReports.find(entry => entry.id === button.dataset.report);
    if (row) window.cyberShieldReport.download(row, button).catch(() => showToast('Could not generate the PDF report.', 'error'));
  }));
}

function applyFilters() {
  const query = (searchInput.value || '').trim().toLowerCase();
  render(allReports.filter(row =>
    (!typeSel.value || row.inputType === typeSel.value)
    && (!verdictSel.value || row.verdict === verdictSel.value)
    && (!query || String(row.content || '').toLowerCase().includes(query))
  ));
}

/* Legacy fallback retained for direct integrations that call downloadReport(row). */
function downloadReport(row) {
  if (window.cyberShieldReport) return window.cyberShieldReport.download(row);
  const lines = [
    'CyberShield Analysis Report',
    '',
    `Content: ${row.content}`,
    `Type: ${row.inputType || 'N/A'}`,
    `Verdict: ${row.verdict || 'Unknown'}`,
    `Risk score: ${row.riskScore ?? 0}/100`,
    `Analyzed at: ${new Date(row.analyzedAt || row.createdAt).toLocaleString('en-IN')}`,
    '',
    'Threat indicators'
  ];
  const indicators = Array.isArray(row.indicators) && row.indicators.length
    ? row.indicators.map(item => item.text || item).join('; ')
    : 'No threat indicators detected.';
  lines.push(...wrapReportText(indicators));

  const features = Object.entries(row.features || {});
  if (features.length) {
    lines.push('', 'Feature breakdown');
    features.forEach(([name, value]) => lines.push(...wrapReportText(`${name}: ${value}`)));
  }

  const pdf = createPdf(lines);
  const url = URL.createObjectURL(new Blob([pdf], { type: 'application/pdf' }));
  const link = document.createElement('a');
  const filename = `CyberShield-${String(row.id).slice(0, 8)}.pdf`;
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function wrapReportText(value, maxLength = 88) {
  const words = String(value ?? 'Not available').split(/\s+/);
  const lines = [];
  let line = '';
  words.forEach(word => {
    if (`${line} ${word}`.trim().length > maxLength && line) {
      lines.push(line);
      line = word;
    } else {
      line = `${line} ${word}`.trim();
    }
  });
  if (line) lines.push(line);
  return lines;
}

function createPdf(lines) {
  const safe = value => String(value).replace(/[^\x20-\x7E]/g, '?').replace(/([\\()])/g, '\\$1');
  const pages = [];
  for (let index = 0; index < lines.length; index += 42) pages.push(lines.slice(index, index + 42));

  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    `<< /Type /Pages /Kids [${pages.map((_, index) => `${4 + index * 2} 0 R`).join(' ')}] /Count ${pages.length} >>`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>'
  ];
  pages.forEach((page, index) => {
    const pageId = 4 + index * 2;
    const contentId = pageId + 1;
    const content = ['BT', '/F1 16 Tf', '50 800 Td'];
    page.forEach((line, lineIndex) => {
      if (lineIndex === 1) content.push('/F1 11 Tf');
      content.push(`(${safe(line)}) Tj`, '0 -16 Td');
    });
    const stream = content.concat('ET').join('\n');
    objects[pageId - 1] = `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents ${contentId} 0 R >>`;
    objects[contentId - 1] = `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`;
  });

  let pdf = '%PDF-1.4\n';
  const offsets = [0];
  objects.forEach((object, index) => {
    offsets.push(pdf.length);
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });
  const xref = pdf.length;
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  offsets.slice(1).forEach(offset => { pdf += `${String(offset).padStart(10, '0')} 00000 n \n`; });
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  return pdf;
}

async function loadReports() {
  try {
    allReports = await window.csFirebase.listAnalyses();
    document.getElementById('sum-total').textContent = allReports.length;
    document.getElementById('sum-safe').textContent = allReports.filter(row => row.verdict === 'safe').length;
    document.getElementById('sum-phishing').textContent = allReports.filter(row => row.verdict === 'phishing').length;
    document.getElementById('sum-suspicious').textContent = allReports.filter(row => row.verdict === 'suspicious').length;
    applyFilters();
  } catch { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px">Could not load Firestore reports.</td></tr>'; }
}
searchInput.addEventListener('input', applyFilters);
typeSel.addEventListener('change', applyFilters);
verdictSel.addEventListener('change', applyFilters);
loadReports();
