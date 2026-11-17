# FormPilot

FormPilot is a responsive application-readiness assistant for applicants completing complex forms. It accepts application and supporting documents, extracts text, lets applicants review and save answers, runs readiness checks, and creates a draft answer-sheet PDF. It never submits an application to an official portal.

## Run locally on Windows

1. Install Python 3.11 or newer.
2. Copy `.env.example` to `.env` and set a stable `AUTH_SECRET_KEY` (at least 32 characters).
3. Open PowerShell in this folder and run `.\run.ps1`.
4. Open [http://127.0.0.1:8000](http://127.0.0.1:8000), create an account, then start an application.

The first run creates `.venv` and installs `requirements.txt`. The API and frontend are served together. Local development uses SQLite at `backend/data/auth.sqlite3`; uploaded documents are stored under `FORMPILOT_DATA_DIR` (defaults to `backend/data`).

To run manually:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

## Deploy with Docker Compose

Create a PostgreSQL database, set its connection URL as `DATABASE_URL`, set a stable random `AUTH_SECRET_KEY` (at least 32 characters), and run `docker compose up --build -d`. In production the app refuses to start without PostgreSQL. Put the service behind HTTPS and route the public domain to port 8000. The browser and API must be same-origin (or behind a same-origin reverse proxy) for the session cookie to work.

For a Render deployment, create a PostgreSQL database, then add its **internal database URL** as the web service's `DATABASE_URL` environment variable. Also set `APP_ENV=production`, `AUTH_SECRET_KEY`, and `COOKIE_SECURE=true`. Keep the database URL and signing key in the hosting provider's environment settings, never in GitHub or `.env.example`. The `/api/v1/health` response reports the active database backend and connection status.

Set `ALLOW_SIGNUP=false` after the intended accounts have been created if public account creation should close. Do not rotate `AUTH_SECRET_KEY` casually: doing so signs out all users. For deployment, set `CORS_ORIGINS` to the actual public origin if other origins are needed; avoid wildcard origins with authenticated workflows.

## Accounts and storage

Users have email/password accounts. Passwords are stored as salted PBKDF2-SHA256 hashes. The server issues an HTTP-only, SameSite=Lax cookie with a 14-day expiry. Invalid login attempts are temporarily throttled. Accounts, login attempts, and application sessions are stored in the configured SQL database (PostgreSQL in production; SQLite locally). Sessions are restored from the database after a restart. Uploaded document files remain on the service filesystem under `FORMPILOT_DATA_DIR`; production deployments need persistent file storage or object storage as well. Deleting an application removes its uploaded files and database session record.

This is a hackathon MVP, not a production document vault. It does not currently include email verification, password reset, MFA, session/device revocation, a scheduled cleanup worker, encrypted-at-rest storage, a durable background queue, or audited recovery. Signup is open by default. Use synthetic documents for demos. Do not upload real identity, bank, or certificate data to an unreviewed deployment.

## Providers and behavior

The demo works without provider credentials. It uses native PDF text extraction, deterministic validation, and a local sample scholarship schema when there is no usable form text. Add `GEMINI_API_KEY` to enable model-backed schema extraction, explanations, and OCR for scanned documents. `SARVAM_API_KEY` is optional and adds another OCR path. Provider keys remain server-side. Browser speech recognition and speech synthesis are best-effort and depend on browser support; typed answers always remain available.

Copy `.env.example` to `.env` for the available settings. Missing AI keys do not prevent manual completion. A schema or answer extracted from a document is a suggestion and must be reviewed. Readiness results do not verify documents, determine eligibility, or predict approval.

## Tests

Backend API and security tests:

```powershell
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
```

Browser workflow smoke tests run against a live server:

```powershell
python -m uvicorn backend.main:app --port 8000
# In another terminal:
cd tests/frontend
npm ci
npm test
```

## Main components

- `index.html`, `styles.css`, `app.js`: responsive sign-in and five-screen application interface.
- `backend/main.py`: FastAPI routes, uploads, extraction/provider adapters, readiness checks and PDF/JSON export.
- `backend/auth.py`: account storage, password hashing and signed cookie tokens.
- `backend/data/`: local database, persisted sessions and uploads (ignored by Git).
- `tests/`: API tests and a jsdom browser-to-API workflow smoke test.
