/* Firebase Authentication + Firestore profile page. */
const alertOk = document.getElementById('alert-success');
const alertErr = document.getElementById('alert-error');
function showAlert(el, message) { [alertOk, alertErr].forEach(item => item.classList.remove('show')); el.textContent = message; el.classList.add('show'); setTimeout(() => el.classList.remove('show'), 4000); }

async function loadProfile() {
  try {
    const { user, data } = await window.csFirebase.profile();
    const firstName = data.firstName || (user.displayName || '').split(' ')[0] || '';
    const lastName = data.lastName || (user.displayName || '').split(' ').slice(1).join(' ') || '';
    document.getElementById('profile-name').textContent = `${firstName} ${lastName}`.trim() || user.email;
    document.getElementById('profile-email').textContent = user.email;
    document.getElementById('profile-role').textContent = 'User';
    document.getElementById('profile-avatar').textContent = (firstName || user.email)[0].toUpperCase();
    document.getElementById('first_name').value = firstName;
    document.getElementById('last_name').value = lastName;
    document.getElementById('email_ro').value = user.email;
  } catch { showAlert(alertErr, 'Could not load your Firebase profile.'); }
}

document.getElementById('profile-form').addEventListener('submit', async event => {
  event.preventDefault();
  try {
    const { fb, user } = await window.csFirebase.currentUser();
    const firstName = document.getElementById('first_name').value.trim();
    const lastName = document.getElementById('last_name').value.trim();
    const displayName = `${firstName} ${lastName}`.trim();
    await fb.updateProfile(user, { displayName });
    await fb.setDoc(fb.doc(fb.db, 'users', user.uid), { firstName, lastName, displayName, email: user.email }, { merge: true });
    sessionStorage.setItem('cs_user', JSON.stringify({ id: user.uid, name: displayName, email: user.email }));
    document.getElementById('profile-name').textContent = displayName;
    document.getElementById('user-name').textContent = displayName;
    showAlert(alertOk, 'Profile updated successfully.');
  } catch (error) { showAlert(alertErr, error.message || 'Could not update profile.'); }
});

document.getElementById('password-form').addEventListener('submit', async event => {
  event.preventDefault();
  const newPassword = document.getElementById('new_password').value;
  if (newPassword.length < 8) return showAlert(alertErr, 'New password must be at least 8 characters.');
  try {
    const { fb, user } = await window.csFirebase.currentUser();
    await fb.updatePassword(user, newPassword);
    event.target.reset();
    showAlert(alertOk, 'Password updated successfully.');
  } catch (error) {
    showAlert(alertErr, error.code === 'auth/requires-recent-login' ? 'Please sign out and sign in again before changing your password.' : error.message);
  }
});
loadProfile();
