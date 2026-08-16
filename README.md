# CyberShield

CyberShield investigates submitted web URLs using live infrastructure and page
behaviour evidence. It does not derive phishing decisions from URL character
counts, brand-name lists, or fixed URL-pattern rules.

## Current pipeline

1. Normalizes and validates an HTTP/HTTPS URL.
2. Rejects localhost, private, link-local, and other non-public IP targets.
3. Collects HTTP redirects, DNS data, WHOIS/domain age, and TLS metadata.
4. Loads the page in Playwright and records the rendered DOM, forms, browser
   events, and a screenshot.
5. Extracts a stable `evidence-v1` feature payload from the collected data.
6. Returns an explainable phishing probability and the evidence contributors.

The returned classifier is `evidence-baseline-v1`. It is an explainable
development baseline, not a production-trained model. A production blocking
decision must use a versioned model trained and validated on labelled phishing
and benign data.

For the college demo, `backend/models/phishing_model.joblib` is generated from
a clearly labelled synthetic dataset. See [COLLEGE_DEMO.md](COLLEGE_DEMO.md)
for the correct way to present its limits.

CyberShield uses the explainable `evidence-baseline-v1` classifier by default.
A trained model is opt-in only: set `CYBERSHIELD_USE_TRAINED_MODEL=true` after
it has been validated on representative labelled phishing and benign data.

## Fresh zip quick start (Windows)

These are the only commands a teammate needs after downloading the project.
Use **Command Prompt** for the backend terminal because `rmdir /s /q` and
`call` are Command Prompt syntax.

### Terminal 1 — backend

```bat
cd backend
rmdir /s /q venv
py -3.12 -m venv venv
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install playwright
playwright install chromium
uvicorn app.main:app --reload
```

Leave this terminal running. Then open a second terminal at the project root
(`CyberShield`) for the frontend:

```powershell
python -m http.server 5173 --directory frontend
```

Open `http://localhost:5173/` in the browser.

If using PowerShell for Terminal 1, replace only the virtual-environment
commands with:

```powershell
if (Test-Path venv) { Remove-Item -Recurse -Force venv }
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
```

Then run the remaining backend commands unchanged.

You can also use the interactive API at `http://127.0.0.1:8000/docs`.

## QR code URL analysis

The dashboard's **QR Code** tab accepts a PNG, JPEG, or WebP image up to 5 MB.
CyberShield decodes exactly one QR code and sends its website URL through the
same URL-analysis pipeline, including the isolated Chromium screenshot. QR
values that are not valid website URLs are decoded but rejected by the URL
admission checks; support for non-web QR payloads is planned separately.

The API endpoint is `POST /analyze/qr` with multipart form field `image`.

Use the frontend terminal from the quick-start section above. To enable VirusTotal or Google Safe Browsing,
copy `backend/.env.example` to `backend/.env` and provide your own API keys.

For a containerized local deployment, run `docker compose up --build` and open
the dashboard on `http://127.0.0.1:8080`.

```json
{
  "url": "https://example.com"
}
```

The response includes raw evidence under `data`, model-ready values under
`data.features`, and the risk decision plus explanations under
`data.classification`.

## Next development milestone

Add opt-in reputation providers (Google Safe Browsing, VirusTotal, OpenPhish,
and URLhaus), store labelled feature rows, train a versioned model, and measure
precision/recall before enabling automated blocking.

## Screenshot storage

Browser captures are uploaded to Firebase Cloud Storage when the backend has
both Firebase Admin credentials and a bucket configured. Set these variables
before starting uvicorn:

```powershell
$env:FIREBASE_SERVICE_ACCOUNT = "secrets/cybershield-service-account.json"
$env:FIREBASE_STORAGE_BUCKET = "your-project.firebasestorage.app"
```

Successful uploads remove the temporary file from `backend/reports/screenshots`
and save the Storage URL/path with the analysis. If an analysis is deleted,
the associated Storage object is deleted as well. Without these variables the
local reports directory remains an intentional development fallback.

## Team Firebase setup

`backend/.env` and `backend/secrets/` are intentionally local and are not
committed. Never commit a service-account JSON file to Git. Each developer
should place their own Firebase service-account file at:

```text
backend/secrets/cybershield-service-account.json
```

The existing local configuration already points there:

```env
FIREBASE_SERVICE_ACCOUNT=secrets/cybershield-service-account.json
FIREBASE_STORAGE_BUCKET=cybershield-5494d.firebasestorage.app
```

Then start the backend from the `backend` directory:

```powershell
uvicorn app.main:app --reload
```

For deployment, configure these as encrypted environment/secrets in the host
(for example, a JSON secret value or mounted secret file). Admin operations
such as changing roles require the backend to have Firebase Admin credentials;
ordinary URL analysis and frontend Firestore use do not require teammates to
share your credential.
