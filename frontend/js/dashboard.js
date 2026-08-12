/* Dashboard UI backed by the supplied Firebase project and this URL analyzer. */
const ANALYZER_API = 'http://127.0.0.1:8000';
let history = [];
const isGuest = () => localStorage.getItem('cs_guest') === 'true';
const guestHistoryKey = 'cs_guest_analyses';
const dashboardHistoryLimit = 6;
const analysisStages = [
  'Validating URL safety', 'Checking HTTP response and redirects', 'Resolving DNS records',
  'Checking domain age and registration', 'Inspecting TLS certificate', 'Checking threat reputation',
  'Rendering page in a secure browser', 'Inspecting page content, scripts and forms', 'Calculating risk score'
];
let progressTimer;

const byId = id => document.getElementById(id);
const escapeHtml = value => { const el = document.createElement('div'); el.textContent = value ?? ''; return el.innerHTML; };
const screenshotUrl = path => {
  if (!path) return null;
  if (/^https?:\/\//i.test(path)) return path;
  // Accept both the current static-mount-relative path (`screenshots/...`)
  // and the value returned by a backend that has not been restarted yet
  // (`reports/screenshots/...`).
  const cleanPath = path.replace(/^\/+/, '');
  return `${ANALYZER_API}/${cleanPath.startsWith('reports/') ? cleanPath : `reports/${cleanPath}`}`;
};

function normalizeResult(response, content) {
  const score = Math.round(response.phishing_probability || 0);
  const verdict = score >= 70 ? 'phishing' : score >= 40 ? 'suspicious' : 'safe';
  const contributors = response.data?.classification?.contributors || [];
  return {
    risk_score: score,
    verdict,
    input_type: response.data?.qr ? 'qr' : 'url',
    content,
    analyzed_at: new Date().toISOString(),
    screenshot_url: screenshotUrl(response.data?.browser?.screenshot),
    indicators: contributors.map(item => ({
      text: item.reason || 'Risk signal detected',
      level: item.impact === 'high' ? 'red' : item.impact === 'medium' ? 'amber' : 'green'
    })),
    features: response.data?.features?.values || {}
  };
}

function setLoading(loading) {
  byId('url-analyze-btn').disabled = loading;
  byId('url-spinner').style.display = loading ? 'block' : 'none';
  byId('url-btn-label').textContent = loading ? 'Analyzing…' : 'Analyze URL';
}

function setQrLoading(loading) {
  byId('image-analyze-btn').disabled = loading;
  byId('image-spinner').style.display = loading ? 'block' : 'none';
  byId('image-btn-label').textContent = loading ? 'Decoding and analyzing' : 'Decode and Analyze QR';
}

function placeProgressBelow(tabName) {
  const panel = byId('analysis-progress');
  const tab = byId(`tab-${tabName}`);
  if (panel && tab) tab.appendChild(panel);
}

function renderProgress(activeIndex, state = 'running') {
  const list = byId('analysis-progress-list');
  if (!list) return;
  list.innerHTML = analysisStages.map((stage, index) => {
    const status = state === 'failed' && index === activeIndex ? 'failed' : index < activeIndex || state === 'complete' ? 'done' : index === activeIndex ? 'active' : '';
    const icon = status === 'done' ? 'fa-circle-check' : status === 'failed' ? 'fa-circle-exclamation' : status === 'active' ? 'fa-spinner' : 'fa-circle';
    return `<div class="analysis-step ${status}"><i class="fa-solid ${icon}"></i><span>${stage}</span></div>`;
  }).join('');
  byId('analysis-progress-title').textContent = state === 'complete' ? 'Analysis complete — preparing your result' : state === 'failed' ? 'Analysis could not be completed' : analysisStages[activeIndex];
}

function startProgress() {
  const panel = byId('analysis-progress');
  panel.classList.remove('error');
  byId('analysis-progress-list').hidden = false;
  panel.classList.add('show');
  let index = 0;
  renderProgress(index);
  clearInterval(progressTimer);
  progressTimer = setInterval(() => {
    index = Math.min(index + 1, analysisStages.length - 1);
    renderProgress(index);
  }, 3500);
}

function stopProgress(state = 'complete', message = '', failedStage) {
  clearInterval(progressTimer);
  const active = state === 'complete'
    ? analysisStages.length - 1
    : failedStage ?? [...document.querySelectorAll('.analysis-step')].findIndex(item => item.classList.contains('active'));
  renderProgress(Math.max(active, 0), state);
  if (message) {
    byId('analysis-progress').classList.add('error');
    byId('analysis-progress-title').textContent = message;
    byId('analysis-progress-list').hidden = true;
  }
}

function showResultBox(result) {
  const score = result.risk_score;
  const header = byId('result-header');
  byId('result-box').classList.add('show');
  byId('risk-score').textContent = score;
  header.className = `result-header ${score >= 70 ? 'danger' : score >= 40 ? 'warning' : 'safe'}`;
  byId('verdict-icon').innerHTML = score >= 70 ? '<i class="fa-solid fa-bell"></i>' : score >= 40 ? '<i class="fa-solid fa-triangle-exclamation"></i>' : '<i class="fa-solid fa-circle-check"></i>';
  byId('verdict-text').textContent = score >= 70 ? 'High risk — likely phishing' : score >= 40 ? 'Suspicious — review carefully' : 'Safe — no threat detected';
  byId('indicator-list').innerHTML = result.indicators.map(item => `<span class="indicator ${item.level}">${escapeHtml(item.text)}</span>`).join('') || '<span class="indicator green">No high-impact indicators</span>';
}

function renderHistory() {
  const tbody = byId('history-body');
  const empty = byId('empty-state');
  // Registered users see a compact recent list on the dashboard; their full
  // archive remains on the History page. Guest sessions keep every entry here.
  const displayedHistory = isGuest() ? history : history.slice(0, dashboardHistoryLimit);
  tbody.innerHTML = displayedHistory.map(item => `<tr>
    <td><span class="type-badge ${item.inputType === 'qr' ? 'type-image' : 'type-url'}"><i class="fa-solid ${item.inputType === 'qr' ? 'fa-qrcode' : 'fa-link'}"></i> ${item.inputType === 'qr' ? 'QR code' : 'URL'}</span></td>
    <td title="${escapeHtml(item.content)}" style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(item.content)}</td>
    <td><span class="risk-pill ${item.riskScore >= 70 ? 'risk-high' : item.riskScore >= 40 ? 'risk-medium' : 'risk-low'}">${item.riskScore}</span></td>
    <td>${escapeHtml(item.verdict)}</td><td style="color:var(--gray);font-size:12px">${formatDate(item.createdAt || item.analyzedAt)}</td>
    <td><button class="action-btn" data-analysis-id="${item.id}">View</button></td>
  </tr>`).join('');
  empty.style.display = displayedHistory.length ? 'none' : 'block';
  tbody.querySelectorAll('[data-analysis-id]').forEach(button => button.addEventListener('click', () => viewResult(button.dataset.analysisId)));
}

async function refreshHistory() {
  history = isGuest() ? JSON.parse(sessionStorage.getItem(guestHistoryKey) || '[]') : await window.csFirebase.listAnalyses();
  const weekAgo = Date.now() - 7 * 86400000;
  byId('stat-total').textContent = history.length;
  byId('stat-threats').textContent = history.filter(item => item.riskScore >= 70).length;
  byId('stat-safe').textContent = history.filter(item => item.riskScore < 40).length;
  byId('stat-week').textContent = history.filter(item => new Date(item.createdAt || item.analyzedAt).getTime() >= weekAgo).length;
  renderHistory();
}

async function saveAnalysis(result, content) {
  if (!isGuest()) return window.csFirebase.saveAnalysis(result, content);
  const record = {
    id: `guest-${Date.now()}`,
    inputType: result.input_type,
    content,
    riskScore: result.risk_score,
    verdict: result.verdict,
    indicators: result.indicators || [],
    features: result.features || {},
    screenshotUrl: result.screenshot_url || null,
    analyzedAt: result.analyzed_at,
    createdAt: new Date().toISOString()
  };
  const guestHistory = JSON.parse(sessionStorage.getItem(guestHistoryKey) || '[]');
  guestHistory.unshift(record);
  sessionStorage.setItem(guestHistoryKey, JSON.stringify(guestHistory));
  return record.id;
}

function viewResult(id) {
  const item = history.find(entry => entry.id === id);
  if (!item) return;
  sessionStorage.setItem('cs_result', JSON.stringify({ risk_score: item.riskScore, verdict: item.verdict, indicators: item.indicators, input_type: item.inputType, content: item.content, analyzed_at: item.analyzedAt, features: item.features || {}, screenshot_url: item.screenshotUrl || null, analysis_id: item.id }));
  sessionStorage.setItem('cs_result_source', 'dashboard');
  location.href = 'result.html';
}

async function analyzeUrl() {
  const content = byId('url-input').value.trim();
  if (!content) return showToast('Please enter a URL first.', 'warning');
  placeProgressBelow('url');
  setLoading(true);
  startProgress();
  try {
    const response = await fetch(`${ANALYZER_API}/analyze`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: content }) });
    const body = await response.json();
    if (!response.ok || !body.success || body.exists === false) {
      throw new Error(body.exists === false ? 'URL not found.' : body.detail || body.message || 'Analysis failed.');
    }
    const result = normalizeResult(body, content);
    result.analysis_id = await saveAnalysis(result, content);
    sessionStorage.setItem('cs_result', JSON.stringify(result));
    sessionStorage.setItem('cs_result_source', 'dashboard');
    await refreshHistory();
    stopProgress('complete');
    window.setTimeout(() => { window.location.href = 'result.html'; }, 250);
  } catch (error) {
    const message = error.message || 'Analysis failed.';
    stopProgress('failed', message, message === 'URL not found.' ? 1 : undefined);
    showToast(message, 'error');
  }
  finally { setLoading(false); }
}

