# TSI — Trendify Sports Intelligence

**Trendify Labs** · **Understand the game beyond the score.**

TSI is planned as a responsive, self-service football analysis studio for pundits, independent analysts, journalists, creators, coaches and enthusiasts. The initial competition focus is Kenyan football, including the FKF Premier League.

## Project status

**Requirements and planning only. No runnable application, video-analysis pipeline, deployed service or validated movement tracking exists yet.** The documentation describes intended functionality, not completed features.

The first release must analyse actual authorised highlight footage, store timestamped evidence, produce grounded tactical and editorial reports, support follow-up questions, and distinguish observed player movement from user-created hypothetical alternatives.

## Documentation

- [Product requirements and acceptance criteria](docs/PRODUCT_REQUIREMENTS.md)
- [Implementation plan and proposed architecture](docs/IMPLEMENTATION_PLAN.md)

## Operating principles

- Evidence before interpretation; no invented statistics or identities.
- Highlights do not establish full-match possession, heatmaps or passing networks.
- Preserve original evidence separately from hypothetical movement scenarios.
- Respect copyright, platform terms and access controls.
- Keep credentials server-side and out of Git.
- No automatic paid-provider fallback. Paid services require explicit approval.
- Test on representative real footage before calling the MVP usable.

## Relationship to the existing website

TSI is a separate repository. The existing `castro901-art/tiff-website` and its routes remain unchanged. That website's root was inspected and contains static HTML pages and assets; its deeper assets and integrations must be examined before any branding reuse or integration.

## Licensing

No software licence has been selected. Public visibility does not grant an open-source licence. Review dependency, model-weight, footage and provider terms before distribution or commercial operation.
