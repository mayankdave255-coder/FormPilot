# FormPilot

FormPilot is a responsive application-readiness assistant for applicants completing complex forms. This hackathon MVP connects a browser UI to a FastAPI service. It accepts application and support documents, extracts document text, keeps answer provenance, runs deterministic checks, and creates a draft answer-sheet PDF.

The demo works without provider credentials. Voice input and playback are free by default: they use the browser's built-in Web Speech API (`SpeechRecognition` / `speechSynthesis`), so no voice provider key is needed. Add `GEMINI_API_KEY` to enable model-backed form-schema extraction, explanations, and OCR for scanned documents (Gemini has a free tier, suitable for demo-level usage). `SARVAM_API_KEY` is optional and only adds a paid, higher-quality OCR path for scanned documents through Sarvam's Parse API — everything else in the app works without it. Provider calls run on the server. The browser never receives provider keys.

## Run locally on Windows

1. Install Python 3.11 or newer.
2. Open PowerShell in this folder and run `.\run.ps1`.
3. Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

The first run creates `.venv` and installs the packages in `requirements.txt`. To stop the server, press Ctrl+C.

To run the same app in Docker, use `docker compose up --build` from this folder. The API and frontend are served together on port 8000. Uploaded files are stored in the mounted `backend/data` folder.

You can also install manually:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

## Provider setup

Copy `.env.example` to `.env`, then add the keys you have:

- `GEMINI_API_KEY` enables model-backed form schema extraction, explanations, and OCR for scanned documents. `GEMINI_MODEL` selects the model. Google's Gemini API has a free tier, which is the recommended path if you don't want to pay for anything.
- `SARVAM_API_KEY` is **optional** and not required for voice at all — recorded voice answers are transcribed, and responses spoken, entirely in the browser via the Web Speech API, for free, with no key. Setting `SARVAM_API_KEY` only adds a secondary, paid OCR path for scanned documents (Sarvam's Parse API); without it, scanned-document OCR falls back to Gemini (if `GEMINI_API_KEY` is set) or local text extraction.

Leave missing keys blank. FormPilot then uses the local scholarship demo schema, bilingual explanations, typed answers and deterministic validation. The UI labels provider failures and keeps manual entry available. Voice input requires a browser with `SpeechRecognition` support (Chrome and most Chromium-based browsers); on unsupported browsers the mic button shows a message and you can type the answer instead.

The first FormPilot sample is fictional. It demonstrates Rahul Kumar's scholarship application, a name comparison against a marksheet, and a missing income certificate. Do not upload real government IDs, account numbers or certificates to a hackathon demo.

## Data and retention

The MVP keeps sessions in server memory and uploaded files in `backend/data/<session-id>`. A session is removed after 12 hours of inactivity when the next session is created, or immediately when the deletion API is called. Restarting the server clears session records; remove `backend/data` to clear leftover files. This is temporary demo storage, not a document vault.

Files are limited to 20 MB and PDFs to 30 pages by default. Set `MAX_FILE_MB`, `MAX_PDF_PAGES`, `SESSION_TTL_HOURS`, `FORMPILOT_DATA_DIR`, and optionally `PDF_UNICODE_FONT` in `.env` to change those local limits. Production use needs persistent session storage, background-job infrastructure, access control, encryption, a scheduled cleanup worker and an appropriate privacy review.

## API

Interactive API documentation is at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Routes are versioned under `/api/v1`.

The MVP includes session management, file upload and deletion, background PDF/OCR processing, page extraction, form schema and field correction, localized explanations, answer save/confirmation, evidence matching, voice transcription and speech synthesis adapters, rule-based readiness checks, issue resolution, answer export and draft PDF generation.

Readiness checks report missing values, configured format issues and candidate cross-document mismatches. They do not verify documents against official sources, predict approval, or submit an application. Extracted values remain suggestions until the applicant confirms them.

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The browser tests start from a running server (`python -m uvicorn backend.main:app --port 8000`), then run `npm install` and `npm test` inside `tests/frontend`.

## Project files

- `index.html`, `styles.css`, `app.js`: responsive five-screen frontend.
- `backend/main.py`: FastAPI routes, temporary session store, extraction/provider adapters, validation and PDF export.
- `requirements.txt`: Python dependencies.
- `tests/`: API tests (pytest) and a jsdom end-to-end test of the frontend.
- `TASKS.md`: open work before the demo.
- `.env.example`: local configuration template.
