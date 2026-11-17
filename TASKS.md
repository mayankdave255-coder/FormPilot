# FormPilot status and remaining work

Status: the authenticated hackathon MVP and account document library are implemented. Production is hosted on Render, with Supabase Free selected for PostgreSQL and private file storage. Latest health check: PostgreSQL connected; S3 file storage unavailable. Previously recorded local verification was 40 backend tests and 13 frontend workflow checks; those checks have not been rerun for the latest storage changes.

## Implemented

- Account creation, sign-in, sign-out and account-owned API access.
- Persistent local account and application-session storage with upload deletion.
- Persistent account document gallery with OCR text indexing and cross-application document attachment.
- S3-compatible private object storage adapter for source uploads and generated drafts; local filesystem adapter remains for development. Supabase Storage path-style client support is configured.
- PDF/image upload, extraction fallbacks, reviewable answers, readiness checks and draft export.
- Responsive login and application UI; new accounts start without fictional applicant answers.
- Docker Compose deployment settings and a GitHub Actions backend test workflow.

## Before a public deployment

1. Fix Supabase Storage connectivity: verify Render `S3_ENDPOINT_URL`, `S3_REGION`, and the S3 access-key pair against Supabase Storage → S3; never share these secrets.
2. Verify `/api/v1/health` reports PostgreSQL and file storage connected, then test upload/retrieval/deletion with synthetic documents.
3. Stay on Supabase Free quotas; Free projects may pause after a week of low activity. Do not enable paid billing.
4. Before public announcement, rotate the Supabase database password because a fragment appeared in Render logs, rotate S3 keys, and confirm a stable `AUTH_SECRET_KEY` of at least 32 characters, `APP_ENV=production`, secure cookies, and HTTPS.
5. Check Gemini OCR error recovery and test camera, microphone, and responsive screens on real Android/iOS devices.

## Remaining product work

- Email verification, password reset, MFA and user-controlled session/device revocation.
- Encryption at rest, scheduled TTL cleanup, durable background jobs and database migration tooling.
- Broader multilingual field-schema correction, fuzzy field-to-document matching and source-linked evidence review for uncertain OCR results.
- Validate scan quality, voice transcripts and provider failure recovery across real documents and devices.

FormPilot does not verify official records, decide eligibility, predict approval or submit applications to government or institutional portals.
