/* Branded Firebase password-reset action page. The password is changed in
   Firebase Auth by confirmPasswordReset; no password is stored locally. */
const form = document.getElementById('reset-form');
const btn = document.getElementById('submit-btn');
const btnLabel = document.getElementById('btn-label');
const alertOk = document.getElementById('alert-success');
const alertErr = document.getElementById('alert-error');
const code = new URLSearchParams(window.location.search).get('oobCode');
const controls = form.querySelectorAll('input, button[type="submit"]');
const showAlert = (el, message) => {
  [alertOk, alertErr].forEach(item => item.classList.remove('show'));
  el.textContent = message;
  el.classList.add('show');
};
const friendlyError = (error) => {
  const codeName = error?.code || '';
  if (codeName.includes('expired-action-code') || codeName.includes('invalid-action-code')) {
    return 'This reset link is invalid or has expired. Please request a new one.';
  }
  if (codeName.includes('user-disabled')) return 'This account is disabled. Please contact an administrator.';
  if (codeName.includes('weak-password')) return 'Choose a stronger password with at least 8 characters.';
  if (codeName.includes('network-request-failed')) return 'Network error. Check your connection and try again.';
  return 'We could not complete the reset. Please request a new link and try again.';
};
const setEnabled = (enabled) => controls.forEach(element => { element.disabled = !enabled; });
setEnabled(false);

const initialise = async () => {
  if (!code) return showAlert(alertErr, 'This reset link is invalid or has expired. Please request a new one.');
  try {
    const fb = await window.firebaseReady;
    await fb.verifyPasswordResetCode(fb.auth, code);
    setEnabled(true);
    showAlert(alertOk, 'Reset link verified. Choose a new password below.');
  } catch (error) {
    showAlert(alertErr, friendlyError(error));
  }
};

const password = document.getElementById('password');
const confirm = document.getElementById('confirm');
const meter = document.getElementById('password-meter-bar');
const strength = document.getElementById('password-strength');
const rules = {
  length: document.getElementById('rule-length'),
  case: document.getElementById('rule-case'),
  number: document.getElementById('rule-number')
};
const updateStrength = () => {
  if (!password || !meter) return;
  const value = password.value;
  const checks = [value.length >= 8, /[a-z]/.test(value) && /[A-Z]/.test(value), /\d/.test(value)];
  Object.entries(rules).forEach(([key, element], index) => element?.classList.toggle('is-valid', checks[index]));
  const score = checks.filter(Boolean).length;
  meter.style.width = `${score * 33.333}%`;
  meter.dataset.score = String(score);
  if (strength) strength.textContent = score === 0 ? 'Enter a password' : score === 3 ? 'Strong password' : 'Could be stronger';
};
password?.addEventListener('input', updateStrength);
document.querySelectorAll('.password-toggle').forEach(toggle => toggle.addEventListener('click', () => {
  const target = document.getElementById(toggle.dataset.target);
  if (!target) return;
  target.type = target.type === 'password' ? 'text' : 'password';
  toggle.setAttribute('aria-label', target.type === 'password' ? 'Show password' : 'Hide password');
}));

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (!code) return;
  if (password.value.length < 8) return showAlert(alertErr, 'Password must be at least 8 characters.');
  if (password.value !== confirm.value) return showAlert(alertErr, 'Passwords do not match.');
  btn.disabled = true; btnLabel.textContent = 'Updating securely…';
  try {
    const fb = await window.firebaseReady;
    await fb.confirmPasswordReset(fb.auth, code, password.value);
    showAlert(alertOk, 'Password updated securely. Redirecting to log in…');
    setTimeout(() => { window.location.href = 'login.html?reset=success'; }, 1600);
  } catch (error) {
    showAlert(alertErr, friendlyError(error));
  } finally {
    btn.disabled = false; btnLabel.textContent = 'Reset password';
  }
});

initialise();
