/**
 * CyberShield — result.js
 * Handles rendering the full analysis result page.
 * Reads result data from sessionStorage set by dashboard.js
 */

// ── Render result ─────────────────────────────────────────────
function renderResult(result) {
  const score      = result.risk_score   ?? 0;
  const verdict    = result.verdict      ?? 'safe';
  const indicators = result.indicators   ?? [];
  const inputType  = result.input_type   ?? 'url';
  const content    = result.content      ?? '—';
  const features   = result.features     ?? {};
  // An image must belong to this specific analysis.  Do not fall back to a
  // shared "latest" image: it may have been captured for a different URL.
  const screenshot = result.screenshot_url || null;
  const time = (() => {
    if (!result.analyzed_at) return new Date().toLocaleString('en-IN');
    const d = new Date(result.analyzed_at);
    // History rows come back as an already-formatted string like
    // "02 Aug 2026, 12:17" rather than ISO — show it as-is if it
    // doesn't parse into a real date instead of printing "Invalid Date".
    return isNaN(d.getTime()) ? String(result.analyzed_at) : d.toLocaleString('en-IN');
  })();

  // ── Verdict banner ──────────────────────────────────────────
  const banner   = document.getElementById('verdict-banner');
  const emoji    = document.getElementById('verdict-emoji');
  const title    = document.getElementById('verdict-title');
  const subtitle = document.getElementById('verdict-subtitle');
  const scoreEl  = document.getElementById('score-number');
  const bar      = document.getElementById('score-bar');

  if (verdict === 'phishing') {
    banner.className = 'verdict-banner danger';
    emoji.innerHTML   = '<i class="fa-solid fa-bell"></i>';
    title.textContent   = 'Phishing Detected';
    subtitle.textContent= 'This content shows strong signs of being a phishing attempt.';
    bar.style.background= '#DC2626';
  } else if (verdict === 'suspicious') {
    banner.className = 'verdict-banner warning';
    emoji.innerHTML   = '<i class="fa-solid fa-triangle-exclamation"></i>';
    title.textContent   = 'Suspicious Content';
    subtitle.textContent= 'This content has suspicious characteristics. Review carefully.';
    bar.style.background= '#D97706';
  } else {
    banner.className = 'verdict-banner safe';
    emoji.innerHTML   = '<i class="fa-solid fa-circle-check"></i>';
    title.textContent   = 'Looks Safe';
    subtitle.textContent= 'No significant phishing patterns were detected.';
    bar.style.background= '#059669';
  }

  scoreEl.textContent = score;
  setTimeout(() => { bar.style.width = score + '%'; }, 150);

  // ── Meta row ────────────────────────────────────────────────
  const typeLabels = { url: '<i class="fa-solid fa-link"></i> URL', email: '<i class="fa-solid fa-envelope"></i> Email / Text', image: '<i class="fa-solid fa-image"></i> Screenshot' };
  document.getElementById('meta-type').innerHTML      = typeLabels[inputType] || inputType;
  document.getElementById('meta-time').textContent    = time;
  const contentEl = document.getElementById('meta-content');
  contentEl.textContent = content;
  contentEl.title = content;
  if (inputType === 'url') {
    contentEl.href = content;
  } else {
    contentEl.removeAttribute('href');
  }

  const overview = document.getElementById('content-overview');
  const screenshotEl = document.getElementById('content-screenshot');
  if (screenshot) {
    screenshotEl.src = screenshot;
    screenshotEl.onerror = () => { overview.hidden = true; };
    overview.hidden = false;
  } else {
    overview.hidden = true;
  }

  // ── Recommendation ──────────────────────────────────────────
  const rec      = document.getElementById('recommendation');
  const recIcon  = document.getElementById('rec-icon');
  const recTitle = document.getElementById('rec-title');
  const recBody  = document.getElementById('rec-body');

  const recommendations = {
    phishing: {
      cls:   'danger',
      icon:  '<i class="fa-solid fa-ban"></i>',
      title: 'Do NOT proceed — this is likely phishing.',
      body:  'Do not click any links, enter personal information, or download attachments from this source. If this is an email, mark it as spam and delete it. Report it to your IT administrator or cybercrime authority.'
    },
    suspicious: {
      cls:   'warning',
      icon:  '<i class="fa-solid fa-triangle-exclamation"></i>',
      title: 'Proceed with extreme caution.',
      body:  'This content has suspicious characteristics but is not definitively phishing. Verify the sender\'s identity through a separate channel before clicking links or entering any information. When in doubt, don\'t.'
    },
    safe: {
      cls:   'safe',
      icon:  '<i class="fa-solid fa-circle-check"></i>',
      title: 'This content appears to be safe.',
      body:  'Our analysis did not detect significant phishing indicators. However, always stay alert — no automated system is 100% accurate. If something still feels off, trust your instincts and verify manually.'
    }
  };

  const r = recommendations[verdict];
  rec.className        = 'recommendation ' + r.cls;
  recIcon.innerHTML    = r.icon;
  recTitle.textContent = r.title;
  recBody.textContent  = r.body;

  // ── Indicators ──────────────────────────────────────────────
  const grid  = document.getElementById('indicator-grid');
  const count = document.getElementById('indicator-count');
  count.textContent = indicators.length + ' found';

  const descs = {
    'No HTTPS (insecure connection)':             'Legitimate sites almost always use HTTPS. HTTP-only sites are a red flag.',
    'IP address used instead of domain':          'Attackers use raw IP addresses to avoid domain registration checks.',
    'Multiple brand names in URL (impersonation)':'Putting brand names like "paypal" in the URL is a classic phishing trick.',
    'Suspicious top-level domain':                'Domains like .xyz, .top, .tk are cheap and frequently used in phishing.',
    'Excessive hyphens in domain':                'paypal-secure-verify-login.com — hyphens are used to look legitimate.',
    'Strong urgency language detected':           '"Act immediately", "account suspended" — designed to panic you.',
    'Brand impersonation detected':               'The message pretends to be from a known company to gain your trust.',
    'Requests sensitive personal information':    'Legitimate services never ask for passwords or card numbers over email.',
    'Logo resembles brand but is not identical':  'A slightly altered logo is a common visual phishing technique.',
  };

  if (!indicators.length) {
    grid.innerHTML = '<p style="color:var(--gray);font-size:14px">No threat indicators detected.</p>';
  } else {
    const levelOrder = { red: 0, amber: 1, green: 2 };
    const sorted = [...indicators].sort((a,b) =>
      (levelOrder[a.level] ?? 2) - (levelOrder[b.level] ?? 2)
    );
    grid.innerHTML = sorted.map(ind => {
      const desc = Object.entries(descs).find(([k]) => ind.text.toLowerCase().includes(k.toLowerCase()));
      return `
        <div class="indicator-row ${ind.level}">
          <div class="indicator-dot"></div>
          <div class="indicator-content">
            <div class="indicator-text">${ind.text}</div>
            ${desc ? `<div class="indicator-desc">${desc[1]}</div>` : ''}
          </div>
          <span class="indicator-badge">${ind.level === 'red' ? 'HIGH' : ind.level === 'amber' ? 'MEDIUM' : 'INFO'}</span>
        </div>`;
    }).join('');
  }

  // ── Feature breakdown ────────────────────────────────────────
  const featureBody = document.getElementById('feature-body');
  const featureKeys = Object.keys(features).filter(k =>
    !['filename','extraction_error','bbox','best_match','is_spoofed','risk_level'].includes(k)
  );

  const riskOf = (key, val) => {
    const highRisk = ['uses_ip_address','has_redirect_param','at_count','suspicious_tld','is_spoofed'];
    const medRisk  = ['hyphen_count','brand_keyword_count','subdomain_count','url_entropy'];
    if (highRisk.includes(key) && val > 0)  return ['risk-h','High'];
    if (medRisk.includes(key)  && val > 1)  return ['risk-m','Medium'];
    if (key === 'has_https'    && val === 0) return ['risk-h','High'];
    return ['risk-l','Low'];
  };

  if (!featureKeys.length) {
    featureBody.innerHTML = '<tr><td colspan="3" style="color:var(--gray);padding:16px">Feature data not available for this input type.</td></tr>';
  } else {
    featureBody.innerHTML = featureKeys.map(key => {
      const val   = features[key];
      const [cls, lbl] = riskOf(key, val);
      const label = key.replace(/_/g,' ').replace(/\b\w/g, l => l.toUpperCase());
      return `<tr>
        <td>${label}</td>
        <td><span class="feature-val">${val}</span></td>
        <td><span class="feature-risk ${cls}">${lbl}</span></td>
      </tr>`;
    }).join('');
  }
}

