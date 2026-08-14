/* Shared Firebase data access for CyberShield. No PHP sessions or MySQL IDs. */
(function () {
  const userDoc = (fb, uid) => fb.doc(fb.db, 'users', uid);
  const analyses = (fb, uid) => fb.collection(fb.db, 'users', uid, 'analyses');

  async function currentUser(requireUser = true) {
    const fb = await window.firebaseReady;
    await new Promise(resolve => fb.onAuthStateChanged(fb.auth, resolve));
    if (!fb.auth.currentUser && requireUser) window.location.href = 'login.html';
    return { fb, user: fb.auth.currentUser };
  }

  async function profile() {
    const { fb, user } = await currentUser();
    const snapshot = await fb.getDoc(userDoc(fb, user.uid));
    return { fb, user, data: snapshot.exists() ? snapshot.data() : {} };
  }

  window.csFirebase = {
    currentUser,
    profile,
    async saveAnalysis(result, content) {
      const { fb, user } = await currentUser();
      const ref = await fb.addDoc(analyses(fb, user.uid), {
        inputType: result.input_type,
        content,
        riskScore: result.risk_score,
        verdict: result.verdict,
        indicators: result.indicators || [],
        features: result.features || {},
        screenshotUrl: result.screenshot_url || null,
        screenshotStoragePath: result.screenshot_storage_path || null,
        analyzedAt: result.analyzed_at || new Date().toISOString(),
        createdAt: new Date().toISOString()
      });
      return ref.id;
    },
    async listAnalyses() {
      const { fb, user } = await currentUser();
      const snapshot = await fb.getDocs(fb.query(analyses(fb, user.uid), fb.orderBy('createdAt', 'desc')));
      return snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
    },
    async deleteAnalysis(id) {
      const { fb, user } = await currentUser();
      const ref = fb.doc(fb.db, 'users', user.uid, 'analyses', id);
      const snapshot = await fb.getDoc(ref);
      const data = snapshot.exists() ? snapshot.data() : {};
      if (data.screenshotStoragePath) {
        try { await fb.deleteObject(fb.ref(fb.storage, data.screenshotStoragePath)); }
        catch (error) { console.warn('Screenshot cleanup failed:', error); }
      }
      await fb.deleteDoc(ref);
    },
    async settings() {
      const { fb, user } = await currentUser();
      const ref = fb.doc(fb.db, 'users', user.uid, 'settings', 'preferences');
      const snapshot = await fb.getDoc(ref);
      return { ref, data: snapshot.exists() ? snapshot.data() : {} };
    }
  };
})();
