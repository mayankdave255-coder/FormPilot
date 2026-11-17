# FormPilot: Work Log and Plan

Last updated: 2026-11-18

This file tracks what is implemented, decisions made, and the next steps. `TASKS.md` remains the concise deployment checklist.

## Product direction

FormPilot is an authenticated assistant for filling forms. A user uploads a form, FormPilot identifies fields and suggests values from documents the user has already uploaded, the user reviews and corrects answers, then FormPilot can run a readiness check and create a draft PDF/JSON. It does not submit forms to official portals. It should work with varied forms, rather than only scholarship applications, and should ask the user when no reliable answer source exists.

## Completed work

- Built the five-screen web UI (`index.html`, `styles.css`, `app.js`) served by FastAPI.
- Added email/password accounts, PBKDF2-SHA256 password hashing, HTTP-only session cookies, and account-owned sessions.
- Added SQLite for local development and PostgreSQL support for production; sessions survive restarts and deleting an application removes its related records/files.
- Added PDF/image uploads, local extraction, Gemini OCR when configured, reviewable answers, readiness checks, and draft PDF/JSON export.
- Added an account document gallery, OCR text indexing, and attaching gallery documents to applications.
- Removed Sarvam from the provider plan; Gemini is the only planned OCR provider.
- Added Docker Compose settings and GitHub Actions backend/browser workflow.
- Added a private S3-compatible object storage adapter for uploads and generated drafts. In production, file operations require object storage configuration rather than falling back to Render's ephemeral filesystem.
- Confirmed the deployed Render health response reported PostgreSQL connected, Gemini configured, native PDF text and scanned OCR capabilities, and live mode.
- Last previously recorded local verification: 40 backend tests and 13 frontend workflow checks against a live API. The latest storage change has not had its backend suite rerun.
- User preference: future code changes should be pushed to GitHub when made.

## Deployment and storage decision

- The app is deployed on Render and uses Render PostgreSQL for structured data.
- Render's web service filesystem is ephemeral unless a paid persistent disk is attached. R2 was selected as the first persistent file-storage approach and its integration is already in the repository.
- The user does not want to activate Cloudflare R2 because the setup presents a billing subscription and possible overage charges.
- Recommended next alternative: store uploaded file bytes in the existing Render PostgreSQL database (for example, a `BYTEA` column) so files survive web-service restarts without a separate object-storage subscription. This is appropriate for a small MVP, but makes the database grow with files and should be revisited if usage grows. Confirm the Render database's available storage/quota before moving production uploads.
- This PostgreSQL file-storage change is a proposal only; it has not been implemented. Do not ask the user to enable R2 unless they later choose it.
- Existing files lost from Render's ephemeral filesystem cannot be recovered; users will need to re-upload them after durable storage is deployed.

## Next implementation steps

1. Replace the production S3 requirement with a PostgreSQL-backed file store using the existing database connection; preserve the local development adapter if useful.
2. Keep object metadata, ownership checks, and deletion behavior aligned with existing gallery/application access controls.
3. Update `.env.example`, README, health reporting, and deployment notes so Render no longer needs R2 credentials for file persistence.
4. Check Render PostgreSQL storage limits and costs against expected uploads; set upload size/retention limits appropriate to the database capacity.
5. Push the code and documentation updates to the connected GitHub repository, as requested.
6. After deployment, verify health and persistence across a Render restart, then re-upload any files previously lost.

## Product and production follow-ups

- Make the dashboard show document-analysis/guidance features in a state appropriate to whether the user has uploaded a form or documents.
- Improve generic form-field extraction and map each field to existing OCR evidence; ask the user for missing or uncertain values instead of inferring an application type.
- Improve Gemini OCR error handling and clearly report when a key is missing or a provider call fails.
- Review privacy, retention, deletion, and access controls before public use. Current session/application data has a 12-hour retention policy; gallery retention needs an explicit product policy.
- Add email verification, password reset, MFA, session revocation, encryption-at-rest review, scheduled cleanup, background jobs, and safer database migrations.
- Test camera, microphone, and layouts on real Android/iOS devices and supported browsers.
- Before public deployment, use stable `AUTH_SECRET_KEY` (at least 32 characters), `APP_ENV=production`, secure cookies, HTTPS, PostgreSQL, and durable file storage.

## Known limitations and risks

- Gemini was configured on the deployed service, but one previous local Gemini call returned an HTTP error and fell back to manual entry. Sarvam has not been verified and is out of scope.
- OCR output can be wrong; users must review extracted values. Stronger confidence/evidence review is not yet built.
- PostgreSQL-backed binary storage is simpler for this MVP, but large files or high upload volume can increase database storage and backup costs. Keep strict per-file and per-account limits and revisit object storage if usage grows.
- FormPilot does not verify official records, determine eligibility, predict approval, or submit applications to a government or institutional portal.
