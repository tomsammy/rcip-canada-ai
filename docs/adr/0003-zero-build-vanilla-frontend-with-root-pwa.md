# Zero-Build Vanilla Frontend With Root-Scoped PWA

The web client is split into small zero-build JavaScript modules ([utils.js](../../frontend/js/utils.js), [pwa.js](../../frontend/js/pwa.js), [app.js](../../frontend/app.js)) served directly by FastAPI alongside root-scoped PWA endpoints (`/manifest.webmanifest`, `/sw.js` with `Service-Worker-Allowed: /`, and `/apple-touch-icon.png`).

Choosing vanilla modules over Next.js or a bundler eliminates build pipelines, preserves single-command Python deployment on Vercel/Docker/Render, and allows both browser `<script>` loading and `node --test` verification without transpilation—with the explicit trade-off of manual cache-busting query versions (`?v=N`) mirrored in `frontend/sw.js`.
