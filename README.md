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

## Run locally first time

```powershell
cd backend
rmdir /s /q venv
py -3.12 -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install playwright
playwright install chromium
uvicorn app.main:app --reload
```

## Run locally after first time
```powershell
cd backend
.\venv\Scripts\activate 
uvicorn app.main:app --reload
```

In another terminal
```powershell
python -m http.server 5173 --directory frontend
```

Open browser and go to `http://localhost:5173/`


Then submit a URL to `POST /analyze` or use the interactive API at
`http://127.0.0.1:8000/docs`.

## QR code URL analysis

The dashboard's **QR Code** tab accepts a PNG, JPEG, or WebP image up to 5 MB.
CyberShield decodes exactly one QR code and sends its website URL through the
same URL-analysis pipeline, including the isolated Chromium screenshot. QR
values that are not valid website URLs are decoded but rejected by the URL
admission checks; support for non-web QR payloads is planned separately.

The API endpoint is `POST /analyze/qr` with multipart form field `image`.

In a second terminal, serve the multi-page dashboard:

```powershell
python -m http.server 5173 --directory frontend
```

Open `http://127.0.0.1:5173`. To enable VirusTotal or Google Safe Browsing,
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