// ── Download report ──────────────────────────────────────────
function downloadReport() {
  const result = JSON.parse(sessionStorage.getItem('cs_result') || '{}');
  const id     = result.analysis_id;
  if (id) {
    window.print();
  } else {
    showToast('Save the analysis first to generate a report.', 'warning');
  }
}

// ── Flag as phishing ─────────────────────────────────────────
async function flagItem() {
  const result  = JSON.parse(sessionStorage.getItem('cs_result') || '{}');
  const content = result.content || '';
  const type    = result.input_type === 'url' ? 'url' : 'keyword';
  try {
    const res  = await fetch(`${API}/admin/flag`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ item_type: type, value: content, reason: 'Flagged by user', admin_id: 1 })
    });
    const data = await res.json();
    if (data.success) showToast('Flagged successfully! Added to phishing database.', 'success');
    else showToast('Could not flag item.', 'error');
  } catch(e) {
    showToast('Could not connect to server. Is Flask running?', 'error');
  }
}

// ── Init ─────────────────────────────────────────────────────
// (API base URL comes from main.js, loaded before this file —
// see the note in dashboard.js for why it isn't redeclared here.)
const resultRaw = sessionStorage.getItem('cs_result');
const resultSource = sessionStorage.getItem('cs_result_source');
const historyBackButton = document.getElementById('history-back-btn');

if (resultSource === 'history') {
  historyBackButton.hidden = false;
}

if (resultRaw) {
  renderResult(JSON.parse(resultRaw));
} else {
  // Demo result shown if page is opened directly
  renderResult({
    risk_score:  82,
    verdict:     'phishing',
    input_type:  'url',
    content:     'http://paypal-secure-login.net/verify?token=abc123',
    analyzed_at: new Date().toISOString(),
    indicators: [
      { text: 'No HTTPS (insecure connection)',              level: 'red' },
      { text: 'Multiple brand names in URL (impersonation)',  level: 'red' },
      { text: 'Suspicious top-level domain',                 level: 'amber' },
      { text: 'Excessive hyphens in domain',                 level: 'amber' },
    ],
    features: {
      url_length: 51, dot_count: 2, hyphen_count: 2,
      has_https: 0, uses_ip_address: 0, brand_keyword_count: 2,
      suspicious_tld: 1, url_entropy: 3.94, subdomain_count: 0,
    }
  });
}
