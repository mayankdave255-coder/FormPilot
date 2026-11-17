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

- The app is deployed on Render and uses Render PostgreSQL for structured data. The Render dashboard screenshot (2026-11-18) shows the current database on the Free compute plan; Render warns that free databases expire after 30 days and are intended for testing/prototyping.
- Render's web service filesystem is ephemeral unless a paid persistent disk is attached. R2 was selected as the first persistent file-storage approach and its integration is already in the repository.
- The user wants strictly free services for a small portfolio project and does not want Cloudflare R2 or any provider that requires paid/usage billing.
- Recommended deployment: keep the Render web service, move PostgreSQL from the expiring Render Free database to Supabase Free, and use Supabase Storage Free for private file objects. The existing S3 adapter can connect to Supabase Storage's S3-compatible endpoint.
- Supabase Free currently includes 500 MB database size and 1 GB file storage. The existing FormPilot upload cap is 20 MB per file. Supabase may pause Free projects after seven days of low activity; a paused project can be restored, with a one-year restore window. This fits a portfolio demo, but is not archival storage or a production reliability guarantee.
- This Supabase setup is not yet configured in the user's accounts. The user must create the Free project, private bucket and server-side S3 credentials, then set Render environment variables. Do not select a paid plan or request billing credentials.
- Existing files lost from Render's ephemeral filesystem cannot be recovered; users will need to re-upload them after durable storage is deployed.

## Next implementation steps

1. Create the Supabase Free project and private Storage bucket. Back up the current Render PostgreSQL data, then migrate it if the existing account should be preserved; the new Supabase database starts empty. Existing files lost from Render's ephemeral filesystem must be re-uploaded.
2. Move the app database to Supabase PostgreSQL and retain account ownership checks for all files. The server-side Supabase S3 credentials bypass Supabase Storage RLS, so never expose them to the browser.
3. Deploy, verify health and file persistence, then re-upload any files previously lost from Render's ephemeral filesystem.
4. Stay within the Supabase Free quotas and periodically open/use the project to reduce the chance of an inactivity pause. Keep personal copies of files that must not be lost.
5. Push the code and documentation updates to the connected GitHub repository, as requested.

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
