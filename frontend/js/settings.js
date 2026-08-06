/* Firestore-backed user preferences. */
const slider = document.getElementById('threshold-slider');
const sliderValue = document.getElementById('threshold-value');
const emailAlerts = document.getElementById('email-alerts');
const weeklySum = document.getElementById('weekly-summary');
const themeSel = document.getElementById('theme-select');
const formatSel = document.getElementById('report-format');
const saveBtn = document.getElementById('save-btn');
const alertOk = document.getElementById('alert-success');
const alertErr = document.getElementById('alert-error');
const saveStatus = document.getElementById('save-status');
slider.addEventListener('input', () => sliderValue.textContent = slider.value);
themeSel.addEventListener('change', () => { localStorage.setItem('cs_theme', themeSel.value); applyTheme(themeSel.value); });
function showAlert(el, message) { [alertOk, alertErr].forEach(item => item.classList.remove('show')); el.textContent = message; el.classList.add('show'); setTimeout(() => el.classList.remove('show'), 4000); }
async function loadSettings() {
  try {
    const { data } = await window.csFirebase.settings();
    slider.value = data.alertThreshold ?? 70; sliderValue.textContent = slider.value;
    emailAlerts.checked = data.emailAlerts ?? true; weeklySum.checked = data.weeklySummary ?? false;
    themeSel.value = localStorage.getItem('cs_theme') || data.theme || 'light'; formatSel.value = data.defaultReportFormat || 'pdf';
  } catch { showAlert(alertErr, 'Could not load Firebase settings.'); }
}
saveBtn.addEventListener('click', async () => {
  saveBtn.disabled = true; saveBtn.textContent = 'Saving…';
  try {
    const { fb, user } = await window.csFirebase.currentUser();
    await fb.setDoc(fb.doc(fb.db, 'users', user.uid, 'settings', 'preferences'), {
      alertThreshold: Number(slider.value), emailAlerts: emailAlerts.checked, weeklySummary: weeklySum.checked,
      theme: themeSel.value, defaultReportFormat: formatSel.value, updatedAt: new Date().toISOString()
    }, { merge: true });
    showAlert(alertOk, 'Settings saved.'); saveStatus.classList.add('show'); setTimeout(() => saveStatus.classList.remove('show'), 2000);
  } catch (error) { showAlert(alertErr, error.message || 'Could not save settings.'); }
  finally { saveBtn.disabled = false; saveBtn.textContent = 'Save settings'; }
});
loadSettings();
