/**
 * CyberShield — forgot_password.js
 * Handles the forgot-password request form.
 */

const form       = document.getElementById('forgot-form');
const btn        = document.getElementById('submit-btn');
const btnLabel   = document.getElementById('btn-label');
const alertOk    = document.getElementById('alert-success');
const alertErr   = document.getElementById('alert-error');

function showAlert(el, message) {
  [alertOk, alertErr].forEach(a => a.classList.remove('show'));
  el.innerHTML = message;
  el.classList.add('show');
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const email = document.getElementById('email').value.trim();
  if (!email) {
    showAlert(alertErr, 'Please enter your email address.');
    return;
  }

  btn.disabled = true;
  btnLabel.textContent = 'Sending…';

  try {
    const fb = await window.firebaseReady;
    await fb.sendPasswordResetEmail(fb.auth, email, {
      url: new URL('login.html', window.location.href).href,
      handleCodeInApp: false
    });
    showAlert(alertOk, 'If this address has a CyberShield account, Firebase has sent a password-reset email.');
    form.reset();
  } catch (err) {
    showAlert(alertErr, 'Could not reach the server. Is the project running?');
  } finally {
    btn.disabled = false;
    btnLabel.textContent = 'Send reset link';
  }
});
