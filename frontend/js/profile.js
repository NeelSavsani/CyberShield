/* Firebase Authentication + Firestore profile page. */
const alertOk = document.getElementById('alert-success');
const alertErr = document.getElementById('alert-error');
function showAlert(el, message) { [alertOk, alertErr].forEach(item => item.classList.remove('show')); el.textContent = message; el.classList.add('show'); setTimeout(() => el.classList.remove('show'), 4000); }
let profilePhotoData = null;
function paintAvatar(element, photo, fallback) {
  if (!element) return;
  element.replaceChildren();
  if (photo) {
    const image = document.createElement('img');
    image.src = photo;
    image.alt = 'Profile photo';
    element.appendChild(image);
  } else element.textContent = fallback;
}

async function loadProfile() {
  try {
    const { user, data } = await window.csFirebase.profile();
    const firstName = data.firstName || (user.displayName || '').split(' ')[0] || '';
    const lastName = data.lastName || (user.displayName || '').split(' ').slice(1).join(' ') || '';
    document.getElementById('profile-name').textContent = `${firstName} ${lastName}`.trim() || user.email;
    document.getElementById('profile-email').textContent = user.email;
    document.getElementById('profile-role').textContent = 'User';
    profilePhotoData = data.photoDataUrl || null;
    paintAvatar(document.getElementById('profile-avatar'), profilePhotoData, (firstName || user.email)[0].toUpperCase());
    document.getElementById('first_name').value = firstName;
    document.getElementById('last_name').value = lastName;
    document.getElementById('email_ro').value = user.email;
  } catch { showAlert(alertErr, 'Could not load your Firebase profile.'); }
}

document.getElementById('avatar-input')?.addEventListener('change', event => {
  const file = event.target.files?.[0];
  if (!file) return;
  if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 2 * 1024 * 1024) {
    event.target.value = '';
    return showAlert(alertErr, 'Choose a PNG, JPG, or WebP image smaller than 2 MB.');
  }
  const reader = new FileReader();
  reader.onload = () => {
    const image = new Image();
    image.onload = () => {
      const size = 256;
      const canvas = document.createElement('canvas'); canvas.width = size; canvas.height = size;
      const context = canvas.getContext('2d');
      const scale = Math.max(size / image.width, size / image.height);
      const width = image.width * scale; const height = image.height * scale;
      context.drawImage(image, (size - width) / 2, (size - height) / 2, width, height);
      profilePhotoData = canvas.toDataURL('image/jpeg', 0.82);
      paintAvatar(document.getElementById('profile-avatar'), profilePhotoData, 'U');
      showAlert(alertOk, 'Photo selected. Save your profile to apply it.');
    };
    image.src = reader.result;
  };
  reader.readAsDataURL(file);
});

document.getElementById('remove-avatar-btn')?.addEventListener('click', () => {
  profilePhotoData = null;
  const name = document.getElementById('first_name')?.value.trim() || document.getElementById('email_ro')?.value || 'U';
  paintAvatar(document.getElementById('profile-avatar'), null, name[0].toUpperCase());
  document.getElementById('avatar-input').value = '';
  showAlert(alertOk, 'Photo removed. Save your profile to apply it.');
});

document.getElementById('profile-form').addEventListener('submit', async event => {
  event.preventDefault();
  try {
    const { fb, user } = await window.csFirebase.currentUser();
    const firstName = document.getElementById('first_name').value.trim();
    const lastName = document.getElementById('last_name').value.trim();
    const displayName = `${firstName} ${lastName}`.trim();
    await fb.updateProfile(user, { displayName });
    await fb.setDoc(fb.doc(fb.db, 'users', user.uid), { firstName, lastName, displayName, email: user.email, photoDataUrl: profilePhotoData }, { merge: true });
    sessionStorage.setItem('cs_user', JSON.stringify({ id: user.uid, name: displayName, email: user.email }));
    document.getElementById('profile-name').textContent = displayName;
    document.getElementById('user-name').textContent = displayName;
    sessionStorage.setItem('cs_avatar', profilePhotoData || '');
    paintAvatar(document.getElementById('user-avatar'), profilePhotoData, (displayName || user.email)[0].toUpperCase());
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
