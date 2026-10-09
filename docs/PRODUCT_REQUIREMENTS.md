# TSI product requirements

This document consolidates the founder's development brief. All features below are requirements, not statements of implementation.

## Identity and audience

- Company: Trendify Labs.
- Product: TSI (Trendify Sports Intelligence).
- Tagline: Understand the game beyond the score.
- Initial users: football pundits, independent analysts, sports journalists, content creators, coaches and enthusiasts.
- Initial competition focus: Kenyan football, including the FKF Premier League.
- Platforms: responsive mobile and desktop web; no native Android app required. Evaluate PWA installation if appropriate.

## Vision

Provide real video analysis of legally accessible highlights without specialist equipment, stadium cameras, professional analysis software or advanced data expertise. Do not substitute generic prompted commentary for actual video understanding.

## Primary journey

1. Open TSI and choose Analyse a Match.
2. Paste a supported video URL or upload authorised footage.
3. Validate the source, permissions and technical constraints; explain highlight limitations.
4. Start asynchronous analysis and display progress.
5. Extract candidate events and observations.
6. Explore results, timestamped evidence and clips only where permitted.
7. Open movement review for supported sequences, pause/scrub, and inspect reliable detections.
8. Select a player and create an alternative position or run destination where confidence permits.
9. Compare original movement with the user's hypothetical overlay; never alter original evidence.
10. Ask evidence-grounded follow-up questions within the same analysis.
11. Correct metadata, review findings, then save, export or share the report and supported scenarios.

Persist signed-in analyses. Provide a sensible guest/trial path if supported by the selected architecture, with enforced usage limits. A club account or institutional subscription must not be required to try the core workflow.

## Match Analysis Studio

Provide URL/upload inputs, title, optional teams, competition and date where known, analysis type selection, progress, results, metadata correction, save and export controls. Mobile must be first-class: single-column flow, large touch targets, readable reports and lightweight visualisations. Desktop can place video, timeline and report side by side.

## Video understanding and candidate events

Use a configurable provider; evaluate the current Gemini free tier and practical open-weight alternatives before selection. Identify candidate goals/scoring sequences, shots, saves, corners, free kicks, combinations, counterattacks, visible defensive errors, set pieces and supported player movements. Every finding needs a timestamp/video reference when available. Distinguish direct observations from model interpretations.

Do not assume public URLs are processable. Maintain an explicit ingestion support matrix. Respect platform terms, copyright, access controls and permitted ingestion methods; never bypass restrictions.

## Tactical report

- Attacking: visible development, progression, wide play, combinations, chance creation, finishing, runs, positioning and possible alternatives.
- Defensive: visible actions, marking/positioning problems, transitions, errors leading to chances and alternative coverage.
- Set pieces: visible routines, deliveries, finishing and questions for further investigation; optional movement review.
- Match interpretation: supported turning points, strengths, weaknesses, alternative explanations and unresolved questions.

Never infer unseen match periods as historical fact. Separate what happened from what might have happened under a user adjustment.

## Pundit Mode

A core differentiator, generating grounded editorial material rather than generic commentary. Formats: five talking points; tactical breakdown; a qualified discussion of why a match was won/lost; player observations; controversial decisions needing review; pre/post-match notes; podcast questions; video script outline; short social posts; alternative movement/coaching discussion points.

Every factual claim must reference verified event data or an identified source. Candidate observations must stay explicitly unverified. Never invent quotations, referee decisions, player identities or statistics. Inconclusive footage must remain inconclusive. Pre-match notes require separately sourced information where the analysed footage cannot establish it.

## Ask the Match

Retrieve relevant stored events and evidence before answering. Preserve conversation context without resubmitting footage. Support questions about important sequences, chance development, defensive mistakes, reasonable conclusions, talking points, unavailable evidence and alternative runs/positions. Every response must separate observations, interpretations and user-created hypothetical scenarios.

## Timeline and review

Each event shows timestamp, type, explanation, verified team/player identity only where justified, confidence/verification status, supported source link and reliable movement information. Users can mark findings correct, incorrect or uncertain; retain review provenance.

