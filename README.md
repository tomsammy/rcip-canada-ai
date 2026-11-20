# JapaAI.ng — Official 12-Country Immigration & PR Roadmap Platform

Built on the **Opportunity AI** architecture (`FastAPI + SQLite WAL + Grounded Gov RAG + Evidence-Based Scoring`), **JapaAI.ng** (`japaai.ng`) is a real-time curated official-source immigration and Permanent Residence (PR) roadmap platform built for applicants worldwide across **12 countries**:

**Canada** (RCIP Pilot & 2027 Permanent Program, Express Entry, PNP, Atlantic Immigration, Francophone Pilot, Study-to-PR) · **United Kingdom** · **United States** · **Germany** · **Netherlands** · **Sweden** · **Estonia** · **Bulgaria** · **Lithuania** · **Spain** · **France** · **Brazil**

---

## Key Capabilities

1. **Cross-Country "Find My Pathway" Matcher (`POST /api/global/match`):**
   - Evaluates your education, work experience, sector, language skills, relocation budget, remote income, and job offer status across all 12 countries.
   - **Zero fake score floors:** Empty or incomplete profiles honestly return `INCOMPLETE` with `0` matches.
   - Groups matches into **Strong Matches**, **Viable With Sponsored Job Offer**, and **Prepare & Close Gaps**, enforcing hard rules (e.g., strict sector gates, French requirements, and DV lottery rules).

2. **12 Official Country Hubs & Real-Time Live Snapshots (`GET /api/countries`):**
   - Direct links strictly to verified government portals (`canada.ca`, `gov.uk`, `uscis.gov`, `make-it-in-germany.com`, `ind.nl`, `migrationsverket.se`, `politsei.ee`, `mvr.bg`, `migracija.lrv.lt`, `exteriores.gob.es`, `france-visas.gouv.fr`, `gov.br`, etc.) — curated directly with zero added assumptions or omissions.
   - Interactive step-by-step pathway checklists, 2026 verified income/salary thresholds, international applicant notes, real-time live portal snapshots (`POST /api/sync-sources?country_id=...`), and printable HTML dossier exports (`POST /api/global/roadmap/export/html`).

3. **Canada RCIP Eligibility, Tools & 14-Community Toolkit:**
   - **6-Stage Official Canada.ca Guided Roadmap** branching dynamically for Outside/Inside Canada, Work Permit funds exemptions, Local International Graduates, and **Pilot (<= Dec 31, 2026) vs Permanent Program (Jan 1, 2027+)**.
   - **Honest 6-Pillar RCIP Scoring**, **IRCC Language Converter** (`CELPIP-General`, `IELTS General Training`, `PTE Core`, `TEF Canada`, `TCF Canada`), **Settlement Funds Calculator**, **Resume Parser & NOC 2021 Matcher**, and **All 14 RCIP Participating Communities**.

4. **Real-Time Official Gov Sync & RAG Copilot (`POST /api/sync-sources`, `POST /api/chat`):**
   - Concurrently fetches live official portals across all 12 countries, detects changes via SHA-256 content hashes, and quotes direct official government excerpts with clickable citations.

5. **Installable Mobile App (PWA) & Private Browser Persistence (`localStorage`):**
   - Installable on Android and iPhone/iPad (`manifest.webmanifest` + `/sw.js`), with private browser `localStorage` persistence (`japaai_ng_state_v3`) locally and on Vercel deployments.

---

## Quick Start (Local Run)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch Server
```bash
python run_server.py
```
Open your browser at **`http://127.0.0.1:8001`**.

### 3. Run Automated Tests
```bash
python -m unittest discover -s tests -v
```

---

## API Reference

* `GET /api/health` — Service (`JapaAI.ng`), indexed pages, `live_global_pages`, `last_synced_at`, and country count (`12`)
* `GET /api/countries` — List all 12 destination country hubs (supports `?region=` and `?search=`)
* `GET /api/countries/{country_id}` — Full official country hub, pathways, thresholds, checklists, `applicant_notes`, and `live_snapshots`
* `POST /api/global/match` — Cross-country pathway scorer across all 12 countries (`INCOMPLETE` when empty)
* `POST /api/global/roadmap/export/html` — Printable HTML country/pathway dossier with escaping
* `POST /api/sync-sources` — Real-time concurrent sync across all 12 or 1 country (`?country_id=`)
* `POST /api/sync-canada` — Fetch live `canada.ca` RCIP Pilot & Permanent Program pages
* `GET /api/sources` — List real-time live snapshots and verified official portals across all 12 countries
* `POST /api/chat` — Country-scoped (`country_id`) or auto-detected Official Gov RAG Q&A with clickable citations
* `GET /api/stats` — Canada RCIP readiness score, roadmap completion, active track/branch, indexed pages
* `GET /api/profile`, `POST /api/profile` — Save/retrieve candidate profile
* `POST /api/resume/upload` — Parse `.pdf`/`.docx`/`.txt` upload or JSON `resume_text`
* `POST /api/evaluate` — Evaluate Canada RCIP 6 eligibility pillars & prioritized gap action plan
* `GET /api/roadmap` & `POST /api/roadmap/compute` — Tailored 6-stage Canada.ca RCIP roadmap + IMM forms
* `POST /api/roadmap/progress` — Persist checklist item completion & notes
* `POST /api/tools/clb-convert` — Convert raw CELPIP/IELTS/PTE/TEF/TCF scores to CLB/NCLC
* `GET /api/tools/funds` — Calculate exact CAD settlement funds or work-permit exemption
* `GET /api/tools/noc-search` — Search representative NOC 2021 codes & TEER categories
* `GET /api/communities` & `POST /api/communities/shortlist` — 14 RCIP communities & outreach tracker
* `GET /api/roadmap/export/html` & `POST /api/roadmap/export/html` — Printable HTML RCIP dossier

---

## Deployment & `japaai.ng` Custom Domain Setup

### Deploy to Vercel (Recommended — Zero Required Env Vars)
JapaAI.ng includes a root FastAPI entrypoint ([app.py](app.py)), Fluid Compute configuration ([vercel.json](vercel.json)), and [.vercelignore](.vercelignore):
1. Push to GitHub (`main` branch auto-deploys to Vercel) or run `vercel --prod`.
2. **Persistence model on Vercel:** When `VERCEL` is set, the backend caches RAG snapshots in `/tmp/rcip.db` while each visitor's global profile, 12-country checklists, Canada RCIP profile, and shortlisted communities persist privately in browser `localStorage` (`japaai_ng_state_v3`) and compute statelessly.

### Registering & Connecting `japaai.ng`
Vercel's domain registrar does not sell `.ng` ccTLDs directly. To go live on `japaai.ng`:
1. Register `japaai.ng` through a **NiRA-accredited `.ng` registrar** (such as Whogohost, QServers, Truehost, or DomainKing).
2. In your Vercel project (**Settings -> Domains**), add `japaai.ng` and `www.japaai.ng`.
3. Point your DNS records at your registrar to the exact `A` and `CNAME` values shown by Vercel, then wait for automatic TLS certificate issuance.

### Render / Docker
* **Render:** Configured via `render.yaml` (`pip install -r requirements.txt` / `python run_server.py`, `NO_RELOAD=1`).
* **Docker:** Configured via `Dockerfile` exposing port `8001`.

*Disclaimer: JapaAI.ng curates official government documentation across 12 destination countries with no added assumptions for planning purposes only and does not constitute legal immigration advice.*
