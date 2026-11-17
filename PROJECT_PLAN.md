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
- Updated the S3 client for path-style requests required by Supabase Storage and documented Supabase Free deployment.
- Confirmed the deployed Render health response reports PostgreSQL connected through Supabase and Gemini configured. File storage still reports unavailable and is not yet persistent.
- Last previously recorded local verification: 40 backend tests and 13 frontend workflow checks against a live API. The latest storage change has not had its backend suite rerun.
- User preference: future code changes should be pushed to GitHub when made.

## Deployment and storage decision

- The app's web service remains on Render. Its web-service filesystem is ephemeral unless a paid persistent disk is attached, so uploads must use remote object storage.
- The previous Render Free PostgreSQL database expires after 30 days. The app has now been switched to a Supabase Free PostgreSQL database; the live health check confirms `database.status=connected` and `database.backend=postgresql`.
- The user wants strictly free services for a small portfolio project and does not want Cloudflare R2 or any provider that requires paid/usage billing.
- The chosen deployment is Render for hosting, Supabase Free for PostgreSQL, and Supabase Storage Free for private file objects. The S3 adapter can connect to Supabase Storage's S3-compatible endpoint.
- Supabase Free currently includes 500 MB database size and 1 GB file storage. The existing FormPilot upload cap is 20 MB per file. Supabase may pause Free projects after seven days of low activity; a paused project can be restored, with a one-year restore window. This fits a portfolio demo, but is not archival storage or a production reliability guarantee.
- The user created a Supabase Free project, a private `formpilot-documents` bucket, enabled S3 protocol access, generated S3 credentials, and entered the Supabase database and storage settings in Render. Do not select a paid plan or request billing credentials.
- Latest health response: database connected; file storage `status=unavailable`, `backend=s3`, `persistent=false`. The user confirmed the bucket name matches. Next diagnose the endpoint, region, and S3 key pair without asking them to share secrets.
- The database connection initially failed because an `@` in the password was not URL-encoded; this was corrected and the database now connects. A fragment of the password appeared in a private Render log, so rotate the database password before making the app public. The user chose to defer rotation for the demo.
- Existing files lost from Render's ephemeral filesystem cannot be recovered; users will need to re-upload them. The new Supabase database started empty; the user will need to create a FormPilot account again.

## Next implementation steps

1. In Render, verify `S3_ENDPOINT_URL` and `S3_REGION` exactly match Supabase Storage → S3. Confirm `S3_ACCESS_KEY_ID` and `S3_SECRET_ACCESS_KEY` are the generated Supabase S3 access-key pair (not Supabase API keys); keep these values private.
2. Redeploy if any value changes and check `/api/v1/health` until file storage reports connected with `persistent=true`.
3. Create a new FormPilot account, upload a synthetic image/PDF, and verify upload, OCR attempt, retrieval, and deletion. Re-upload any files previously lost from Render's ephemeral filesystem.
4. Stay within the Supabase Free quotas and periodically open/use the project to reduce the chance of an inactivity pause. Keep personal copies of files that must not be lost.
5. Before public announcement, rotate the Supabase database password (a fragment appeared in Render logs), rotate the S3 access key pair, verify `AUTH_SECRET_KEY` is stable and at least 32 characters, and confirm HTTPS/secure cookies.
6. Push future code and documentation updates to the connected GitHub repository, as requested.

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
- Supabase Storage S3 credentials grant broad project-wide storage access and bypass Storage RLS. Keep them server-side only and rotate them if exposed.
- Supabase Free projects can pause after a week of low activity, have strict storage quotas, and are not archival storage. Keep separate copies of important files.
- FormPilot does not verify official records, determine eligibility, predict approval, or submit applications to a government or institutional portal.
