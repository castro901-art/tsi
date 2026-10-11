# Match dashboard and authorised platform links

The dashboard replaces the workspace layout, not the authentication system. Existing
`studio.js` remains responsible for local MP4 uploads, sessions, CSRF, polling,
upload recovery, protected playback and evidence-linked text reports. The new
`dashboard.js` adds match titles/search, status styling, source tabs, file information,
drag/drop, timeline collapse and YouTube/X import submission. All API text remains
text, never HTML. Touch controls remain at least 44px; authentication is unchanged.

## Platform link access: explicitly configured, not a bundled downloader

YouTube and X URLs are accepted by `POST /v1/analyses/from-link` with the existing
MatchInput fields nested under `metadata` and the URL under `url`. MP4 uploads use
the existing create/PUT workflow unchanged. Link import **does not work out of the
box**: no platform API, downloader, credentials, resolver subscription or paid
fallback has been provisioned. Public availability is not permission to download.
The operator must select a lawful, permitted-access resolver, review its terms and
costs, and explicitly configure it. Private/restricted footage is not bypassed.

Configure server-side only:

- `TSI_LINK_RESOLVER_URL`: trusted HTTPS resolver endpoint (443, public network).
- `TSI_LINK_RESOLVER_TOKEN`: optional bearer token, never sent to the browser/media host.
- `TSI_LINK_MEDIA_HOSTS`: comma-separated exact permitted HTTPS media hostnames.

The resolver receives `POST {"url": "canonical platform URL", "authorised": true}`
and must return `200 {"mp4_url": "direct authorised HTTPS MP4 URL"}`. It must use
permitted platform access, enforce restrictions and choose an appropriate video
where posts contain multiple media items. Unsupported sources must fail, not fall
back to unauthorised scraping. Source URLs are normalized to public video/post
identifiers; time offsets are discarded and the full returned highlight is analysed.

No redirects, URL credentials, non-443 ports or non-public network addresses are
accepted. Media hosts are allowlisted, DNS results validated, and TLS connections
pinned to validated public addresses with hostname verification. Downloads use no
resolver credentials, reject compression, bound time/bytes, hash the stored MP4
and validate its actual duration/container/resolution using the existing ffprobe.
Only then is the existing worker queue entered. Failures remove partial files and
persist a failed job. Size (100 MiB), duration (10 minutes), account quotas, consent,
ownership, retention and provider configuration remain authoritative. Do not
resubmit after a timeout; refresh saved jobs first.

Capabilities expose `url_ingestion: false` until resolver/media hosts are configured,
and the interface explains the setup requirement. Source URL/platform are retained
in metadata, evidence provenance and text reports; temporary signed media URLs and
resolver tokens are not stored in reports. Browser X/YouTube links are not embedded
or downloaded by third-party client scripts.

## Validation

Run `python -m pytest -q` with the existing browser test dependencies. Link tests
use doubles; they do not establish real YouTube/X availability or licensing.
Evaluate the configured resolver against representative authorised platform footage
before enabling imports in production. Screenshots use a local isolated account,
not live user footage or fabricated match statistics.
