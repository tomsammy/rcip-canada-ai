# Wall-Clock Bounded Concurrent Official Sync Without Fabrication

Live portal synchronization (`POST /api/sync-sources`) crawls official government URLs concurrently with tight per-socket timeouts and an explicit `9.0s` wall-clock bound (`pool.shutdown(wait=False, cancel_futures=True)`), storing only verbatim HTTP `200` text alongside exact SHA-256 content hashes.

When remote government portals block automated HTTP fetches (`403`, JS-only shells, TLS errors, or timeouts), **JapaAI.ng** records the failure against the exact `country_id` and `url` instead of synthesizing replacements, keeping the verified **Source Registry** baseline and direct government links intact so full 12-country sync completes reliably within Vercel's serverless window.
