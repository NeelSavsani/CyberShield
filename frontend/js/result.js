/**
 * CyberShield — result.js
 * Handles rendering the full analysis result page.
 * Reads result data from sessionStorage set by dashboard.js
 */

// ── Render result ─────────────────────────────────────────────
const featureDetails = {
  domain_age_days: ['Domain age', 'How many days the domain has existed. Very new domains deserve extra scrutiny because phishing campaigns often use newly registered addresses.'],
  certificate_age_days: ['Certificate age', 'How many days ago the site TLS certificate was issued. A new certificate is common for legitimate new or renewed sites, but is useful context when combined with other warnings.'],
  domain_age_risk: ['Domain age risk', 'A 0 to 1 score derived from domain age. Higher values mean the domain is newer and may require more verification.'],
  certificate_age_risk: ['Certificate age risk', 'A 0 to 1 score derived from certificate age. Higher values indicate a more recently issued certificate.'],
  dnssec_enabled: ['DNSSEC enabled', 'DNSSEC helps protect DNS records from being forged. 1 means it is enabled; 0 means the check did not find it. Its absence alone does not make a site unsafe.'],
  http_reachable: ['HTTP reachable', 'Whether CyberShield could successfully reach the website. 1 means reachable; 0 means it could not be reached during the scan.'],
  redirect_count: ['Redirect count', 'How many times the site sent the browser to another address. A few redirects can be normal, but many can be used to hide the final destination.'],
  has_valid_tls: ['Valid TLS', 'Whether the site presented a usable HTTPS security certificate. 1 means a certificate was available; 0 means HTTPS protection was not confirmed.'],
  password_field_count: ['Password fields', 'The number of password-entry fields found. Password forms are common on real login pages but are especially important to inspect on an unfamiliar site.'],
  otp_field_count: ['One-time-password fields', 'The number of fields asking for a verification or one-time code. Unexpected requests for these codes can be a sign of account takeover attempts.'],
  credit_card_field_count: ['Credit card fields', 'The number of payment-card fields found. Only provide card details after independently confirming that a website and checkout process are legitimate.'],
  cross_domain_form_actions: ['Cross-domain form actions', 'Forms that submit your information to a different domain. This can be legitimate for payment providers, but it can also send credentials to an attacker-controlled site.'],
  insecure_form_actions: ['Insecure form actions', 'Forms that submit data without HTTPS protection. Information entered there could be exposed while it is sent.'],
  get_login_forms: ['GET login forms', 'Login forms that put submitted values in the web address rather than the protected request body. This can expose sensitive data in browser history or logs.'],
  hidden_iframe_count: ['Hidden iframes', 'Invisible embedded pages found in the site. They can be harmless, but are sometimes used to load unwanted content or conceal activity.'],
  meta_refresh_present: ['Meta refresh', 'Whether the page uses an automatic refresh or redirect. It can be used legitimately, but attackers sometimes use it to move visitors to another page.'],
  popup_count: ['Popups', 'The number of browser pop-up windows opened during the scan. Unexpected pop-ups can pressure users or lead them away from the original site.'],
  download_count: ['Downloads', 'The number of files the page attempted to download. Unexpected downloads should be treated carefully, especially from an untrusted site.'],
  permission_request_count: ['Permission requests', 'The number of browser permissions requested, such as notifications, camera, or location. Unexpected requests can be used for spam or data collection.'],
  javascript_error_count: ['JavaScript errors', 'The number of script errors seen while loading the page. Errors are not automatically malicious but can indicate a poorly functioning or suspicious page.'],
  obfuscated_script_count: ['Obfuscated scripts', 'The number of scripts intentionally made hard to read. Obfuscation can protect legitimate code, but it is also often used to conceal malicious behavior.'],
  reputation_detection_count: ['Reputation detections', 'How many reputation sources flagged this site or content. More detections generally increase confidence that it may be unsafe.'],
  safe_browsing_flagged: ['Safe Browsing flag', 'Whether a Safe Browsing-style reputation source flagged the site. 1 means it was flagged and should be avoided; 0 means no flag was returned.']
};

function openFeatureInfo(key, value) {
  const [title, description] = featureDetails[key] || [key.replace(/_/g, ' '), 'This is a signal collected by CyberShield during the analysis. Review it together with the verdict and other evidence.'];
  document.getElementById('feature-info-title').textContent = title;
  document.getElementById('feature-info-description').textContent = description;
  document.getElementById('feature-info-value').textContent = value ?? 'Not available';
  document.getElementById('feature-info-note').textContent = 'No single feature decides whether a website is safe. CyberShield considers multiple signals together.';
  document.getElementById('feature-info-modal').hidden = false;
}