async function analyzeQr() {
  const file = byId('file-input')?.files?.[0];
  if (!file) return showToast('Choose a QR code image first.', 'warning');
  if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) return showToast('Use a PNG, JPEG, or WebP image.', 'warning');
  if (file.size > 5 * 1024 * 1024) return showToast('QR code images must be 5 MB or smaller.', 'warning');

  placeProgressBelow('image');
  setQrLoading(true);
  startProgress();
  try {
    const formData = new FormData();
    formData.append('image', file);
    const response = await fetch(`${ANALYZER_API}/analyze/qr`, { method: 'POST', body: formData });
    const body = await response.json();
    if (!response.ok || !body.success || body.exists === false) {
      throw new Error(body.detail || body.message || 'QR code analysis failed.');
    }
    const decodedUrl = body.data?.qr?.decoded_value;
    if (!decodedUrl) throw new Error('The QR code was decoded, but no website URL was returned.');
    // A QR often points at a short-link service. Show and save the final page
    // Chromium actually opened, which is also the source of the screenshot.
    const renderedUrl = body.data?.browser?.final_url || body.normalized_url || decodedUrl;
    const result = normalizeResult(body, renderedUrl);
    result.input_type = 'qr';
    result.analysis_id = await saveAnalysis(result, renderedUrl);
    sessionStorage.setItem('cs_result', JSON.stringify(result));
    sessionStorage.setItem('cs_result_source', 'dashboard');
    await refreshHistory();
    stopProgress('complete');
    window.setTimeout(() => { window.location.href = 'result.html'; }, 250);
  } catch (error) {
    const message = error.message || 'QR code analysis failed.';
    stopProgress('failed', message);
    showToast(message, 'error');
  } finally {
    setQrLoading(false);
  }
}

