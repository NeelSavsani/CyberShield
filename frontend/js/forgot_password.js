/**
 * CyberShield — forgot_password.js
 * Handles password reset request using custom email delivery API.
 */

(() => {
  const form = document.getElementById('forgot-form');
  if (!form) return;

  const emailInput = document.getElementById('email');
  const btn = document.getElementById('submit-btn');
  const btnLabel = document.getElementById('btn-label');
  const alertOk = document.getElementById('alert-success');
  const alertErr = document.getElementById('alert-error');

  function showAlert(element, message) {
    [alertOk, alertErr].filter(Boolean).forEach(alert => alert.classList.remove('show'));
    if (element) {
      element.textContent = message;
      element.classList.add('show');
    }
  }

  form.addEventListener('submit', async event => {
    event.preventDefault();
    const email = emailInput?.value.trim() || '';

    if (!email || (emailInput && !emailInput.checkValidity())) {
      showAlert(alertErr, 'Please enter a valid email address.');
      emailInput?.focus();
      return;
    }

    if (btn) btn.disabled = true;
    if (btnLabel) btnLabel.textContent = 'Sending…';

    console.log(`[CyberShield Auth] Initiating password reset request for: ${email}`);

    // 10-second timeout controller so form never hangs indefinitely
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    try {
      const resetUrl = new URL('reset_password.html', window.location.href).href;
      
      // Compute backend URL robustly across local servers (Live Server, Vite, CRA, file://, etc.)
      let backendOrigin = 'http://localhost:8000';
      if (window.location.origin && window.location.origin !== 'null' && !window.location.protocol.startsWith('file')) {
        if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1' && window.location.port !== '5500' && window.location.port !== '5173' && window.location.port !== '3000') {
          backendOrigin = window.location.origin;
        }
      }

      const response = await fetch(`${backendOrigin}/api/v1/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, continue_url: resetUrl }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        console.error('[CyberShield Auth Error] Server error response:', data);
        throw new Error(data.detail || 'Backend failed to send email');
      }

      // Write status to the console and confirm email has been sent to USER_EMAIL
      console.log(`STATUS: SUCCESS`);
      console.log(`Email has been sent to ${email}`);
      console.log(`[CyberShield Auth Details] Status: ${data.status || 'SUCCESS'}`);
      console.log(`[CyberShield Auth Details] Delivery Provider: ${data.delivery?.provider || 'custom_email_service'}`);
      
      if (data.delivery?.reset_link) {
        console.log(`%c[Custom HTML Reset Link]: %c${data.delivery.reset_link}`, 'color: #3b82f6; font-weight: bold;', 'color: #06b6d4; text-decoration: underline;');
      }

      // Show clear message on UI explicitly naming user email
      showAlert(alertOk, `STATUS: SUCCESS. Password reset email has been sent to ${email}. Please check your inbox. If you do not see the email, check your spam/junk folder. If you still do not receive the email, please contact support.`);
      form.reset();
    } catch (error) {
      clearTimeout(timeoutId);
      console.error('[CyberShield Auth Exception]:', error);

      if (error.name === 'AbortError') {
        showAlert(alertErr, 'Request timed out. Please verify backend server (http://localhost:8000) is active.');
      } else {
        showAlert(alertErr, `Could not connect to backend email service for ${email}. Please ensure backend is running at http://localhost:8000`);
      }
    } finally {
      if (btn) btn.disabled = false;
      if (btnLabel) btnLabel.textContent = 'Send reset link';
    }
  });
})();

