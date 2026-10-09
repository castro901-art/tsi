# TSI implementation plan

## Status and inspected baseline

Planning only. The new public `castro901-art/tsi` repository was inspected after creation and contained only GitHub's initial README. No frontend, backend, database or authentication exists here to reuse. The existing `tiff-website` root contains static HTML and assets; deeper integrations and brand assets have not yet been audited. It will not be modified by this project setup.

## Proposed stack — not installed or deployed

- Responsive TypeScript/React web client with accessible video/timeline components.
- Python/FastAPI backend for uploads, validated schemas, provider adapters and evidence APIs.
- Separate asynchronous worker for video-understanding and selected-sequence detection/tracking; API requests must not block for long jobs.
- SQLite and filesystem storage for initial local development; configurable database/object-storage adapters for later hosting.
- Choose hosted authentication/storage only after reviewing free-tier terms, resource limits and explicit approval for any paid use. Do not invent authentication endpoints or ship placeholder login as working.
- Gemini is an evaluation candidate, not a confirmed free production service. Verify current model availability, quotas, commercial terms, footage privacy/retention and regional availability. Open-weight alternatives also require weight/dependency licensing and compute review.

## Milestone 0: prerequisites and design

1. Inspect website assets if adopting brand conventions; do not copy unrelated routes or custom-domain settings.
2. Define source support matrix. Start with authorised uploads. Add URL ingestion only through explicitly supported, compliant methods.
3. Evaluate provider on representative authorised football highlights; record dated results, cost/quota terms and temporal accuracy. No service deployment or paid configuration without approval.
4. Define schema validation and ownership model; choose auth implementation and bounded guest policy.
5. Decide numeric upload/duration/guest/concurrency limits after measurements; enforce them server-side. Decide tracking-confidence gates using validation, not arbitrary precision claims.

## Milestone 1: real vertical slice

Implement responsive submission -> source validation -> queued job -> actual provider analysis -> structured timestamped candidate events -> persisted results -> evidence timeline -> limited tactical report. Correct metadata before final generation. Display real job transitions (`queued`, `processing`, `completed`, `failed`), not timed fake progress. Preserve failure codes for unsupported source, permissions, invalid file, timeout, provider quota and model failure. Never retry quota failures by enabling paid services.

Validate file contents/container and duration, not just extension. Use size limits, request throttling, isolated worker directories and timeouts. Restrict URL adapters to approved schemes/hosts and guard SSRF, redirects/private networks. Store secrets only on the server. Do not commit or retain unauthorised footage.

## Milestone 2: review and editorial workflow

Add correct/incorrect/uncertain review with audit history, source citations and observation/interpretation labels. Pundit formats consume stored evidence; Ask the Match retrieves events and relevant ranges, retains contextual turns and cites evidence. Candidate material must not become verified merely because a model repeated it. Lack of evidence produces an uncertainty response, not a fabricated answer.

Persist signed-in analyses with tested authentication and resource ownership; trial access must not require a club subscription. Support reopen, metadata correction and revision-aware reports. Add copy talking points, structured JSON export, printable/PDF report export and scoped sharing with revocation and appropriate expiry. Exports retain all limitations and provenance. Persist report summaries separately from original structured evidence.

## Milestone 3: selected-sequence movement review

Implement actual detection and short-sequence tracking through a separate adapter. Benchmark identity switches, camera cuts and occlusions. Use normalized image coordinates for image overlays; do not label them pitch metres without calibrated mapping. Break tracks at unsupported cuts and hide uncertain paths. Player marker labels can be anonymous track IDs; do not imply verified names.

First ship synchronized position overlays with pause/scrub controls. Then add confidence-gated player selection, alternative positions/run paths, annotations and original-versus-hypothetical comparison. Mobile uses touch targets and a simplified run-destination editor. Persist scenario versions and creator access independently of evidence. Qualitative interpretation must explicitly say hypothetical; no asserted probability or physical outcome without an implemented, validated model.

## Milestone 4: end-to-end release gate

Run every acceptance criterion in PRODUCT_REQUIREMENTS.md against real authorised footage. Exercise mobile and desktop interactions, uploads, provider quotas, malformed timestamps, camera cuts, weak detections, auth ownership, share revocation, exports, prompt-injection attempts in metadata/evidence and missing evidence. Ensure report claims link to valid ranges. Test keys are never exposed in bundles/logs. Inspect public repository for secrets/media before publishing implementation commits.

Release only after a full user workflow passes, including at least one reliable movement-review sequence and saved/exported hypothetical scenario. Document measured limitations. Do not mark features complete from unit tests or mock fixtures alone.

## Proposed application boundaries

`web/` client; `api/` endpoints and auth integration; `worker/` asynchronous jobs; `providers/` interchangeable understanding/detection/tracking interfaces; `schemas/` structured events, evidence and scenarios; `tests/` unit/integration/end-to-end validation. These are proposed directories, not existing code.

Understanding adapters return structured candidate events and provider/model version. Tracking adapters return time-aligned positions, confidence, occlusion and continuity metadata. Validation checks ranges against actual source duration, schema conformance, evidence references and review provenance. Report/chat services retrieve evidence; scenario services cannot overwrite observed tracking.

## Unresolved release dependencies

Configured provider credentials; provider/free-tier terms evaluation; authorised evaluation footage; chosen auth/hosting solution; measured duration/size limits; verified tracking method and dependency/model licences. No paid service, unrestricted URL downloader, full-match statistics, league data integration or physics simulation is included by default.
