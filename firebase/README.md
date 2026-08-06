# Firebase setup

1. In Firebase Console, add a **Web app** and copy its configuration into `frontend/js/firebase.js`.
2. Enable **Authentication → Sign-in method → Email/Password**.
3. Create a **Cloud Firestore** database in production mode, then publish `firestore.rules` from this folder.
4. Add `localhost` and your deployed domain under **Authentication → Settings → Authorized domains**.

## Admin setup

The Admin Panel is protected by a Firebase custom claim, not a Firestore field.
Download a Firebase Admin SDK service-account JSON file **outside this repo**,
install `backend/requirements.txt`, and run:

```powershell
python scripts/set_firebase_admin.py C:\safe\service-account.json your-admin-email@example.com
```

Sign out and sign in again after granting the claim, then publish the updated
`firestore.rules`. Do not upload the service-account JSON to GitHub or place it
in `frontend/`.

The Firebase project configuration is not a secret. Never add an Admin SDK service-account file to the frontend or Git.
