# Analysis Studio

The same-origin, dependency-free browser client is served at `/studio` and `/studio/`
by the existing FastAPI application. Follow `docs/BACKEND.md` for API/worker setup.
Use the exact `TSI_APP_ORIGIN` host/port when opening the studio. Secure session
cookies require HTTPS; only local development should disable secure cookies.

## Supported workflow

- Register (only if enabled by the server), sign in, restore a session and sign out.
- Read `/v1/capabilities` before allowing uploads. Failed capability loading disables
  upload until Refresh list successfully reloads limits.
- Create a job with the exact `MatchInput` metadata and two explicit consent fields.
- PUT a raw MP4 to the API-provided upload path as `video/mp4`, with session cookie
  and `X-TSI-CSRF`. No multipart or URL ingestion.
- Display actual server states: awaiting_upload, uploading, queued, processing,
  completed and failed. The client does not estimate analysis percentages, timings,
  or generate substitute findings. Upload transmission is labelled as a local action,
  not analysis progress. Queued jobs need a running worker.
- Poll uploading/queued/processing jobs every two seconds while selected; stop on
  completion, failure, selection changes or sign out. Status request generations
  prevent an older response overwriting a newer state.
- Resume an awaiting_upload job after selecting its original authorised file and
  confirming permissions, without creating a duplicate job.
- On network/timeout errors, show that the current state is unknown and allow an
  explicit Check status. Never automatically resubmit a job or switch providers.
- Render only completed API results. Missing results, unknown states and failure
  codes never expose sample findings. All returned text is inserted as text, not HTML.
- Review source-video timestamps, unverified candidate observations, evidence-linked
  tactical interpretations, source upload IDs/SHA-256, model/pipeline provenance and
  limitations. Confidence is labelled an uncalibrated model estimate.
- Seek protected same-origin video and download the existing plain-text report.
  Analyses are saved by the API and can be reopened after refresh or sign-in.

URL ingestion, movement tracking/editing, match chat, human review, PDF and public
sharing remain unavailable. The UI does not imply those APIs exist. The backend's
existing development account, quota and retention restrictions still apply.

## Validation

```sh
pip install -r requirements-e2e.txt
python -m playwright install chromium
# Linux hosts may need: python -m playwright install-deps chromium
python -m pytest -q
```

Without Playwright, the optional browser test module is skipped; install it to run
layout checks. Browser tests start an isolated localhost API with temporary SQLite
storage, generate synthetic MP4s, and use clearly labelled provider test doubles.
They never call Gemini or touch live account/R2 data. Request failures are injected
only in tests; there is no mock mode or test data embedded in the shipped client.

Chromium checks cover 360, 390, 768 and 1440 pixel widths, single/two-column layouts,
no horizontal overflow, 44px-or-larger buttons, exact uploaded bytes (API SHA-256),
CSRF headers, queued/processing/completed transitions, candidate seeking, evidence
links, report export, safe text rendering, persistence, login/logout, invalid uploads,
provider errors, capability retry, resumed uploads, network recovery and session
expiry. Unknown states and completed jobs without results are also checked.
Screenshots are written to each test's temporary directory; set `TSI_TEST_ARTIFACTS`
to retain them elsewhere. Tests do not establish real football analysis quality or
coverage on physical devices, Safari or Firefox. Evaluate representative authorised
footage with the real provider before release.

## Storage/deployment follow-up

The studio does not change local video/database storage. Private R2 storage integration
and VPS deployment will be separate changes, preserving authenticated ownership
checks. Do not put application credentials or populated `.env` files in commits.
