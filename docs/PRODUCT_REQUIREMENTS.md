# Product requirements

## Product

TSI (Trendify Sports Intelligence) is a Trendify Labs product for football pundits, independent analysts, journalists, content creators, coaches and enthusiasts. The initial competition focus is Kenyan football, including the FKF Premier League.

**Tagline:** Understand the game beyond the score.

Build a self-service, responsive web studio that analyses legally accessible match highlights. Users should not need specialist equipment, stadium cameras or professional analysis software. Video analysis must be real, not a report generated from match metadata alone.

## User workflow

Open TSI, select Analyse a Match, upload authorised footage or submit a supported URL, review source limitations and start analysis. Show processing status, candidate events and timestamped evidence. Allow metadata correction before final report generation.

Users can review supported movement sequences, pause and scrub, select players and create alternative positions or runs. Original evidence and user adjustments remain separate. Users can ask follow-up questions and save, revisit, share or export reports and supported scenarios.

Persist signed-in analyses. Provide a bounded guest/trial workflow where the architecture supports it, without requiring a club account or institutional subscription.

## Match Analysis Studio

Include URL/upload input, title, optional team names, competition and match date where known, analysis type, progress, results and save/export controls. Explain supported sources and limitations before processing.

Mobile: single-column flow, readable reports, large touch targets, lightweight timelines, easy copying/sharing and simplified positioning controls. Desktop: video, timeline and report alongside one another where practical, with a larger review canvas and optional side-by-side movement comparisons. Evaluate an installable PWA; no native Android app is required initially.

## Highlight analysis

Use a provider-independent interface. Evaluate Gemini's current free tier and practical open-weight alternatives. Start with one supported provider.

Extract candidate goals and scoring sequences, shots, saves, corners, free kicks, attacking combinations, counterattacks, visible defensive errors, selected set pieces and supported player movement. Findings need timestamped references where available. Separate visible observations from inferred interpretations.

Do not assume public URLs are downloadable or accepted by a provider. Use supported ingestion methods and respect copyright, platform terms and access controls. Never bypass restrictions.

## Tactical reports

Organise reports into:

- **Attacking:** development of visible attacks, progression, wide play, combinations, chance creation, finishing, runs and positioning options.
- **Defensive:** visible actions, marking or positioning problems, transitions, errors leading to chances and alternative coverage.
- **Set pieces:** visible routines, delivery and finishing patterns, unresolved questions and optional positioning review.
- **Match interpretation:** supported turning points, strengths, weaknesses, alternative interpretations and what the footage cannot resolve.

Keep actual events separate from possible consequences of user adjustments. Do not claim to know unseen match periods.

## Pundit Mode

Turn analysis into useful editorial material. Support five talking points, tactical breakdowns, qualified discussions of why a match was won or lost, player observations, decisions needing further review, pre/post-match notes, podcast questions, video-script outlines, short social posts and alternative-movement discussion points.

Ground factual claims in verified events or identified sources. Keep unverified candidate observations explicitly labelled. Do not invent quotations, referee decisions, identities or statistics. Explain inconclusive footage. Pre-match context requires separate sources where the footage cannot establish it.

## Ask the Match

Retrieve relevant stored events and evidence before answering. Keep conversation context so follow-up questions do not require resubmission. Support questions about attacking sequences, chance development, defensive errors, reasonable conclusions, talking points, unavailable evidence and alternative positioning or timing.

Cite evidence and distinguish observations, interpretations and user-created hypothetical scenarios in every answer.

## Evidence timeline

Each finding includes timestamp, type, explanation, verified identity where available, confidence/verification status, supported source link and reliable movement information. Let users mark findings correct, incorrect or uncertain and retain review history.

Only offer downloadable clips with permission and implemented technical support; otherwise provide timestamped source references.

## Movement review

For supported sequences, provide pause/scrub controls and detected-player markers, silhouettes or tracking points. Show paths only where confidence supports them. Let users select a player, drag an alternative position or draw a run, annotate the adjustment and compare original and hypothetical movement without changing the video.

Annotations may include run earlier, hold width, drop deeper, attack the near post and cover the passing lane. Allow naming, saving and sharing scenarios where supported.

Tracking can fail across camera cuts, occlusion, similar kits, low quality and cropped footage. Show uncertainty; do not draw precise-looking unreliable paths or assume player identity.

A scenario is a tactical/coaching exercise, not evidence of what happened or proof of what would happen. Qualitative interpretation may discuss possible passing options, space or coverage. Never assert a certain result or imply physics simulation without an implemented, validated simulation.

## Reports and access

Save and reopen analyses. Export PDF reports and structured event data, copy talking points, and share reports with appropriate access controls. Export scenarios/annotations where supported.

Include source footage reference, analysis date, limitations and verification status in exports. Keep hypothetical labels in shared/exported scenarios. Enforce ownership and define guest retention/expiry.

## Data and service boundaries

Separate ingestion, video understanding, object detection, movement tracking, event extraction, validation, evidence storage, tactical interpretation, scenario storage/interpretation, report generation, conversational retrieval and export/sharing.

**Candidate event:** match ID, event type, start/end times, verified team/player identifiers where available, description, confidence, source reference, verification status, model/pipeline version, optional positions/paths, tracking confidence and occlusion. Record timestamp basis, observation versus interpretation and review provenance.

**Hypothetical scenario:** scenario ID, match ID, source event ID, selected player, original position/path, adjusted position/path, time range, annotations, generated interpretation, explicit hypothetical status, creator and creation date. Scenario editing cannot overwrite original evidence.

## Cost, safety and analytical limits

Verify free quotas, commercial terms and data-handling policies. Bound duration, size, concurrency and guest usage. Cache reusable results only where permitted. Use asynchronous jobs and transparent source/quota/failure messages. Track selected sequences rather than full matches by default; gate advanced review by confidence and capacity.

Never silently switch to paid APIs, promise unlimited free analysis or introduce paid services without approval. Keep secrets out of browser code, commits and logs.

Do not claim full-match possession, complete passing networks, heatmaps, formations or comprehensive pressing analysis from incomplete highlights without adequate footage or separately verified data. Label direct observations, model interpretations, human-verified events, detected movement, hypothetical movement and unavailable information. Important claims require appropriate review.

## Development approach

Inspect the current code before changes, reuse conventions and preserve unrelated features. Build the smallest complete working workflow; no fake processing or fabricated results. Add real timestamped movement overlays first, then editable positions and paths after tracking, persistence and rendering are reliable.

## MVP acceptance criteria

- [ ] 1. Open TSI on phone and laptop.
- [ ] 2. Submit authorised highlights.
- [ ] 3. Run real analysis through a configured provider.
- [ ] 4. View events with evidence.
- [ ] 5. Read a tactical report with explicit limitations.
- [ ] 6. Generate grounded Pundit Mode discussion points.
- [ ] 7. Ask follow-ups about the same match.
- [ ] 8. Save and revisit a report.
- [ ] 9. Export or share analysis.
- [ ] 10. Understand source/quota/processing failures.
- [ ] 11. Open at least one supported movement sequence.
- [ ] 12. Pause/scrub with detected positions or paths.
- [ ] 13. Select a player and create an alternative position or run destination where confidence permits.
- [ ] 14. Compare original and hypothetical movement.
- [ ] 15. See clear observed/hypothetical labels.
- [ ] 16. Save or export a supported scenario.

Validate the full workflow on representative real, authorised football highlights before release. Expand into advanced tracking, full-match tactical modelling and league-wide intelligence only when the data and technical capacity are available.
