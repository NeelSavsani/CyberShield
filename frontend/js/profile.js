/* Firebase Authentication + Firestore profile page. */
const alertOk = document.getElementById('alert-success');
const alertErr = document.getElementById('alert-error');
function showAlert(el, message) { [alertOk, alertErr].forEach(item => item.classList.remove('show')); el.textContent = message; el.classList.add('show'); setTimeout(() => el.classList.remove('show'), 4000); }
let profilePhotoData = null;
let cropImage = null;
let cropScale = 1;
let cropOffsetX = 0;
let cropOffsetY = 0;
let cropDragging = false;
let cropDragStart = null;
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
    // Use the Firestore value as the source of truth, while falling back to
    // the session cache so a tab switch never makes a recently saved avatar
    // appear empty during a delayed read.
    const avatarKey = user?.uid ? `cs_avatar_${user.uid}` : '';
    profilePhotoData = data.photoDataUrl || (avatarKey ? sessionStorage.getItem(avatarKey) : null) || null;
    sessionStorage.removeItem('cs_avatar');
    if (profilePhotoData && avatarKey) sessionStorage.setItem(avatarKey, profilePhotoData);
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
  reader.onload = () => { cropImage = new Image(); cropImage.onload = openCropEditor; cropImage.src = reader.result; };
  reader.readAsDataURL(file);
});

function drawCropPreview() {
  const canvas = document.getElementById('crop-canvas'); if (!canvas || !cropImage) return;
  const context = canvas.getContext('2d'); const size = canvas.width;
  context.clearRect(0, 0, size, size); context.fillStyle = '#e8eef3'; context.fillRect(0, 0, size, size);
  const base = Math.max(size / cropImage.width, size / cropImage.height);
  const width = cropImage.width * base * cropScale; const height = cropImage.height * base * cropScale;
  context.drawImage(cropImage, (size - width) / 2 + cropOffsetX, (size - height) / 2 + cropOffsetY, width, height);
}
function openCropEditor() {
  cropScale = 1; cropOffsetX = 0; cropOffsetY = 0;
  document.getElementById('crop-zoom').value = '1'; document.getElementById('crop-modal').hidden = false; drawCropPreview();
}
function closeCropEditor() { document.getElementById('crop-modal').hidden = true; cropImage = null; document.getElementById('avatar-input').value = ''; }
document.getElementById('crop-zoom')?.addEventListener('input', event => { cropScale = Number(event.target.value); drawCropPreview(); });
document.getElementById('crop-canvas')?.addEventListener('pointerdown', event => { cropDragging = true; cropDragStart = { x:event.clientX, y:event.clientY, ox:cropOffsetX, oy:cropOffsetY }; event.currentTarget.setPointerCapture(event.pointerId); });
document.getElementById('crop-canvas')?.addEventListener('pointermove', event => {
  if (!cropDragging || !cropImage) return;
  const size = 320; const base = Math.max(size / cropImage.width, size / cropImage.height);
  const width = cropImage.width * base * cropScale; const height = cropImage.height * base * cropScale;
  const maxX = Math.max(0, (width - size) / 2); const maxY = Math.max(0, (height - size) / 2);
  cropOffsetX = Math.max(-maxX, Math.min(maxX, cropDragStart.ox + event.clientX - cropDragStart.x));
  cropOffsetY = Math.max(-maxY, Math.min(maxY, cropDragStart.oy + event.clientY - cropDragStart.y));
  drawCropPreview();
});
document.getElementById('crop-canvas')?.addEventListener('pointerup', () => { cropDragging = false; });
document.querySelectorAll('[data-close-crop]').forEach(button => button.addEventListener('click', closeCropEditor));
document.getElementById('crop-save-btn')?.addEventListener('click', () => {
  const canvas = document.getElementById('crop-canvas');
  profilePhotoData = canvas.toDataURL('image/jpeg', 0.82);
  paintAvatar(document.getElementById('profile-avatar'), profilePhotoData, 'U');
  closeCropEditor(); showAlert(alertOk, 'Photo selected. Save your profile to apply it.');
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
    const avatarKey = user?.uid ? `cs_avatar_${user.uid}` : '';
    if (avatarKey) {
      if (profilePhotoData) sessionStorage.setItem(avatarKey, profilePhotoData);
      else sessionStorage.removeItem(avatarKey);
    }
    sessionStorage.removeItem('cs_avatar');
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
