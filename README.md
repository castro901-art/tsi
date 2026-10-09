# TSI

**Trendify Sports Intelligence**  
Understand the game beyond the score.

TSI is a football analysis studio from Trendify Labs for independent analysts, pundits, journalists, creators and coaches. The initial focus is Kenyan football and the FKF Premier League.

## Development

The backend supports account sessions, authorised MP4 uploads, queued Gemini analysis, saved candidate events, evidence-linked text reports and protected video playback. See [backend setup](docs/BACKEND.md) for local development.

The responsive studio is available at `/studio`; live-provider evaluation is still pending. Pundit Mode, match chat, event review and movement review are still planned.

Highlights show only part of a match. TSI separates observations from interpretations and does not infer full-match statistics from edited footage.

## Documentation

- [Backend setup and API](docs/BACKEND.md)
- [Product requirements](docs/PRODUCT_REQUIREMENTS.md)
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)

No software licence has been selected yet.

## Analysis Studio

Open `/studio` on the running API to upload authorised MP4s, check actual job states,
review unverified evidence and download the existing plain-text report.
See [studio setup and tests](docs/ANALYSIS_STUDIO.md). No sample analysis is shipped.
R2 integration and hosted deployment remain separate follow-up work.
