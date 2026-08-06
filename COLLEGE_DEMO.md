# CyberShield college demonstration guide

## What to demonstrate

1. Start the FastAPI backend and static dashboard.
2. Submit a known benign URL such as `https://example.com`.
3. Show the queue state, evidence sections, feature schema, model status, and
   final risk explanation.
4. Explain that browser rendering runs in an isolated Playwright process and
   CyberShield rejects localhost/private IP targets to prevent SSRF.
5. Show scan history and the stored result.

## Model disclosure

`backend/models/phishing_model.joblib` is trained from
`backend/datasets/demo_evidence.csv`, which is synthetic and generated only to
make the classifier demonstrable offline. Its perfect score is expected from a
synthetic dataset and must **not** be presented as real-world accuracy.

For your viva, say: “The platform supports a trainable evidence model. For
this prototype, I bundled a synthetic demonstration dataset. A real deployment
requires a legally sourced, labelled, time-separated phishing/benign dataset
and independent evaluation.”

## Optional live reputation demo

Copy `backend/.env.example` to `backend/.env` and add either a VirusTotal or
Google Safe Browsing API key. Provider errors or missing keys are shown as
unavailable evidence; they do not silently become a safe verdict.

## Safety

Use URLs you are authorized to test. Do not enter credentials, download files,
or otherwise interact with suspected phishing pages.
