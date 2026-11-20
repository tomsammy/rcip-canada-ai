# RCIP Canada AI — Official Canada.ca Guided Roadmap & Eligibility Platform

Modeled on the **Opportunity AI** architecture (`FastAPI + SQLite WAL + Live Crawler + Grounded RAG + Evidence-Based Scoring`), **RCIP Canada AI** guides candidates end-to-end through Canada's **Rural Community Immigration Pilot (RCIP)** and its transition into the permanent **Rural Community Immigration Program** opening **January 1, 2027**.

---

## Key Capabilities

1. **6-Stage Official Canada.ca Guided Roadmap:**
   - Mirrors the exact official Canada.ca application flow: `Eligibility` -> `Job Offer & Community` -> `Community Recommendation` -> `PR Portal Application` -> `Optional 2-Year Work Permit` -> `After You Apply & Settling in Canada`.
   - Dynamically branches for **Outside-Canada** vs **Inside-Canada** applicants, **Valid Work Permit Settlement Funds Exemption**, **Local International Graduate Work Experience Exemption**, and **Pilot (<= Dec 31, 2026) vs Permanent Program (Jan 1, 2027+)**.
   - Tracks checklist completion persistently in SQLite and links directly to official IRCC forms (`IMM 0246`, `IMM 0247`, `IMM 0248`, `IMM 0008`, `IMM 5669`, `IMM 5406`, `IMM 5562`, `IMM 5409`, `IMM 5604`, `IMM 5476`, `IMM 5475`).

2. **Honest 6-Pillar RCIP Eligibility & Gap Engine:**
   - **Zero fake score floors:** Incomplete profiles honestly score `0/100`.
   - Enforces official **TEER cross-matching** (including TEER 5 same 5-digit NOC requirement and the Registered Nurse NOC `31301` -> `33102`/`44101` healthcare exception).
   - Evaluates **Local International Graduate Exemptions** (2+ yr 16/24 mo residency, Master's/PhD <=2 yr full-duration residency, 18-month window, and all 3 official disqualifiers).
   - Includes a live **IRCC Language Converter** (`CELPIP-General`, `IELTS General Training`, `PTE Core`, `TEF Canada`, `TCF Canada`) using the lowest-skill-governs rule, plus the **Settlement Funds Calculator** (`$10,507` CAD for 1 up to `$27,806` for 7 + `$2,831` per additional family member).
   - Surfaces **ECA validity (<5 years)** and special regulated profession rules (`CACB` for NOC `21200`, `MCC` for NOC `31100/31101/31102`, `PEBC` for NOC `31120`).

3. **Resume Parser & NOC 2021 Matcher:**
   - Extracts stated skills and suggests up to 3 candidate **NOC 2021** codes/TEER levels from uploaded `.pdf`, `.docx`, or `.txt` resumes without fabricating credentials.

4. **All 14 Official Participating Communities & EDO Directory:**
   - Verified Economic Development Organization (EDO) portals from `canada.ca` across Nova Scotia, Ontario, Manitoba, Saskatchewan, Alberta, and British Columbia, with shortlist tracking and employer outreach counts.

5. **Live Canada.ca Sync & Grounded RAG Copilot:**
   - Crawls all 19 official RCIP Pilot and Permanent Program pages on `canada.ca`, detects updates via content hashes, indexes chunks into TF-IDF + phrase RAG, and answers user questions with clickable `canada.ca` citations.

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

* `GET /api/health` — Service & index status
* `GET /api/stats` — Readiness score, roadmap completion, active track/branch, indexed pages
* `GET /api/profile`, `POST /api/profile` — Save/retrieve candidate profile
* `POST /api/resume/upload` — Parse `.pdf`/`.docx`/`.txt` upload or JSON `resume_text`
* `POST /api/evaluate` — Evaluate 6 eligibility pillars & prioritized gap action plan
* `GET /api/roadmap` — Tailored 6-stage Canada.ca roadmap + IMM forms
* `POST /api/roadmap/progress` — Persist checklist item completion & notes
* `POST /api/tools/clb-convert` — Convert raw CELPIP/IELTS/PTE/TEF/TCF scores to CLB/NCLC
* `GET /api/tools/funds` — Calculate exact CAD settlement funds or work-permit exemption
* `GET /api/tools/noc-search` — Search representative NOC 2021 codes & TEER categories
* `GET /api/communities` & `POST /api/communities/shortlist` — 14 communities & outreach tracker
* `POST /api/sync-canada` — Fetch live `canada.ca` RCIP Pilot & Permanent Program pages
* `GET /api/sources` — List indexed `canada.ca` pages, language charts & ECA bodies
* `POST /api/chat` — Grounded Canada.ca RAG Q&A with citations
* `GET /api/roadmap/export/html` — Printable HTML personalized roadmap dossier

---

## Deployment (Vercel / Render / Docker)

### Deploy to Vercel (Recommended — Zero Required Env Vars)
RCIP Canada AI includes a root FastAPI entrypoint ([app.py](app.py)), Fluid Compute configuration ([vercel.json](vercel.json)), and [.vercelignore](.vercelignore):
1. Push this directory to GitHub (or install Vercel CLI with `npm i -g vercel` and run `vercel --prod` from the project root).
2. Import the repository in Vercel and click **Deploy** — no environment variables are required.
3. **Persistence model on Vercel:** When `VERCEL` is set, the backend caches `canada.ca` snapshots in `/tmp/rcip.db` while each visitor's profile, checklist progress, and shortlisted communities persist privately in their browser `localStorage` and compute statelessly via `POST /api/roadmap/compute` and `POST /api/roadmap/export/html`. (If you later want multi-device user accounts, attach a Vercel Marketplace database such as Neon Postgres or Turso.)

### Render / Docker
* **Render:** Configured via `render.yaml` (`pip install -r requirements.txt` / `python run_server.py`, `NO_RELOAD=1`).
* **Docker:** Configured via `Dockerfile` exposing port `8001`.

*Disclaimer: This tool organizes public Government of Canada (`canada.ca`) documentation for planning purposes only and does not constitute legal immigration advice.*