document.querySelectorAll('.tab').forEach(tab => tab.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach(item => item.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(item => item.classList.remove('active'));
  tab.classList.add('active'); byId(`tab-${tab.dataset.tab}`).classList.add('active');
}));
byId('url-analyze-btn')?.addEventListener('click', analyzeUrl);
byId('url-input')?.addEventListener('keydown', event => {
  if (event.key !== 'Enter') return;
  event.preventDefault();
  analyzeUrl();
});
byId('url-paste-btn')?.addEventListener('click', async () => {
  try {
    const clipboardText = await navigator.clipboard.readText();
    if (!clipboardText.trim()) return showToast('Your clipboard is empty.', 'warning');
    const input = byId('url-input');
    input.value = clipboardText.trim();
    input.focus();
  } catch (error) {
    showToast('Clipboard access was blocked. Please paste with Ctrl+V.', 'warning');
  }
});
byId('email-analyze-btn')?.addEventListener('click', () => showToast('URL analysis is currently available.', 'info'));
byId('image-analyze-btn')?.addEventListener('click', analyzeQr);
byId('file-drop')?.addEventListener('click', () => byId('file-input')?.click());
function setQrFile(file) {
  if (file) {
    const transfer = new DataTransfer();
    transfer.items.add(file);
    byId('file-input').files = transfer.files;
  }
  byId('file-name').textContent = file ? file.name : '';
  byId('file-name').style.display = file ? 'block' : 'none';
}
byId('file-input')?.addEventListener('change', event => {
  const file = event.target.files?.[0];
  byId('file-name').textContent = file ? file.name : '';
  byId('file-name').style.display = file ? 'block' : 'none';
});
byId('qr-paste-btn')?.addEventListener('click', async () => {
  try {
    const items = await navigator.clipboard.read();
    const imageItem = items.find(item => item.types.some(type => ['image/png', 'image/jpeg', 'image/webp'].includes(type)));
    const imageType = imageItem?.types.find(type => ['image/png', 'image/jpeg', 'image/webp'].includes(type));
    if (!imageItem || !imageType) return showToast('No supported QR image was found in your clipboard.', 'warning');
    const blob = await imageItem.getType(imageType);
    setQrFile(new File([blob], `pasted-qr.${imageType.split('/')[1]}`, { type: imageType }));
    showToast('QR image pasted. Select Decode and Analyze QR to continue.', 'success');
  } catch (error) {
    showToast('Clipboard image access was blocked. Allow clipboard access or upload the QR image instead.', 'warning');
  }
});
byId('file-drop')?.addEventListener('dragover', event => { event.preventDefault(); byId('file-drop').classList.add('drag-over'); });
byId('file-drop')?.addEventListener('dragleave', () => byId('file-drop').classList.remove('drag-over'));
byId('file-drop')?.addEventListener('drop', event => {
  event.preventDefault();
  const file = event.dataTransfer.files?.[0];
  if (file) setQrFile(file);
  byId('file-drop').classList.remove('drag-over');
});
byId('clear-history-btn')?.addEventListener('click', async () => {
  if (!history.length || !confirm('Clear all saved analyses?')) return;
  if (isGuest()) sessionStorage.removeItem(guestHistoryKey);
  else await Promise.all(history.map(item => window.csFirebase.deleteAnalysis(item.id)));
  await refreshHistory();
});
refreshHistory().catch(error => showToast(error.message, 'error'));
