/* Branded, client-side PDF reports shared by the Result and Reports pages. */
(function () {
  const CDN = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';

  function loadJsPdf() {
    if (window.jspdf && window.jspdf.jsPDF) return Promise.resolve(window.jspdf.jsPDF);
    return new Promise((resolve, reject) => {
      const existing = document.querySelector('script[data-cybershield-jspdf]');
      if (existing) {
        existing.addEventListener('load', () => resolve(window.jspdf.jsPDF), { once: true });
        existing.addEventListener('error', reject, { once: true });
        return;
      }
      const script = document.createElement('script');
      script.src = CDN;
      script.async = true;
      script.dataset.cybershieldJspdf = 'true';
      script.onload = () => resolve(window.jspdf.jsPDF);
      script.onerror = () => reject(new Error('The PDF library could not be loaded.'));
      document.head.appendChild(script);
    });
  }

  const clean = value => String(value ?? 'Not available').replace(/[\u0000-\u001F\u007F-\uFFFF]/g, ' ').replace(/\s+/g, ' ').trim();
  const titleCase = value => clean(value).replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase());
  const verdictInfo = verdict => ({
    phishing: { label: 'PHISHING DETECTED', color: [220, 38, 38], note: 'Do not proceed. Avoid links, downloads, and requests for personal information.' },
    suspicious: { label: 'SUSPICIOUS CONTENT', color: [217, 119, 6], note: 'Proceed with caution and verify the source through an independent channel.' },
    safe: { label: 'NO SIGNIFICANT THREAT DETECTED', color: [5, 150, 105], note: 'No major phishing indicators were detected. Continue to use normal security precautions.' }
  }[String(verdict || '').toLowerCase()] || { label: 'ANALYSIS COMPLETE', color: [8, 145, 178], note: 'Review the evidence below before making a decision.' });

  function normalized(row) {
    return {
      id: row.analysis_id || row.id || 'analysis', content: row.content || '',
      inputType: row.input_type || row.inputType || 'url', verdict: row.verdict || 'unknown',
      riskScore: Number(row.risk_score ?? row.riskScore ?? 0),
      analyzedAt: row.analyzed_at || row.analyzedAt || row.createdAt || new Date().toISOString(),
      indicators: Array.isArray(row.indicators) ? row.indicators : [], features: row.features || {}
    };
  }

  async function download(row, button) {
    const original = button ? button.innerHTML : '';
    if (button) { button.disabled = true; button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating…'; }
    try {
      const jsPDF = await loadJsPdf();
      const report = normalized(row);
      const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
      const navy = [15, 35, 66], cyan = [8, 145, 178], slate = [51, 65, 85], muted = [100, 116, 139], pale = [241, 245, 249];
      const verdict = verdictInfo(report.verdict);
      let y = 39;

      const header = () => {
        doc.setFillColor(...navy); doc.rect(0, 0, 210, 28, 'F');
        doc.setFillColor(...cyan); doc.rect(0, 26, 210, 2, 'F');
        doc.setTextColor(255, 255, 255); doc.setFont('helvetica', 'bold'); doc.setFontSize(15);
        doc.text('CYBERSHIELD', 14, 13);
        doc.setFont('helvetica', 'normal'); doc.setFontSize(7.5); doc.setTextColor(186, 230, 253);
        doc.text('URL & CONTENT SECURITY ANALYSIS REPORT', 14, 19);
        doc.setTextColor(226, 232, 240); doc.text(`Generated: ${new Date().toLocaleString('en-IN')}`, 196, 15, { align: 'right' });
        doc.text(`Report ID: ${clean(report.id).slice(0, 12)}`, 196, 20, { align: 'right' });
      };
      const footer = page => {
        doc.setDrawColor(226, 232, 240); doc.line(14, 281, 196, 281);
        doc.setTextColor(...muted); doc.setFont('helvetica', 'normal'); doc.setFontSize(7.5);
        doc.text('CyberShield • Explainable phishing-risk assessment', 14, 286);
        doc.text(`Page ${page}`, 196, 286, { align: 'right' });
      };
      let page = 1; header();
      const ensure = height => { if (y + height < 276) return; footer(page++); doc.addPage(); header(); y = 39; };
      const section = heading => {
        ensure(12); doc.setFillColor(...pale); doc.rect(14, y - 4, 182, 8, 'F');
        doc.setTextColor(...navy); doc.setFont('helvetica', 'bold'); doc.setFontSize(9.5); doc.text(heading, 17, y + 1); y += 11;
      };
      const field = (label, value, accent) => {
        const wrapped = doc.splitTextToSize(clean(value), 116); const height = Math.max(7, wrapped.length * 4.4 + 2); ensure(height);
        doc.setTextColor(...muted); doc.setFont('helvetica', 'normal'); doc.setFontSize(8.5); doc.text(label, 17, y);
        doc.setTextColor(...(accent || slate)); doc.setFont('helvetica', accent ? 'bold' : 'normal'); doc.text(wrapped, 72, y);
        y += height;
      };
      const paragraph = text => {
        const wrapped = doc.splitTextToSize(clean(text), 172); const height = wrapped.length * 4.6 + 8; ensure(height);
        doc.setFillColor(248, 250, 252); doc.setDrawColor(203, 213, 225); doc.rect(14, y - 4, 182, height, 'FD');
        doc.setTextColor(...slate); doc.setFont('helvetica', 'normal'); doc.setFontSize(8.8); doc.text(wrapped, 18, y + 2); y += height + 4;
      };

      section('1. ANALYSIS SUMMARY');
      field('Content type:', titleCase(report.inputType));
      field('Analyzed at:', new Date(report.analyzedAt).toLocaleString('en-IN'));
      field('Risk score:', `${Math.min(100, Math.max(0, report.riskScore))}/100`, verdict.color);
      field('Verdict:', verdict.label, verdict.color);
      section('2. SCANNED CONTENT');
      paragraph(report.content || 'No content was retained for this analysis.');
      section('3. SECURITY RECOMMENDATION');
      paragraph(verdict.note);
      section(`4. THREAT INDICATORS (${report.indicators.length})`);
      if (!report.indicators.length) paragraph('No explicit threat indicators were detected by the analyzer.');
      report.indicators.forEach((indicator, index) => {
        const text = typeof indicator === 'object' ? indicator.text || JSON.stringify(indicator) : indicator;
        field(`${index + 1}.`, text);
      });
      const features = Object.entries(report.features);
      if (features.length) {
        section('5. FEATURE BREAKDOWN');
        features.forEach(([name, value]) => field(`${titleCase(name)}:`, typeof value === 'object' ? JSON.stringify(value) : value));
      }
      footer(page);
      doc.save(`CyberShield-${clean(report.id).replace(/[^a-z0-9_-]/gi, '').slice(0, 12) || 'report'}.pdf`);
    } finally {
      if (button) { button.disabled = false; button.innerHTML = original; }
    }
  }

  window.cyberShieldReport = { download };
})();
