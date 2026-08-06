/* Handles Firebase password-reset action links (the oobCode query parameter). */
const form = document.getElementById('reset-form');
const btn = document.getElementById('submit-btn');
const btnLabel = document.getElementById('btn-label');
const alertOk = document.getElementById('alert-success');
const alertErr = document.getElementById('alert-error');
const showAlert = (el, message) => { [alertOk, alertErr].forEach(item => item.classList.remove('show')); el.textContent = message; el.classList.add('show'); };
const code = new URLSearchParams(window.location.search).get('oobCode');
if (!code) {
  showAlert(alertErr, 'This Firebase reset link is invalid or has expired. Please request a new one.');
  form.querySelectorAll('input, button').forEach(element => element.disabled = true);
}
form.addEventListener('submit', async event => {
  event.preventDefault();
  const password = document.getElementById('password').value;
  const confirm = document.getElementById('confirm').value;
  if (password.length < 8) return showAlert(alertErr, 'Password must be at least 8 characters.');
  if (password !== confirm) return showAlert(alertErr, 'Passwords do not match.');
  btn.disabled = true; btnLabel.textContent = 'Resetting…';
  try {
    const fb = await window.firebaseReady;
    await fb.confirmPasswordReset(fb.auth, code, password);
    showAlert(alertOk, 'Password updated. Redirecting to log in…');
    setTimeout(() => window.location.href = 'login.html', 1600);
  } catch (error) { showAlert(alertErr, error.message || 'Could not reset your password.'); }
  finally { btn.disabled = false; btnLabel.textContent = 'Reset password'; }
});
