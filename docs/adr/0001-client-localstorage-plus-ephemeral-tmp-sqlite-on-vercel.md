# Client localStorage + Ephemeral `/tmp` SQLite on Vercel

Visitor **Applicant Profiles**, checked **Pathway** steps, personal notes, and RCIP shortlists persist privately in browser `localStorage` (`japaai_ng_state_v3`) and are sent to stateless compute endpoints (`/api/global/match`, `/api/roadmap/compute`, `/api/global/roadmap/export/html`), while server-side SQLite in `/tmp/rcip.db` on Vercel caches seed data and **Live Snapshots** only.

We rejected requiring an external managed Postgres/KV dependency for visitor state so the app deploys zero-config on Vercel (and falls back cleanly to durable local `data/rcip.db` SQLite WAL on VPS/Docker/local runs). Cross-device user sync is not supported unless an explicit database adapter is introduced later.
