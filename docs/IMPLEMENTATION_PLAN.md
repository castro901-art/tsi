# Implementation plan

## Architecture

- React and TypeScript for the responsive studio.
- FastAPI for ingestion, analysis jobs and evidence APIs.
- A background worker for provider requests and selected-sequence tracking.
- SQLite and local file storage during development; replaceable persistence adapters for hosting.
- Provider interfaces separating video understanding, detection, tracking and report generation.

Hosted authentication and storage will be selected after reviewing their limits and terms. Gemini is the first video-understanding adapter to evaluate; model availability, free-tier eligibility, commercial terms and footage handling need verification before live use. Open-weight alternatives require their own licence and compute review.

## 1. Ingestion and analysis backend

Accept authorised uploads first. Validate container, video stream, size and duration; reject unsupported URLs explicitly. Store metadata and source provenance. Queue analysis, persist structured candidate events and expose real job status and failure codes.

Validate provider output against the schema and actual video duration. Store observations separately from interpretations. Model output starts unverified, regardless of its confidence score. Retain model and pipeline versions.

Keep credentials server-side. Bound upload size, duration, queue depth and concurrency. Do not retry quota failures through another paid service. URL ingestion requires an approved support matrix, platform compliance and SSRF protection.

## 2. Studio and evidence review

Build a mobile-first submission and results flow. Connect video playback to a timestamped event timeline. Allow metadata correction and correct/incorrect/uncertain event review with audit history. Generate a report whose claims refer to stored evidence and whose limitations remain visible.

Add tested resource ownership, a bounded guest path and signed-in persistence. Users should not need a club subscription. Add report reopening, structured export, PDF export and access-controlled sharing with revocation.

## 3. Pundit Mode and Ask the Match

Generate editorial formats from the analysed evidence. Retrieve relevant events before answering questions and retain conversation context. Cite source ranges, retain verification labels and explain missing evidence. A repeated model claim does not become a verified fact.

## 4. Movement review

Detect and track players in selected short sequences. Measure camera-cut handling, occlusion and identity switches before exposing paths. Use anonymous track labels unless identity is verified. Image coordinates are not pitch metres without calibration.

Start with real position overlays and pause/scrub controls. Then add player selection, alternative positions, run paths and annotations where tracking is reliable. Preserve original observations separately from saved scenarios. Mobile gets a simplified destination editor; desktop can support detailed comparisons.

Scenario interpretation is qualitative and hypothetical. Do not imply a physical simulation, certain outcome or calibrated probability without implementing and validating that capability.

## Release checks

Complete the acceptance checklist in PRODUCT_REQUIREMENTS.md against authorised, representative football highlights, including Kenyan-football footage where available. Test mobile and desktop flows, upload limits, quota failures, invalid timestamps, weak tracking, ownership, share revocation and exports.

Test injection attempts in metadata and provider output. Ensure credentials and footage never enter public commits or client bundles. Confirm factual report claims refer to valid evidence ranges. Unit tests with fixtures do not replace real-footage evaluation.

The release gate includes a saved or exported movement-review scenario and clear original/hypothetical labels. Advanced full-match modelling and league-wide intelligence follow only when data and capacity support them.
