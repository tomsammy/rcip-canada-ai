# JapaAI.ng Engineering Guide

- Read [GLOSSARY.md](GLOSSARY.md) before naming new modules, endpoints, or domain concepts.
- Review [CODING_STANDARDS.md](CODING_STANDARDS.md) for code invariants and review rules.
- Architectural trade-offs live in [docs/adr/](docs/adr/).

## Verification Guardrail

Run after every change:

```bash
python scripts/check.py
```

CI runs this exact script on every push and pull request in [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Core Seams

- **Catalog & Schema Invariants**: [backend/catalog_schema.py](backend/catalog_schema.py) validates [backend/countries_data.py](backend/countries_data.py) and UI parity in `#gm-field`.
- **Official Sync Seam**: [backend/sync_service.py](backend/sync_service.py) orchestrates bounded crawling via [backend/canada_crawler.py](backend/canada_crawler.py)'s injectable `fetcher` adapter, SQLite [backend/store.py](backend/store.py), and [backend/rag_service.py](backend/rag_service.py).
- **Dossier Seam**: [backend/dossier_renderer.py](backend/dossier_renderer.py) renders escaped HTML **Dossiers** for global **Pathways** and Canada RCIP.
- **Zero-Build Frontend Seam**: [frontend/js/utils.js](frontend/js/utils.js) (Node-testable pure utilities), [frontend/js/pwa.js](frontend/js/pwa.js) (PWA install), [frontend/app.js](frontend/app.js) (UI controller), [frontend/sw.js](frontend/sw.js).