For supported sequences: pause and scrub frames or intervals; show markers/paths only at sufficient confidence; select a player; drag an alternative position or draw a run; compare original/hypothetical overlays; annotate (e.g. run earlier, hold width, drop deeper, attack near post, cover passing lane); save/name/share scenarios where supported. Provide simplified mobile positioning controls and larger desktop/side-by-side views where practical.

Store evidence and scenarios separately. Explain that this is a tactical/coaching exercise, not proof of an outcome. Qualitative consequences may describe possible passing options, space or coverage but not certain outcomes. Do not imply physics simulation unless implemented. Camera cuts, occlusion, kit similarity, low quality, cropping and uncertain identities constrain tracking; avoid precise-looking unreliable paths.

Download clips only with permission and implemented technical capability. Otherwise provide supported timestamped source references.

## Persistence, export and access

Save/revisit analyses; PDF report export; copy talking points; access-controlled share links; structured event export; supported scenario/annotation export. Reports include source, analysis date, limitations and verification status. All shared/exported hypothetical movements must retain conspicuous labels. Guest data must have clear retention/expiry; signed-in resources need ownership enforcement.

## Architecture boundaries

Separate ingestion, video understanding, player/object detection, movement tracking, event extraction, validation, evidence storage, tactical interpretation, hypothetical scenario storage/interpretation, report generation, conversational retrieval and export/sharing. Start with one supported provider behind a replaceable interface.

### Candidate event data

Match ID; event type; start/end timestamps; team/player identifiers only where verified; description; confidence; source reference; verification status; model and pipeline versions; positions/paths where available; tracking confidence; occlusion status. Store observation versus interpretation explicitly. Preserve timestamp basis, evidence provenance and review history.

### Hypothetical scenario data

Scenario ID; match ID; source event ID; selected player; original position/path; adjusted position/path; timestamp range; annotations; generated interpretation; explicit hypothetical status; creator; creation date. Original evidence is immutable relative to scenario editing.

## Cost and security

Evaluate free quotas AND commercial/data-processing terms. Support practical local/open-weight inference where suitable. Bound duration, size and concurrency; cache only where permitted; avoid repeated work; use asynchronous jobs and transparent failures. Prioritise selected-sequence tracking rather than full-match tracking. Gate advanced review by confidence and capacity. No unlimited-free promise or silent paid fallback. Explicit approval precedes paid services. Never put API keys in browser bundles, commits or logs.

## Honest boundaries

No full-match possession, complete passing networks, player heatmaps, formations or comprehensive pressing claims from incomplete highlights without adequate footage or a separately verified source. Clearly label direct observations, model interpretations, human verification, detected movements, hypothetical movements and unknowns. Important findings require appropriate human review before being presented as established facts.

## Repository change rules

Before changes, inspect structure/framework/backend/database/authentication; reuse conventions; preserve unrelated routes/features. This new repository initially contains only a README, so there is no application stack to replace. Do not replace the existing website. Build the smallest complete working flow, not a static mockup or fake progress/results. Increment movement review from real position overlays and pause/scrub controls to editable alternatives only after tracking, persistence and rendering are reliable.

## MVP acceptance checklist

All unchecked until implemented and validated:

- [ ] 1. Open TSI on phone and laptop.
- [ ] 2. Submit authorised highlights.
- [ ] 3. Run real analysis through a configured provider.
- [ ] 4. View extracted events with evidence.
- [ ] 5. Read a tactical report with explicit limitations.
- [ ] 6. Generate grounded Pundit Mode discussion points.
- [ ] 7. Ask follow-ups about the same match.
- [ ] 8. Save and revisit a report.
- [ ] 9. Export or share analysis.
- [ ] 10. Understand source/quota/processing failures.
- [ ] 11. Open at least one reliably supported movement sequence.
- [ ] 12. Pause/scrub with real detected positions or paths.
- [ ] 13. Select a player and create an alternative position/run destination where confidence permits.
- [ ] 14. Compare original and hypothetical movement.
- [ ] 15. See unambiguous observed/hypothetical labels.
- [ ] 16. Save or export a supported scenario.
- [ ] Test on representative real football highlights, including Kenyan-football footage where authorised, before release.

Final priority: validate the full responsive analyst/pundit workflow first. Advanced tracking, full-match modelling and league-wide intelligence follow only when data and capacity justify them.