function closeFeatureInfo() { document.getElementById('feature-info-modal').hidden = true; }

// Short, non-verbal result notification. Web Audio keeps this lightweight
// and avoids shipping an additional audio asset; browsers may still suppress
// it when the result page was opened without a user gesture.
function playResultNotification(result) {
  if (result.verdict !== 'safe' && result.verdict !== 'phishing') return;
  const key = `cs_result_sound:${result.analysis_id || result.analyzed_at || result.content || 'current'}`;
  if (sessionStorage.getItem(key)) return;
  sessionStorage.setItem(key, '1');
  try {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    const context = new AudioContextClass();
    const gain = context.createGain();
    gain.gain.setValueAtTime(0.0001, context.currentTime);
    gain.connect(context.destination);
    const now = context.currentTime;
    const safe = result.verdict === 'safe';
    const notes = safe ? [660, 880, 1047] : [240, 180, 120];
    notes.forEach((frequency, index) => {
      const oscillator = context.createOscillator();
      oscillator.type = safe ? 'sine' : 'sawtooth';
      oscillator.frequency.setValueAtTime(frequency, now + index * (safe ? 0.13 : 0.16));
      const start = now + index * (safe ? 0.13 : 0.16);
      const end = start + (safe ? 0.22 : 0.14);
      oscillator.connect(gain);
      oscillator.start(start);
      oscillator.stop(end);
    });
    gain.gain.exponentialRampToValueAtTime(0.12, now + 0.03);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + (safe ? 0.62 : 0.58));
    window.setTimeout(() => context.close().catch(() => {}), 900);
  } catch (_) {
    // Audio is optional; never let a browser autoplay restriction affect the
    // displayed analysis result.
  }
}

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
  const typeLabels = { url: '<i class="fa-solid fa-link"></i> URL', qr: '<i class="fa-solid fa-qrcode"></i> QR code URL', email: '<i class="fa-solid fa-envelope"></i> Email / Text', image: '<i class="fa-solid fa-image"></i> Screenshot' };
  document.getElementById('meta-type').innerHTML      = typeLabels[inputType] || inputType;
  document.getElementById('meta-time').textContent    = time;
  const contentEl = document.getElementById('meta-content');
  contentEl.textContent = content;
  contentEl.title = content;
  if (inputType === 'url' || inputType === 'qr') {
    // QR values often contain a bare domain. Prefix it before assigning href,
    // otherwise the browser treats it as a local relative path.
    const externalUrl = /^[a-z][a-z\d+.-]*:\/\//i.test(content) ? content : `https://${String(content).trim()}`;
    try {
      const parsedUrl = new URL(externalUrl);
      contentEl.href = parsedUrl.href;
      contentEl.target = '_blank';
      contentEl.rel = 'noopener noreferrer';
    } catch {
      contentEl.removeAttribute('href');
    }
  } else {
    contentEl.removeAttribute('href');
  }

  const overview = document.getElementById('content-overview');
  const screenshotEl = document.getElementById('content-screenshot');
  const overviewNote = overview.querySelector('.content-overview-note');
  // Website screenshots are evidence for URL and QR scans only. Text/email
  // analyses do not open a browser, so do not show an empty screenshot card.
  const supportsScreenshot = inputType === 'url' || inputType === 'qr';
  if (!supportsScreenshot) {
    overview.hidden = true;
  } else if (screenshot) {
    screenshotEl.src = screenshot;
    screenshotEl.onerror = () => {
      // Keep the evidence section visible when a remote/local image expires
      // or is blocked by a storage rule. Hiding the whole panel made a valid
      // analysis look as if it contained no page evidence.
      screenshotEl.hidden = true;
      if (overviewNote) overviewNote.textContent = 'The analysis completed, but the page preview is currently unavailable.';
    };
    screenshotEl.hidden = false;
    if (overviewNote) overviewNote.textContent = 'This preview is captured in CyberShield’s isolated browser session.';
    overview.hidden = false;
  } else {
    screenshotEl.hidden = true;
    if (overviewNote) overviewNote.textContent = 'The browser did not return a screenshot for this analysis.';
    overview.hidden = false;
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

  // Plain-language explanations make each technical signal actionable.
  const explanations = [
    ['recently issued tls certificate', 'This website certificate was created recently. New certificates are normal for new or renewed sites, but phishing sites can obtain them quickly too. Treat this as context, not proof that the site is unsafe.'],
    ['no https', 'The website does not encrypt information sent between your browser and the site. Someone on the network could potentially read or change data such as passwords or payment details.'],
    ['ip address used instead of domain', 'The link uses a numeric server address instead of a normal website name. Attackers sometimes do this to hide who operates the site and avoid domain reputation checks.'],
    ['multiple brand names', 'The address includes one or more well-known brand names. Scammers often add these names to make a fake page look connected to a trusted company.'],
    ['suspicious top-level domain', 'The ending of this web address is commonly seen in phishing campaigns. It does not make every site with this ending dangerous, but it deserves extra verification.'],
    ['excessive hyphens', 'The address uses several hyphens, which can make a fake domain resemble a real brand or service name at a quick glance.'],
    ['urgency language', 'The message uses pressure or a tight deadline. This is a common tactic intended to make you act before you can verify the request.'],
    ['brand impersonation', 'The content appears to claim it is from a known company. Verify the sender and website independently before signing in or sharing information.'],
    ['sensitive personal information', 'The content asks for information such as a password, card number, or identity details. Legitimate organisations rarely ask for these through an unexpected message or link.'],
    ['logo resembles brand', 'The logo looks similar to a trusted brand but is not an exact match. Small visual changes are often used to make fraudulent pages appear legitimate.']
  ];
  const explainIndicator = (text, level) => {
    const match = explanations.find(([term]) => text.toLowerCase().includes(term));
    if (match) return match[1];
    if (level === 'red') return 'This signal is strongly associated with phishing or unsafe content. Do not enter information or download files until you have verified the source independently.';
    if (level === 'amber') return 'This signal can occur on legitimate sites, but it is also used in scams. Check the website address and source carefully before continuing.';
    return 'This is additional context from the security scan. On its own it does not prove the site is dangerous, but it can help you make a safer decision.';
  };
  const escapeHtml = value => String(value).replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));

  if (!indicators.length) {
    grid.innerHTML = '<p style="color:var(--gray);font-size:14px">No threat indicators detected.</p>';
  } else {
    const levelOrder = { red: 0, amber: 1, green: 2 };
    const sorted = [...indicators].sort((a,b) =>
      (levelOrder[a.level] ?? 2) - (levelOrder[b.level] ?? 2)
    );
    grid.innerHTML = sorted.map(ind => {
      const text = String(ind.text || 'Unspecified security signal');
      const description = explainIndicator(text, ind.level);
      return `
        <div class="indicator-row ${ind.level}">
          <div class="indicator-dot"></div>
          <div class="indicator-content">
            <div class="indicator-text">${escapeHtml(text)}</div>
            <div class="indicator-desc">${escapeHtml(description)}</div>
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
    featureBody.innerHTML = '<tr><td colspan="4" style="color:var(--gray);padding:16px">Feature data not available for this input type.</td></tr>';
  } else {
    featureBody.innerHTML = featureKeys.map(key => {
      const val   = features[key];
      const [cls, lbl] = riskOf(key, val);
      const label = key.replace(/_/g,' ').replace(/\b\w/g, l => l.toUpperCase());
      return `<tr>
        <td>${label}</td>
        <td><span class="feature-val">${val}</span></td>
        <td><span class="feature-risk ${cls}">${lbl}</span></td>
        <td><button class="feature-info-btn" type="button" data-feature-key="${key}" data-feature-value="${String(val)}" aria-label="Explain ${label}" title="Explain ${label}"><i class="fa-solid fa-circle-info"></i></button></td>
      </tr>`;
    }).join('');
    featureBody.querySelectorAll('[data-feature-key]').forEach(button => button.addEventListener('click', () => openFeatureInfo(button.dataset.featureKey, button.dataset.featureValue)));
  }
}

// ── Download report ──────────────────────────────────────────
function downloadReport(event) {
  const result = JSON.parse(sessionStorage.getItem('cs_result') || '{}');
  if (Object.keys(result).length) {
    window.cyberShieldReport.download(result, event?.currentTarget)
      .catch(() => showToast('Could not generate the PDF report. Please try again.', 'error'));
  } else {
    showToast('Run an analysis first to generate a report.', 'warning');
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

document.querySelectorAll('[data-close-feature-info]').forEach(button => button.addEventListener('click', closeFeatureInfo));
document.addEventListener('keydown', event => { if (event.key === 'Escape') closeFeatureInfo(); });

if (resultSource === 'history') {
  historyBackButton.hidden = false;
}

if (resultRaw) {
  const result = JSON.parse(resultRaw);
  renderResult(result);
  playResultNotification(result);
} else {
  // Demo result shown if page is opened directly
  const demoResult = {
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
  };
  renderResult(demoResult);
  playResultNotification(demoResult);
}
