# Backend

FastAPI handles accounts, authorised MP4 uploads, analysis jobs and protected playback. A separate worker sends videos to the configured Gemini model and saves timestamped candidate events. SQLite holds account, session and analysis records.

## Local setup

Requires Python 3.11+ and FFmpeg/FFprobe on PATH.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

For local HTTP development, set `TSI_COOKIE_SECURE=false`, `TSI_REGISTRATION_ENABLED=true` and `TSI_APP_ORIGIN=http://127.0.0.1:8000`. Secure cookies are enabled and registration is disabled by default. Use HTTPS and secure cookies outside local development.

Load the environment and start the API:

```sh
set -a
. ./.env
set +a
uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Account creation, login and playback do not require a Gemini key. New analyses require a server-side key, a supported model and `TSI_PROVIDER_TERMS_ACCEPTED=true`. Review the provider's current quotas, billing and footage-handling terms before enabling it. This setting records approval; it cannot detect whether the provider project has paid billing enabled. There is no automatic provider or model fallback.

In another terminal, load the same environment and run:

```sh
python -m api.worker
```

Never commit the populated `.env` file.

## Accounts and sessions

Register with `POST /v1/auth/register` using JSON `username` and `password`. Usernames contain 3–40 lowercase letters, digits or underscores. Passwords contain 12–128 characters and are stored as Argon2id hashes.

Registration and `POST /v1/auth/login` return user ID, username and a CSRF token. The session cookie is HttpOnly, SameSite=Strict and Secure by default. Session tokens are random and stored only as hashes; sessions expire after 24 hours. `GET /v1/auth/me` returns the current user and CSRF token. `POST /v1/auth/logout` revokes the current session.

Send the cookie on authenticated requests. Send `X-TSI-CSRF` on all authenticated write requests, including uploads and logout. Browser origins must match `TSI_APP_ORIGIN`; use the same origin for frontend and API. No cross-origin access is enabled. CLI clients can omit Origin but still need the cookie and CSRF token.

Login and registration each allow ten attempts per IP and username within ten minutes. Limits are stored in SQLite. Development limits are 100 accounts, five analyses per account and twenty analyses across the instance.

The previous shared bearer token is no longer accepted. Existing analyses without an owner remain unassigned and inaccessible through account routes; they are never automatically given to a newly registered user.

This is development authentication, not a complete public-account service. Password recovery, email verification, account deletion, MFA and broader abuse protection still need implementation before a public launch.

## Submit footage

Create an analysis with `POST /v1/analyses`:

```json
{
  "title": "Match highlights",
  "authorised": true,
  "provider_processing_consent": true
}
```

Optional fields are `home_team`, `away_team`, `competition` and `match_date`. Metadata is user-supplied, not independently verified.

Upload the file to the returned `upload_path` using PUT, `Content-Type: video/mp4`, the session cookie and CSRF header. Send the MP4 as a raw body, not multipart. The development limits are 100 MiB, ten minutes and 3840x2160. FFprobe checks the container, video stream and duration.

Unsupported URLs are not downloaded. Jobs progress through `awaiting_upload`, `uploading`, `queued`, `processing`, then `completed` or `failed`. Queued jobs need a running worker. The API reports source, quota and validation failures without fabricated results.

## Analysis and playback routes

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Process health |
| GET | `/v1/capabilities` | Source support and limits |
| POST | `/v1/analyses` | Create an owned analysis |
| PUT | `/v1/analyses/{id}/video` | Upload footage |
| GET | `/v1/analyses` | List the current user's analyses |
| GET | `/v1/analyses/{id}` | Job status and structured results |
| GET | `/v1/analyses/{id}/report` | Plain-text evidence report |
| GET, HEAD | `/v1/analyses/{id}/video` | Protected video playback |

All analysis routes require a valid account session. Requests for another user's analysis return 404, including upload, report and video routes. Playback serves only accepted uploads and supports byte ranges for seeking. Responses use private, no-store caching. A same-origin HTML video element can use the playback URL without putting credentials in its query string.

Results separate candidate observations from model interpretations and link claims to event IDs. Timestamps use seconds in the uploaded video, not the match clock. Evidence references retain upload ID and SHA-256. Player/team identities remain unset. Confidence is a model estimate; schema checks do not verify that a claim is true.

## Retention and deployment limits

The running worker removes inactive analyses and their footage seven days after creation. Cleanup does not run while the worker is stopped. Interrupted uploads/jobs are marked failed after thirty minutes and are not automatically resubmitted. Provider file deletion is best-effort; remote retention still follows the provider's policy.

This backend remains for local development. Before hosting, add upload deadlines, broader rate limits, worker leases/heartbeats, isolated video validation, account lifecycle handling and production persistence. Keep FFmpeg patched. Do not expose local file storage directly.

## Tests

```sh
python -m pytest -q
```

Tests cover account login/logout, password/session storage, expiry, CSRF/origin checks, throttling, per-user ownership, video ranges and the existing ingestion/analysis flow. Provider requests use test doubles. Live Gemini analysis and representative football footage still require evaluation.

The responsive analysis studio is served at `/studio`; see [studio setup and browser tests](ANALYSIS_STUDIO.md). Pundit Mode, match chat, human event review, movement tracking and PDF export are not implemented yet.
