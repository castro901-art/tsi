# Backend

The development API accepts authorised MP4 uploads, validates them with FFprobe and queues Gemini analysis. Results contain candidate observations, timestamp references and separately labelled interpretations. SQLite stores jobs and results; a separate worker processes one job at a time.

This is a local, single-operator backend. The access token is not a user-account system. Do not expose it as a public service or put the token into a browser bundle. User authentication, ownership controls, frontend, URL ingestion, event review, PDF export, Pundit Mode, chat and movement tracking are still to be added.

## Run locally

Requires Python 3.11+ and FFmpeg/FFprobe on PATH. Tests were run with Python 3.13.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Set the server-side Gemini key and model in `.env`. Choose a currently available video-capable model after reviewing provider terms. Set a random access token of at least 32 characters; generate one with:

```sh
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Do not commit the populated file. Review billing eligibility, quotas and handling of uploaded footage before setting `TSI_PROVIDER_TERMS_ACCEPTED=true`. That flag records operator approval; it cannot verify that an API project has billing disabled. Use an eligible unbilled project for free-tier trials. The code never chooses another provider or model when quota is exhausted.

Load configuration and start the API:

```sh
set -a
. ./.env
set +a
uvicorn api.main:app --host 127.0.0.1 --port 8000
```

In another terminal, activate the same environment, load `.env` and run:

```sh
python -m api.worker
```

The API can start without Gemini configuration, but submissions are blocked until the key, model and terms flag are configured. The worker requires those settings at startup. No external API is contacted just by starting the API server.

## Submit footage

Create an analysis; metadata is user-supplied, not independently verified:

```sh
curl -s http://127.0.0.1:8000/v1/analyses \
  -H "Authorization: Bearer $TSI_ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Match highlights","authorised":true,"provider_processing_consent":true}'
```

Copy the returned ID into `ANALYSIS_ID`, then upload the file as a raw request body:

```sh
curl -s -X PUT "http://127.0.0.1:8000/v1/analyses/$ANALYSIS_ID/video" \
  -H "Authorization: Bearer $TSI_ACCESS_TOKEN" \
  -H 'Content-Type: video/mp4' --data-binary @highlights.mp4
```

This is not a multipart endpoint. Files must contain an MP4 video stream, be at most 100 MiB, last no more than ten minutes and have dimensions no larger than 3840x2160. These are development limits, not measured guarantees of provider accuracy or capacity.

## Endpoints

All `/v1` routes require the operator bearer token.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Process health |
| GET | `/v1/capabilities` | Source support and limits |
| POST | `/v1/analyses` | Create a submission |
| PUT | `/v1/analyses/{id}/video` | Stream an MP4 upload |
| GET | `/v1/analyses` | List local analyses |
| GET | `/v1/analyses/{id}` | Job status and structured results |
| GET | `/v1/analyses/{id}/report` | Plain-text evidence report |

Jobs move through `awaiting_upload`, `uploading`, `queued`, `processing`, then `completed` or `failed`. A queued job needs a running worker. Failures include missing configuration, invalid footage, upload limits, provider rejection, quota exhaustion and invalid event references. Interrupted uploads/jobs are marked failed after thirty minutes; they are not automatically resubmitted.

Timestamps use seconds in the uploaded video, not the stadium match clock. Source references include upload ID and SHA-256. Model event IDs are assigned by the backend. Team/player identities remain unset. Confidence is an uncalibrated model estimate; every event and interpretation remains unverified. Schema validation checks ranges and citation references, not factual accuracy.

## Storage and retention

The instance holds at most twenty analyses. The running worker removes inactive analyses and associated footage seven days after creation. With the worker stopped, automatic cleanup does not run. Results survive API restarts until expiry. Provider files are deleted on a best-effort basis after processing; failed deletion and provider-side data retention are subject to the provider's own policy.

SQLite and local files are a development choice, not a multi-instance deployment design. Before hosting, add account ownership, per-user quotas, request deadlines, rate limiting, worker leases/heartbeats, restricted media serving and isolated video validation. Keep FFmpeg patched. Do not expose the shared operator token to end users.

## Tests

```sh
python -m pytest -q
```

Tests cover consent/configuration guards, access control, invalid uploads, size/storage limits, persistence, queue transitions, schema/evidence validation, quota failures, retention and the provider adapter. The ingestion test uses a generated video; provider calls use test doubles. No real football clip or live Gemini request was evaluated in this milestone.
