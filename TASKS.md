# FormPilot status and remaining work

Status: the authenticated hackathon MVP and account document library are implemented. Before these changes, 40 backend tests and 13 frontend workflow checks passed against the running API; those checks have not been rerun for this update.

## Implemented

- Account creation, sign-in, sign-out and account-owned API access.
- Persistent local account and application-session storage with upload deletion.
- Persistent account document gallery with OCR text indexing and cross-application document attachment.
- PDF/image upload, extraction fallbacks, reviewable answers, readiness checks and draft export.
- Responsive login and application UI; new accounts start without fictional applicant answers.
- Docker Compose deployment settings and a GitHub Actions backend test workflow.

## Before a public deployment

1. Set a stable `AUTH_SECRET_KEY` of at least 32 characters, `APP_ENV=production`, and secure cookies. Use HTTPS and persistent storage for `FORMPILOT_DATA_DIR`.
2. Check the configured Gemini API credentials/model. A request returned an HTTP error during the last local exercise; the local fallback allowed manual completion. Gemini is the sole AI provider.
3. Test the camera, microphone and responsive screens on real Android/iOS devices and supported browsers. Desktop visual inspection was unavailable in this environment.
4. Use synthetic documents until privacy and retention controls are reviewed.

## Remaining product work

- Email verification, password reset, MFA and user-controlled session/device revocation.
- Encryption at rest, scheduled TTL cleanup, durable background jobs and database migration tooling.
- Broader multilingual field-schema correction, fuzzy field-to-document matching and source-linked evidence review for uncertain OCR results.
- Validate scan quality, voice transcripts and provider failure recovery across real documents and devices.

FormPilot does not verify official records, decide eligibility, predict approval or submit applications to government or institutional portals.
