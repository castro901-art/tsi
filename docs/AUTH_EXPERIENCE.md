# TSI authentication experience

Base: feature/analysis-studio at 52f74f8765279ba2cc1a09c386a9bdbbf0b0a412.

- /studio and /studio/ remain the sign-in and signed-in workspace routes.
- /studio/register and /studio/register/ are separate registration presentation pages.
- Registration visibility is rendered from TSI_REGISTRATION_ENABLED, default false; disabled registration pages redirect to sign-in. No credential/session API was changed.
- Authenticated visitors restore their existing sessions and see the real analysis workspace.
- The server rendering change only exposes a public registration boolean and view mode, with Cache-Control: no-store.
- Fields remain username and password. Confirmation is intentionally omitted: the strict credentials schema does not support that field.
- The supplied transparent PNG is cropped to its visible bounds and stored as a local optimized WebP plus a PNG favicon. No external images, scripts or fonts are loaded at runtime.
- Compact neutral surfaces and thin borders; discreet purple identity; two columns only above 800px. Mobile is one column.
- Visible labels, password masking, keyboard focus, pre-submit requirements on registration, inline validation, sanitized errors, loading states and duplicate request guards.
- Session expiry switches the existing page to sign-in without losing the expiry notice. CSRF tokens, cookie flags, password hashing, auth limits, ownership checks and API routes are unchanged.

Validation: 48 tests passed, covering 22 original backend tests, 15 studio cases and 11 new authentication cases. Browser checks use the real isolated localhost API and temporary accounts, at widths 360, 390, 768 and 1440. Provider fixtures are synthetic, not real football results. Both registration settings were tested, including real browser checks while disabled.

Run: python -m pytest tests -q

One existing dependency deprecation warning remains (Starlette/httpx); no test failures.
