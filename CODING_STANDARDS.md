# JapaAI.ng Coding Standards

## Non-Negotiable Domain Invariants

1. **Zero fake score floors**: Empty or incomplete **Applicant Profiles** must return `0` (RCIP) or `INCOMPLETE` with `0` matches (global).
2. **Verbatim official truth**: Never fabricate URLs, fees, salary thresholds, or **Live Snapshot** excerpts when remote portals block scraping.
3. **Global neutrality**: Country **Destination Hubs**, **Pathway** steps, and **Dossiers** serve applicants worldwide unless an official policy explicitly states a nationality restriction (e.g., US DV >50k rule).
4. **Strict HTML escaping at render seams**: Escape every user string (`notes`, `applicant_name`, search queries) via `html.escape` in Python and `esc()` in JS.
5. **Single source of truth for enums**: Catalog enums live in [backend/catalog_schema.py](backend/catalog_schema.py) and must match UI selectors enforced by `python scripts/check.py`.
6. **Testable IO seams**: Network and filesystem adapters are injected (`fetcher=`) at module seams rather than hardcoded inside orchestration logic.

## Review Smell Baseline (Judgement Calls)

Flag these when reviewing diffs unless overridden above or enforced by `scripts/check.py`:
- **Mysterious Name**: identifier fails to reveal intent — rename using `GLOSSARY.md` terms.
- **Duplicated Code**: repeated HTML templates, scoring branches, or escaping logic across hunks — extract one helper.
- **Divergent Change / Shotgun Surgery**: route handlers owning HTML assembly, crawl orchestration, and persistence together — keep them behind seam modules.
- **Primitive Obsession / Speculative Generality**: hardcoded magic strings that belong in `catalog_schema.py`, or speculative abstractions with only one caller.
- **Middle Man**: pass-through wrappers failing the deletion test.
