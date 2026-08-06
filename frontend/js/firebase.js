/*
 * Firebase client bootstrap.
 * Paste the Web app configuration from Firebase Console > Project settings
 * > Your apps into the object below. Firebase web configuration is public;
 * access is protected by Authentication and Firestore Security Rules.
 */
(function () {
  const firebaseConfig = {
    apiKey: 'AIzaSyCw-fexQs2-aFSwgLiINzjfZwpoyszWVvw',
    authDomain: 'cybershield-5494d.firebaseapp.com',
    projectId: 'cybershield-5494d',
    storageBucket: 'cybershield-5494d.firebasestorage.app',
    messagingSenderId: '915022166169',
    appId: '1:915022166169:web:8756fec8a6f2796e772008',
    measurementId: 'G-2PE8B78B2F'
  };

  window.firebaseReady = (async () => {
    const version = '12.16.0';
    const [appModule, authModule, firestoreModule, storageModule] = await Promise.all([
      import(`https://www.gstatic.com/firebasejs/${version}/firebase-app.js`),
      import(`https://www.gstatic.com/firebasejs/${version}/firebase-auth.js`),
      import(`https://www.gstatic.com/firebasejs/${version}/firebase-firestore.js`),
      import(`https://www.gstatic.com/firebasejs/${version}/firebase-storage.js`)
    ]);
    const app = appModule.initializeApp(firebaseConfig);
    return {
      auth: authModule.getAuth(app),
      db: firestoreModule.getFirestore(app),
      storage: storageModule.getStorage(app),
      ...authModule,
      ...firestoreModule,
      ...storageModule
    };
  })();
})();
