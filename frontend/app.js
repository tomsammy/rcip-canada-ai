// JapaAI.ng Frontend Controller — Multi-Country Roadmaps + Canada RCIP Toolkit

const STORAGE_KEY = 'japaai_ng_state_v3';
const LEGACY_STORAGE_KEY = 'rcip_canada_ai_state_v2';
const THEME_KEY = 'japaai_ng_theme';
const MAX_UPLOAD_BYTES = Math.floor(4.2 * 1024 * 1024);
const DONUT_CIRCUMFERENCE = 263.89;

const esc = window.JapaUtils?.esc || (value => {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
});

function showToast(message, isError = false) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${isError ? 'error' : ''}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4200);
}

let state = {
  environment: 'local',
  countriesCatalog: [],
  countryCache: {},
  regionFilter: 'all',
  activeCountryId: 'canada',
  activePathwayId: 'ca-rcip',
  universalProfile: {},
  globalChecklist: {}, // { stepId: { completed: bool, note: str, country_id, pathway_id, title } }
  matcherResult: null,
  // Deep Canada RCIP state
  profile: {},
  progress: {},
  shortlists: {},
  roadmap: null,
  evaluation: null,
  officialForms: [],
  communitiesCatalog: [],
  provinceFilter: 'all',
  focusedStageId: null,
  wizardStep: 1,
  sources: [],
};

// --------------------------------------------------------------------------
// Theme & Persistence
// --------------------------------------------------------------------------

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY) || 'light';
  applyTheme(saved);
}

function applyTheme(theme) {
  const isDark = theme === 'dark';
  document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  localStorage.setItem(THEME_KEY, isDark ? 'dark' : 'light');
  document.querySelectorAll('.theme-icon-moon').forEach(el => el.classList.toggle('hidden', isDark));
  document.querySelectorAll('.theme-icon-sun').forEach(el => el.classList.toggle('hidden', !isDark));
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'light';
  applyTheme(current === 'dark' ? 'light' : 'dark');
}

function loadLocalBrowserState() {
  try {
    const primary = localStorage.getItem(STORAGE_KEY);
    const legacy = localStorage.getItem(LEGACY_STORAGE_KEY);
    if (window.JapaUtils?.migrateBrowserState) {
      return window.JapaUtils.migrateBrowserState(primary, legacy);
    }
    const raw = primary || legacy;
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : null;
  } catch (err) {
    return null;
  }
}

function persistBrowserState() {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        universalProfile: state.universalProfile || {},
        globalChecklist: state.globalChecklist || {},
        profile: state.profile || {},
        progress: state.progress || {},
        shortlists: state.shortlists || {},
      })
    );
  } catch (err) {
    console.warn('localStorage unavailable', err);
  }
}

// --------------------------------------------------------------------------
// Boot Sequence
// --------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', async () => {
  initTheme();
  initPwaSupport();
  setupResumeDropzone();

  let healthData = null;
  try {
    const healthRes = await fetch('/api/health');
    healthData = await healthRes.json();
    state.environment = healthData.environment || 'local';
    updateHeroSyncStatus(healthData.last_synced_at, healthData.live_global_pages);
  } catch (err) {
    console.error(err);
  }

  const localData = loadLocalBrowserState();
  if (localData) {
    state.universalProfile = localData.universalProfile || {};
    state.globalChecklist = localData.globalChecklist || {};
    state.profile = localData.profile || {};
    state.progress = localData.progress || {};
    state.shortlists = localData.shortlists || {};
  } else if (state.environment === 'local') {
    await hydrateFromLocalServer();
  }

  await Promise.all([loadCountries(), loadSources(), loadCommunities()]);
  populateUniversalForm();
  populateProfileForm();
  await recomputeRoadmapAndEvaluation();
  renderSavedProgress();

  maybeAutoRefreshRealTime(healthData);
});

async function hydrateFromLocalServer() {
  try {
    const [profRes, roadRes, commRes] = await Promise.all([
      fetch('/api/profile'),
      fetch('/api/roadmap'),
      fetch('/api/communities'),
    ]);
    const profData = await profRes.json();
    const roadData = await roadRes.json();
    const commData = await commRes.json();

    state.profile = profData.profile || {};
    const progMap = {};
    for (const stage of roadData.roadmap?.stages || []) {
      for (const item of stage.items || []) {
        if (item.completed || item.notes || item.target_date) {
          progMap[item.id] = {
            item_id: item.id,
            stage_id: stage.stage_id,
            completed: !!item.completed,
            notes: item.notes || '',
            target_date: item.target_date || '',
          };
        }
      }
    }
    state.progress = progMap;

    const slMap = {};
    for (const c of commData.communities || []) {
      if (c.shortlisted || c.notes || c.employers_contacted) {
        slMap[c.id] = {
          community_id: c.id,
          shortlisted: !!c.shortlisted,
          notes: c.notes || '',
          employers_contacted: Number(c.employers_contacted || 0),
        };
      }
    }
    state.shortlists = slMap;
    persistBrowserState();
  } catch (err) {
    console.error(err);
  }
}

// --------------------------------------------------------------------------
// Tab & Subtab Navigation
// --------------------------------------------------------------------------

function switchTab(tabId) {
  document.querySelectorAll('.ws-tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });
  document.querySelectorAll('.mobile-nav-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });
  document.querySelectorAll('.tab-panel').forEach(panel => {
    panel.classList.toggle('active', panel.id === tabId);
  });
  if (tabId === 'tab-saved') renderSavedProgress();
}

function scrollToMatcher() {
  switchTab('tab-matcher');
  const el = document.getElementById('tab-matcher');
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function switchRcipSubtab(subtabId) {
  document.querySelectorAll('.subtab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.subtab === subtabId);
  });
  document.querySelectorAll('.subtab-pane').forEach(pane => {
    pane.classList.toggle('active', pane.id === subtabId);
  });
}

function toggleMobileDrawer() {
  const drawer = document.getElementById('mobile-drawer');
  if (drawer) drawer.classList.toggle('open');
}

// --------------------------------------------------------------------------
// 12 Countries Catalog, Country Hubs & Global Checklists
// --------------------------------------------------------------------------

async function loadCountries() {
  try {
    const res = await fetch('/api/countries');
    const data = await res.json();
    state.countriesCatalog = data.countries || [];
    renderHeroCountryStrip();
    renderDestinationShowcase();
    renderCountriesGrid();
    populateCopilotCountryDropdown();
    updateGlobalCounters();
  } catch (err) {
    showToast('Failed to load 12-country catalog.', true);
  }
}

function updateGlobalCounters() {
  const cCount = state.countriesCatalog.length;
  const pCount = state.countriesCatalog.reduce((sum, c) => sum + Number(c.pathway_count || 0), 0);
  const rcipDone = Object.values(state.progress || {}).filter(p => p && p.completed).length;
  const globalDone = Object.values(state.globalChecklist || {}).filter(g => g && g.completed).length;
  const totalSaved = rcipDone + globalDone;

  const elC = document.getElementById('hero-countries-count');
  const elP = document.getElementById('hero-pathways-count');
  const elS = document.getElementById('hero-saved-steps');
  const badgeC = document.getElementById('tab-badge-countries');
  const badgeSaved = document.getElementById('tab-badge-saved');
  const mobileBadge = document.getElementById('mobile-badge-saved');

  if (elC) elC.textContent = String(cCount || 12);
  if (elP) elP.textContent = String(pCount || 43);
  if (elS) elS.textContent = String(totalSaved);
  if (badgeC) badgeC.textContent = String(cCount || 12);
  if (badgeSaved) badgeSaved.textContent = String(totalSaved);
  if (mobileBadge) {
    mobileBadge.textContent = String(totalSaved);
    mobileBadge.classList.toggle('hidden', totalSaved <= 0);
  }
}

function renderHeroCountryStrip() {
  const strip = document.getElementById('hero-country-strip');
  if (!strip) return;
  strip.innerHTML = state.countriesCatalog
    .map(
      c => `
      <button type="button" class="country-chip" onclick="openCountryHub('${esc(c.id)}')">
        <span>${esc(c.flag)}</span>
        <span>${esc(c.name)}</span>
      </button>
    `
    )
    .join('');
}

function populateCopilotCountryDropdown() {
  const sel = document.getElementById('copilot-country-scope');
  if (!sel) return;
  const prev = sel.value || 'all';
  sel.innerHTML =
    '<option value="all">All 12 Countries</option>' +
    state.countriesCatalog.map(c => `<option value="${esc(c.id)}">${esc(c.flag)} ${esc(c.name)}</option>`).join('');
  sel.value = prev;
}

function filterCountries(region, btnEl) {
  state.regionFilter = region;
  document.querySelectorAll('#tab-countries .prov-btn').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  renderCountriesGrid();
}

function getMediaForCountry(countryId) {
  if (window.JapaUtils?.getCountryMedia) {
    return window.JapaUtils.getCountryMedia(countryId);
  }
  return {
    src: '/static/images/hero-global-mobility.webp?v=7',
    alt: 'Global immigration destination skyline',
    focal: 'center',
  };
}

function renderDestinationShowcase() {
  const rail = document.getElementById('landing-destination-showcase');
  if (!rail) return;

  const featuredIds = window.JapaUtils?.FEATURED_SHOWCASE_IDS || [
    'canada',
    'uk',
    'usa',
    'germany',
    'spain',
    'sweden',
    'brazil',
  ];
  const byId = new Map(state.countriesCatalog.map(c => [c.id, c]));
  const items = featuredIds.map(id => byId.get(id)).filter(Boolean);
  const displayList = items.length ? items : state.countriesCatalog.slice(0, 7);

  rail.innerHTML = displayList
    .map(c => {
      const media = getMediaForCountry(c.id);
      const topPathway = (c.pathway_names || [])[0] || c.authority || '';
      return `
        <button type="button" class="showcase-card" onclick="openCountryHub('${esc(c.id)}')" aria-label="Explore ${esc(c.name)} immigration hub">
          <img src="${esc(media.src)}"
               alt="${esc(media.alt)}"
               width="800"
               height="480"
               loading="lazy"
               decoding="async"
               class="showcase-card-img"
               style="object-position:${esc(media.focal || 'center')};">
          <div class="showcase-card-scrim" aria-hidden="true"></div>
          <div class="showcase-card-top">
            <span class="showcase-badge">${esc(c.region)}</span>
            <span class="showcase-badge showcase-badge-emerald tabular">${Number(c.pathway_count)} pathways</span>
          </div>
          <div class="showcase-card-bottom">
            <div class="showcase-card-name">${esc(c.flag)} ${esc(c.name)}</div>
            <div class="showcase-card-sub">${esc(topPathway)}</div>
          </div>
        </button>
      `;
    })
    .join('');
}

function renderCountriesGrid() {
  const grid = document.getElementById('countries-grid');
  if (!grid) return;

  const q = strVal('country-search').toLowerCase();
  const reg = state.regionFilter.toLowerCase();

  const filtered = state.countriesCatalog.filter(c => {
    if (reg !== 'all' && c.region.toLowerCase() !== reg) return false;
    if (q) {
      const hay = [c.name, c.code, c.region, c.authority, c.summary, ...(c.pathway_names || [])].join(' ').toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  if (!filtered.length) {
    grid.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:32px; color:var(--ink-subtle);">No countries match your filter.</div>';
    return;
  }

  grid.innerHTML = filtered
    .map(c => {
      const media = getMediaForCountry(c.id);
      const chips = (c.pathway_names || [])
        .slice(0, 3)
        .map(name => `<span class="tag">${esc(name)}</span>`)
        .join('');
      const extraCount = (c.pathway_names || []).length > 3 ? `<span class="tag">+${c.pathway_names.length - 3} more</span>` : '';
      return `
        <article class="country-card">
          <div class="country-card-media" onclick="openCountryHub('${esc(c.id)}')" role="button" tabindex="0"
               onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openCountryHub('${esc(c.id)}');}"
               aria-label="Open ${esc(c.name)} country hub">
            <img src="${esc(media.src)}"
                 alt="${esc(media.alt)}"
                 width="800"
                 height="480"
                 loading="lazy"
                 decoding="async"
                 class="country-card-img"
                 style="object-position:${esc(media.focal || 'center')};">
            <div class="country-card-scrim" aria-hidden="true"></div>
            <div class="country-card-badges">
              <span class="showcase-badge">${esc(c.region)}</span>
              <span class="showcase-badge showcase-badge-emerald tabular">${Number(c.pathway_count)} pathways</span>
            </div>
            <div class="country-card-title-wrap">
              <h3 class="country-card-title">${esc(c.flag)} ${esc(c.name)}</h3>
              <div class="country-card-auth">${esc(c.authority)}</div>
            </div>
          </div>

          <div class="country-card-body">
            <div>
              <p class="country-card-summary">${esc(c.summary)}</p>
              <div class="tag-row">${chips}${extraCount}</div>
            </div>

            <div class="country-card-actions">
              <button type="button" class="btn btn-primary btn-sm" style="flex:1;" onclick="openCountryHub('${esc(c.id)}')">
                Open Country Hub
              </button>
              <a class="btn btn-sm" href="${esc(c.official_portal)}" target="_blank" rel="noopener">Official Site ↗</a>
            </div>
          </div>
        </article>
      `;
    })
    .join('');
}

async function openCountryHub(countryId, pathwayId = null) {
  switchTab('tab-countries');
  state.activeCountryId = countryId;

  let country = state.countryCache[countryId];
  if (!country) {
    try {
      const res = await fetch(`/api/countries/${encodeURIComponent(countryId)}`);
      if (!res.ok) throw new Error('Country unavailable');
      const data = await res.json();
      country = data.country;
      state.countryCache[countryId] = country;
    } catch (err) {
      showToast('Failed to load country hub details.', true);
      return;
    }
  }

  const pathways = country.pathways || [];
  state.activePathwayId =
    pathwayId && pathways.some(p => p.id === pathwayId) ? pathwayId : (pathways[0]?.id || '');

  renderCountryHubWorkspace(country);
  const ws = document.getElementById('country-hub-workspace');
  if (ws) ws.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function selectCountryPathway(pathwayId) {
  state.activePathwayId = pathwayId;
  const country = state.countryCache[state.activeCountryId];
  if (country) renderCountryHubWorkspace(country);
}

function renderCountryHubWorkspace(country) {
  const ws = document.getElementById('country-hub-workspace');
  if (!ws || !country) return;
  ws.classList.remove('hidden');

  const pathways = country.pathways || [];
  const activePathway = pathways.find(p => p.id === state.activePathwayId) || pathways[0];
  if (!activePathway) return;

  const extraLinksHtml = (country.extra_official_links || [])
    .map(l => `<a class="btn btn-sm" href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)} ↗</a>`)
    .join('');

  const watchoutsHtml = (country.applicant_notes || [])
    .map(n => `<li style="margin-top:4px;">${esc(n)}</li>`)
    .join('');

  const liveSnaps = country.live_snapshots || [];
  const lastVerified = country.last_verified_at
    ? `Verified ${esc(country.last_verified_at.replace('T', ' ').replace('+00:00', ' UTC'))}`
    : 'Awaiting live portal refresh';

  const snapsHtml = liveSnaps.length
    ? liveSnaps
        .map(
          s => `
          <div class="live-snapshot-item">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;">
              <a href="${esc(s.url)}" target="_blank" rel="noopener" style="font-size:12.5px; font-weight:700;">${esc(s.title)} ↗</a>
              <span class="pill pill-emerald" style="font-size:10.5px;">LIVE · ${esc((s.fetched_at || '').slice(0, 10))}</span>
            </div>
            ${s.alert_text ? `<div style="font-size:12px; color:var(--amber); margin-top:4px;"><strong>Notice:</strong> ${esc(s.alert_text)}</div>` : ''}
            ${s.excerpt ? `<div style="font-size:12px; color:var(--ink-muted); margin-top:4px;">${esc(s.excerpt)}</div>` : ''}
          </div>
        `
        )
        .join('')
    : `<div style="font-size:12px; color:var(--ink-muted);">Click <strong>Fetch Live Update</strong> to pull current verbatim requirements directly from ${esc(country.authority)} now.</div>`;

  const pathwayBtns = pathways
    .map(
      p => `
      <button type="button" class="pathway-tab-btn ${p.id === activePathway.id ? 'active' : ''}"
              onclick="selectCountryPathway('${esc(p.id)}')">
        ${esc(p.name)}
      </button>
    `
    )
    .join('');

  const stepsHtml = (activePathway.stages || [])
    .map((step, idx) => {
      const saved = state.globalChecklist[step.id] || {};
      const isDone = !!saved.completed;
      const note = saved.note || '';
      return `
        <div class="checklist-row ${isDone ? 'is-done' : ''}">
          <input type="checkbox" ${isDone ? 'checked' : ''}
                 onchange="toggleGlobalStep('${esc(country.id)}', '${esc(activePathway.id)}', '${esc(step.id)}', '${esc(step.title)}', this.checked)">
          <div class="checklist-content">
            <div class="checklist-title">Step ${idx + 1}: ${esc(step.title)}</div>
            <div class="checklist-desc">${esc(step.description)}</div>
            <div class="checklist-actions">
              <a class="btn btn-sm" href="${esc(step.url)}" target="_blank" rel="noopener">Official Government Guide ↗</a>
              <button type="button" class="btn btn-ghost btn-sm" onclick="toggleGlobalNote('${esc(step.id)}')">
                ${note ? 'Edit Note' : '+ Note'}
              </button>
            </div>
            <div id="gnote-box-${esc(step.id)}" class="note-box ${note ? '' : 'hidden'}">
              <input type="text" id="gnote-in-${esc(step.id)}" class="input" style="font-size:12px; padding:6px 10px;"
                     value="${esc(note)}" placeholder="Add document date, reference number, or reminder...">
              <button type="button" class="btn btn-sm"
                      onclick="saveGlobalStepNote('${esc(country.id)}', '${esc(activePathway.id)}', '${esc(step.id)}', '${esc(step.title)}')">Save</button>
            </div>
          </div>
        </div>
      `;
    })
    .join('');

  const deepRcipBtn = activePathway.has_deep_engine
    ? `<button type="button" class="btn btn-crimson btn-sm" onclick="switchTab('tab-rcip')">Open Interactive RCIP Toolkit →</button>`
    : '';

  const media = getMediaForCountry(country.id);
  ws.innerHTML = `
    <div class="card">
      <div class="hub-hero-banner">
        <img src="${esc(media.src)}"
             alt="${esc(media.alt)}"
             width="800"
             height="480"
             loading="lazy"
             decoding="async"
             class="hub-hero-img"
             style="object-position:${esc(media.focal || 'center')};">
        <div class="hub-hero-scrim" aria-hidden="true"></div>
        <div class="hub-hero-content">
          <div class="hub-hero-text">
            <span class="showcase-badge showcase-badge-emerald">${esc(country.flag)} ${esc(country.name)} · Official Country Hub</span>
            <h2 class="hub-hero-title">${esc(country.name)} — ${esc(country.authority)}</h2>
            <p class="hub-hero-desc">${esc(country.summary)}</p>
          </div>
          <div class="hub-hero-links">
            <a class="btn btn-primary btn-sm" href="${esc(country.official_portal)}" target="_blank" rel="noopener">Official Portal ↗</a>
            ${extraLinksHtml}
          </div>
        </div>
      </div>

      <div class="live-snapshot-box">
        <div class="live-snapshot-head">
          <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <span class="live-dot-pulse" aria-hidden="true"></span>
            <strong style="font-size:13px;">Live Official Portal Snapshot</strong>
            <span class="pill pill-emerald tabular" style="font-size:11px;">${lastVerified}</span>
          </div>
          <button type="button" class="btn btn-sm" id="btn-sync-country-${esc(country.id)}" onclick="syncSingleCountry('${esc(country.id)}')">
            Fetch Live Update
          </button>
        </div>
        ${snapsHtml}
      </div>

      <div class="watchout-box">
        <strong style="font-size:13px;">Official International Applicant Notes &amp; Key Requirements</strong>
        <ul style="font-size:12.5px; padding-left:18px; margin-top:4px; color:var(--ink);">${watchoutsHtml}</ul>
      </div>

      <div class="pathway-tabs">${pathwayBtns}</div>

      <div class="funds-card" style="margin-bottom:14px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap;">
          <div>
            <h3 style="font-size:16.5px; font-weight:700;">${esc(activePathway.name)}</h3>
            <p style="font-size:13px; color:var(--ink-muted); margin-top:4px;">${esc(activePathway.summary)}</p>
          </div>
          <div style="display:flex; gap:8px; flex-wrap:wrap;">
            ${deepRcipBtn}
            <button type="button" class="btn btn-sm" onclick="exportGlobalRoadmap('${esc(country.id)}', '${esc(activePathway.id)}')">Export Printable Roadmap</button>
            <a class="btn btn-primary btn-sm" href="${esc(activePathway.official_url)}" target="_blank" rel="noopener">Verify on Official Site ↗</a>
          </div>
        </div>
        <div style="display:flex; flex-wrap:wrap; gap:6px; margin-top:10px;">
          <span class="pill pill-blue">${esc(activePathway.category)}</span>
          <span class="pill pill-emerald">${esc(activePathway.leads_to_pr)}</span>
          <span class="pill ${activePathway.requires_job_offer ? 'pill-amber' : 'pill-emerald'}">${activePathway.requires_job_offer ? 'Requires Job Offer' : 'No Job Offer Needed Upfront'}</span>
          <span class="pill">${esc(activePathway.threshold_label)}</span>
        </div>
      </div>

      ${stepsHtml}
    </div>
  `;
}

function toggleGlobalNote(stepId) {
  const el = document.getElementById(`gnote-box-${stepId}`);
  if (el) el.classList.toggle('hidden');
}

function toggleGlobalStep(countryId, pathwayId, stepId, stepTitle, completed) {
  const prev = state.globalChecklist[stepId] || {};
  state.globalChecklist[stepId] = {
    country_id: countryId,
    pathway_id: pathwayId,
    step_id: stepId,
    title: stepTitle,
    completed: !!completed,
    note: prev.note || '',
  };
  persistBrowserState();
  updateGlobalCounters();
  const country = state.countryCache[countryId];
  if (country) renderCountryHubWorkspace(country);
  showToast(completed ? 'Roadmap step marked complete.' : 'Roadmap step marked incomplete.');
}

function saveGlobalStepNote(countryId, pathwayId, stepId, stepTitle) {
  const input = document.getElementById(`gnote-in-${stepId}`);
  const prev = state.globalChecklist[stepId] || {};
  state.globalChecklist[stepId] = {
    country_id: countryId,
    pathway_id: pathwayId,
    step_id: stepId,
    title: stepTitle,
    completed: !!prev.completed,
    note: (input?.value || '').trim(),
  };
  persistBrowserState();
  const country = state.countryCache[countryId];
  if (country) renderCountryHubWorkspace(country);
  showToast('Note saved.');
}

async function exportGlobalRoadmap(countryId, pathwayId) {
  const checked = {};
  const notes = {};
  for (const [k, v] of Object.entries(state.globalChecklist || {})) {
    if (v && v.pathway_id === pathwayId) {
      checked[k] = !!v.completed;
      if (v.note) notes[k] = v.note;
    }
  }
  try {
    const res = await fetch('/api/global/roadmap/export/html', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        country_id: countryId,
        pathway_id: pathwayId,
        applicant_name: state.profile?.name || 'JapaAI.ng Applicant',
        checked_steps: checked,
        notes,
      }),
    });
    if (!res.ok) throw new Error('Export failed');
    const htmlContent = await res.text();
    const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const win = window.open(url, '_blank', 'noopener');
    if (!win) {
      const a = document.createElement('a');
      a.href = url;
      a.download = `JapaAI_${countryId}_${pathwayId}.html`;
      a.click();
    }
    setTimeout(() => URL.revokeObjectURL(url), 15000);
  } catch (err) {
    showToast('Could not export roadmap.', true);
  }
}

// --------------------------------------------------------------------------
// Universal 12-Country Matcher
// --------------------------------------------------------------------------

function populateUniversalForm() {
  const u = state.universalProfile || {};
  setVal('gm-edu', u.education_level);
  setVal('gm-field', u.field);
  setVal('gm-exp', u.years_experience);
  setVal('gm-age', u.age);
  setVal('gm-eng', u.english_level);
  setVal('gm-fr', u.french_level || 'none');
  setVal('gm-de', u.german_level || 'none');
  setVal('gm-region', u.target_region || 'all');
  setVal('gm-budget', u.relocation_budget_usd);
  setVal('gm-remote', u.monthly_remote_income_usd);
  setChecked('gm-offer', u.has_foreign_job_offer);
}

function collectUniversalForm() {
  return {
    education_level: strVal('gm-edu'),
    field: strVal('gm-field'),
    years_experience: numOrNull('gm-exp') || 0,
    age: numOrNull('gm-age') || 0,
    english_level: strVal('gm-eng'),
    french_level: strVal('gm-fr') || 'none',
    german_level: strVal('gm-de') || 'none',
    target_region: strVal('gm-region') || 'all',
    relocation_budget_usd: numOrNull('gm-budget') || 0,
    monthly_remote_income_usd: numOrNull('gm-remote') || 0,
    has_foreign_job_offer: boolVal('gm-offer'),
  };
}

async function runGlobalMatcher() {
  state.universalProfile = collectUniversalForm();
  persistBrowserState();

  try {
    const res = await fetch('/api/global/match', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(state.universalProfile),
    });
    const data = await res.json();
    state.matcherResult = data;
    renderMatcherResults(data);
  } catch (err) {
    showToast('Failed to match across countries.', true);
  }
}

function renderMatcherResults(res) {
  const container = document.getElementById('global-matcher-results');
  if (!container) return;

  if (!res || res.status === 'INCOMPLETE') {
    container.innerHTML = `<div class="card"><p style="color:var(--ink-muted);">${esc(res?.message || 'Enter your background details above to see ranked country & pathway matches.')}</p></div>`;
    return;
  }

  const renderTier = (title, badgeClass, items) => {
    if (!items || !items.length) return '';
    const cards = items
      .map(m => {
        const whyHtml = (m.why_it_fits || []).map(w => `<li style="color:var(--emerald); margin-top:3px;">${esc(w)}</li>`).join('');
        const gapsHtml = (m.gaps_to_close || []).map(g => `<li style="color:var(--amber); margin-top:3px;">${esc(g)}</li>`).join('');
        const deepBtn = m.has_deep_engine
          ? `<button type="button" class="btn btn-crimson btn-sm" onclick="switchTab('tab-rcip')">RCIP Toolkit</button>`
          : '';
        return `
          <div class="match-card tier-${esc(m.fit_tier)}">
            <div>
              <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
                <div>
                  <span class="pill">${esc(m.flag)} ${esc(m.country_name)}</span>
                  <h4 style="font-size:15px; font-weight:700; margin-top:6px;">${esc(m.pathway_name)}</h4>
                </div>
                <span class="pill ${badgeClass} tabular">${m.score}/100</span>
              </div>
              <div style="font-size:11.5px; color:var(--ink-subtle); margin-top:5px;">${esc(m.leads_to_pr)}</div>
              <div style="font-size:11.5px; color:var(--ink-muted); margin-top:4px;"><strong>Thresholds:</strong> ${esc(m.threshold_label)}</div>
              <ul style="font-size:12px; padding-left:16px; margin-top:8px;">
                ${whyHtml}
                ${gapsHtml}
              </ul>
            </div>
            <div style="display:flex; gap:6px; flex-wrap:wrap; border-top:1px solid var(--border-subtle); padding-top:10px;">
              <button type="button" class="btn btn-primary btn-sm" onclick="openCountryHub('${esc(m.country_id)}', '${esc(m.pathway_id)}')">Open Roadmap →</button>
              ${deepBtn}
              <a class="btn btn-sm" href="${esc(m.official_url)}" target="_blank" rel="noopener">Official ↗</a>
            </div>
          </div>
        `;
      })
      .join('');

    return `
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">${esc(title)} (${items.length})</h3>
        </div>
        <div class="matcher-grid">${cards}</div>
      </div>
    `;
  };

  container.innerHTML =
    `<div class="card" style="padding:14px 18px;"><strong style="font-size:13.5px;">${esc(res.message)}</strong></div>` +
    renderTier('Strong Pathway Matches', 'pill-emerald', res.top_matches) +
    renderTier('Viable With a Sponsored Job Offer', 'pill-blue', res.viable_with_job_offer) +
    renderTier('Explore & Close Gaps', 'pill-amber', res.explore_and_prepare);
}

// --------------------------------------------------------------------------
// Tab 5: Saved Progress Across All Countries
// --------------------------------------------------------------------------

function renderSavedProgress() {
  const container = document.getElementById('saved-progress-container');
  if (!container) return;

  const grouped = {};
  for (const item of Object.values(state.globalChecklist || {})) {
    if (!item || (!item.completed && !item.note)) continue;
    const key = `${item.country_id}::${item.pathway_id}`;
    if (!grouped[key]) {
      grouped[key] = { country_id: item.country_id, pathway_id: item.pathway_id, done: 0, notes: 0 };
    }
    if (item.completed) grouped[key].done += 1;
    if (item.note) grouped[key].notes += 1;
  }

  const globalCards = Object.values(grouped)
    .map(g => {
      const country = state.countriesCatalog.find(c => c.id === g.country_id) || { name: g.country_id, flag: '🌍' };
      return `
        <div class="funds-card" style="display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap;">
          <div>
            <strong>${esc(country.flag)} ${esc(country.name)} — ${esc(g.pathway_id)}</strong>
            <div style="font-size:12px; color:var(--ink-muted);">${g.done} step(s) completed · ${g.notes} note(s)</div>
          </div>
          <div style="display:flex; gap:8px;">
            <button type="button" class="btn btn-primary btn-sm" onclick="openCountryHub('${esc(g.country_id)}', '${esc(g.pathway_id)}')">Resume Roadmap</button>
            <button type="button" class="btn btn-sm" onclick="exportGlobalRoadmap('${esc(g.country_id)}', '${esc(g.pathway_id)}')">Export</button>
          </div>
        </div>
      `;
    })
    .join('');

  const rcipDone = Object.values(state.progress || {}).filter(p => p && p.completed).length;
  const rcipScore = state.evaluation?.readiness_score ?? 0;
  const shortCount = Object.values(state.shortlists || {}).filter(s => s && s.shortlisted).length;

  container.innerHTML = `
    <div class="funds-card" style="display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; margin-bottom:12px;">
      <div>
        <strong>🇨🇦 Canada RCIP Roadmap &amp; Checklist</strong>
        <div style="font-size:12px; color:var(--ink-muted);">Readiness Score: ${rcipScore}% · ${rcipDone} RCIP checklist step(s) done · ${shortCount} community shortlist(s)</div>
      </div>
      <div style="display:flex; gap:8px;">
        <button type="button" class="btn btn-crimson btn-sm" onclick="switchTab('tab-rcip')">Open RCIP Toolkit</button>
        <button type="button" class="btn btn-sm" onclick="exportRoadmapReport()">Export RCIP Dossier</button>
      </div>
    </div>
    ${globalCards || '<p style="font-size:13px; color:var(--ink-subtle);">No country-hub steps checked off yet — open any of the 12 Country Hubs to start tracking your roadmap.</p>'}
  `;
}

// --------------------------------------------------------------------------
// Canada RCIP Toolkit (Full Interactive Verification)
// --------------------------------------------------------------------------

function setWizardStep(stepNum) {
  state.wizardStep = Math.max(1, Math.min(6, Number(stepNum) || 1));
  const showAll = !!document.getElementById('toggle-wizard-all')?.checked;
  if (showAll) return;

  document.querySelectorAll('#wizard-stepper .wiz-step-btn').forEach((btn, idx) => {
    btn.classList.toggle('active', idx + 1 === state.wizardStep);
  });
  document.querySelectorAll('#wizard-card .wizard-pane').forEach(pane => {
    pane.classList.toggle('active', Number(pane.dataset.step) === state.wizardStep);
  });
  const prevBtn = document.getElementById('wiz-prev-btn');
  const nextBtn = document.getElementById('wiz-next-btn');
  if (prevBtn) prevBtn.disabled = state.wizardStep <= 1;
  if (nextBtn) nextBtn.disabled = state.wizardStep >= 6;
}

function prevWizardStep() { setWizardStep(state.wizardStep - 1); }
function nextWizardStep() { setWizardStep(state.wizardStep + 1); }

function toggleWizardViewAll() {
  const showAll = !!document.getElementById('toggle-wizard-all')?.checked;
  const card = document.getElementById('wizard-card');
  const stepper = document.getElementById('wizard-stepper');
  const prevBtn = document.getElementById('wiz-prev-btn');
  const nextBtn = document.getElementById('wiz-next-btn');
  if (card) card.classList.toggle('wizard-all', showAll);
  if (stepper) stepper.classList.toggle('hidden', showAll);
  if (prevBtn) prevBtn.classList.toggle('hidden', showAll);
  if (nextBtn) nextBtn.classList.toggle('hidden', showAll);
  if (!showAll) setWizardStep(state.wizardStep);
}

async function recomputeRoadmapAndEvaluation() {
  try {
    const res = await fetch('/api/roadmap/compute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile: state.profile || {}, progress: state.progress || {} }),
    });
    const data = await res.json();
    state.roadmap = data.roadmap;
    state.evaluation = data.evaluation;
    state.officialForms = data.official_forms || [];

    updateHeroSummary();
    updateGlobalCounters();
    renderStageRail();
    renderRoadmap();
    renderEvaluationScorecard(state.evaluation);
    renderOfficialForms();
  } catch (err) {
    showToast('Failed to compute Canada RCIP roadmap.', true);
  }
}

function updateHeroSummary() {
  const ev = state.evaluation || {};
  const rm = state.roadmap || {};
  const score = Number(ev.readiness_score || 0);

  const scoreEl = document.getElementById('kpi-score');
  const heroRcip = document.getElementById('hero-rcip-score');
  const ringEl = document.getElementById('hero-donut-ring');
  const verdictEl = document.getElementById('kpi-verdict');
  const progEl = document.getElementById('kpi-progress');
  const progBar = document.getElementById('kpi-progress-bar');
  const trackEl = document.getElementById('kpi-track');
  const branchEl = document.getElementById('kpi-branch');
  const pagesEl = document.getElementById('kpi-pages');
  const shortEl = document.getElementById('kpi-shortlisted');
  const tabScoreBadge = document.getElementById('tab-badge-score');

  if (scoreEl) scoreEl.textContent = `${score}%`;
  if (heroRcip) heroRcip.textContent = `${score}%`;
  if (tabScoreBadge) tabScoreBadge.textContent = `${score}%`;
  if (ringEl) {
    const offset = DONUT_CIRCUMFERENCE * (1 - Math.max(0, Math.min(100, score)) / 100);
    ringEl.style.strokeDashoffset = String(offset.toFixed(2));
    ringEl.style.stroke = score >= 80 ? 'var(--emerald)' : (score >= 40 ? 'var(--amber)' : 'var(--crimson)');
  }
  if (verdictEl) verdictEl.textContent = ev.verdict || 'Profile incomplete';

  const done = rm.completed_items || 0;
  const total = rm.total_items || 0;
  const pct = rm.completion_percent || 0;
  if (progEl) progEl.textContent = `${done} / ${total} steps (${pct}%)`;
  if (progBar) progBar.style.width = `${pct}%`;

  const trackObj = ev.program_track || {};
  if (trackEl) trackEl.textContent = trackObj.track === 'pilot' ? 'Pilot (<= Dec 31, 2026)' : 'Permanent 2027';

  const ctx = ev.applicant_context || {};
  const branchParts = [
    ctx.location_branch === 'inside_canada' ? 'Inside Canada' : 'Outside Canada',
    ctx.funds_exempt ? 'Funds Exempt' : 'Funds Required',
  ];
  if (ctx.local_grad_exempt) branchParts.push('Local Grad Exempt');
  if (branchEl) branchEl.textContent = branchParts.join(' · ');

  if (pagesEl) pagesEl.textContent = `${state.sources.length} official pages`;
  const shortCount = Object.values(state.shortlists || {}).filter(s => s && s.shortlisted).length;
  if (shortEl) shortEl.textContent = `${shortCount} shortlisted`;
}

function renderStageRail() {
  const rail = document.getElementById('stage-rail');
  const rm = state.roadmap;
  if (!rail || !rm) return;

  const allActive = state.focusedStageId === null;
  let html = `<button type="button" class="rail-btn ${allActive ? 'active' : ''}" onclick="focusRoadmapStage(null)">All 6 Stages</button>`;
  const shortNames = ['Eligibility', 'Job Offer', 'Recommend', 'PR Portal', 'Work Permit', 'Settle'];

  for (const stage of rm.stages || []) {
    const isComplete = stage.active_count > 0 && stage.completed_count >= stage.active_count;
    const isFocused = state.focusedStageId === stage.stage_id;
    const shortTitle = shortNames[stage.order - 1] || `Stage ${stage.order}`;
    html += `
      <button type="button" class="rail-btn ${isFocused ? 'active' : ''} ${isComplete ? 'is-complete' : ''}"
              onclick="focusRoadmapStage('${esc(stage.stage_id)}')">
        <span class="rail-num">${isComplete ? '✓' : stage.order}</span>
        <span>${esc(shortTitle)} (${stage.completed_count}/${stage.active_count})</span>
      </button>
    `;
  }
  rail.innerHTML = html;
}

function focusRoadmapStage(stageId) {
  state.focusedStageId = stageId;
  renderStageRail();
  renderRoadmap();
}

function renderRoadmap() {
  const roadmap = state.roadmap;
  const evaluation = state.evaluation;
  if (!roadmap) return;

  const badgeWrap = document.getElementById('roadmap-branch-badges');
  const ctx = roadmap.applicant_context || {};
  const track = roadmap.program_track || {};
  if (badgeWrap) {
    const badges = [
      `<span class="pill ${track.track === 'pilot' ? 'pill-amber' : 'pill-red'}">${track.track === 'pilot' ? 'Pilot (<= Dec 31, 2026)' : 'Permanent Program (Jan 1, 2027)'}</span>`,
      `<span class="pill pill-blue">${ctx.location_branch === 'inside_canada' ? 'Inside Canada Branch' : 'Outside Canada Branch'}</span>`,
      `<span class="pill ${ctx.funds_exempt ? 'pill-emerald' : 'pill-amber'}">${ctx.funds_exempt ? 'Settlement Funds Exempt' : 'Proof of Funds Required'}</span>`,
    ];
    if (ctx.local_grad_exempt) badges.push('<span class="pill pill-emerald">Local Graduate Exempt</span>');
    badgeWrap.innerHTML = badges.join('');
  }

  const showAll = !!document.getElementById('toggle-show-all-steps')?.checked;
  const stagesEl = document.getElementById('roadmap-stages-container');
  if (stagesEl) {
    const stagesToRender = (roadmap.stages || []).filter(s => !state.focusedStageId || s.stage_id === state.focusedStageId);
    stagesEl.innerHTML = stagesToRender.map(stage => {
      const visibleItems = showAll ? stage.items : stage.items.filter(i => i.applicable);
      const itemsHtml = visibleItems.map(item => {
        const formsHtml = (item.forms || []).map(f => `<span class="form-chip">${esc(f)}</span>`).join('');
        const inactiveBadge = !item.applicable ? `<span class="pill">Inactive (${esc(item.applies_to)})</span>` : '';
        const noteText = item.notes || '';
        return `
          <div class="checklist-row ${item.completed ? 'is-done' : ''} ${!item.applicable ? 'is-inactive' : ''}">
            <input type="checkbox" ${item.completed ? 'checked' : ''}
                   onchange="toggleChecklistItem('${esc(item.id)}', '${esc(stage.stage_id)}', this.checked)">
            <div class="checklist-content">
              <div class="checklist-title">${esc(item.title)}</div>
              <div class="checklist-desc">${esc(item.description)}</div>
              <div class="checklist-actions">
                ${inactiveBadge}
                ${formsHtml}
                <a class="btn btn-sm" href="${esc(item.url)}" target="_blank" rel="noopener">Canada.ca Guide ↗</a>
                <button type="button" class="btn btn-ghost btn-sm" onclick="toggleTaskNoteBox('${esc(item.id)}')">${noteText ? 'Edit Note' : '+ Note'}</button>
              </div>
              <div id="note-box-${esc(item.id)}" class="note-box ${noteText ? '' : 'hidden'}">
                <input type="text" id="note-input-${esc(item.id)}" class="input" style="font-size:12px; padding:6px 10px;" value="${esc(noteText)}" placeholder="Add personal reminder...">
                <button type="button" class="btn btn-sm" onclick="saveTaskNote('${esc(item.id)}', '${esc(stage.stage_id)}')">Save</button>
              </div>
            </div>
          </div>
        `;
      }).join('');

      return `
        <div class="stage-block">
          <div class="stage-block-head">
            <h3 style="font-size:16px; font-weight:700;">${esc(stage.title)}</h3>
            <div style="display:flex; gap:8px; align-items:center;">
              <span class="pill pill-emerald tabular">${stage.completed_count} / ${stage.active_count}</span>
              <a class="btn btn-sm" href="${esc(stage.official_url)}" target="_blank" rel="noopener">Official Page ↗</a>
            </div>
          </div>
          <p style="font-size:13px; color:var(--ink-muted); margin-bottom:10px;">${esc(stage.summary)}</p>
          ${itemsHtml || '<p style="font-size:12.5px; color:var(--ink-subtle);">No active steps in this stage for your current branch.</p>'}
        </div>
      `;
    }).join('');
  }

  const planEl = document.getElementById('roadmap-action-plan');
  if (planEl && evaluation) {
    const actions = evaluation.action_plan || [];
    planEl.innerHTML = actions.length
      ? actions.map(a => `
          <div class="action-item priority-${esc(a.priority)}">
            <div style="font-weight:700; margin-bottom:2px;">[${esc(a.priority)}] ${esc(a.pillar)}</div>
            <div style="color:var(--ink-muted); margin-bottom:4px;">${esc(a.action)}</div>
            <a href="${esc(a.url)}" target="_blank" rel="noopener">Verify on Canada.ca ↗</a>
          </div>
        `).join('')
      : '<div class="pill pill-emerald">All 6 core eligibility pillars satisfied. Ready to submit PR Portal dossier.</div>';
  }
}

function toggleTaskNoteBox(itemId) {
  const box = document.getElementById(`note-box-${itemId}`);
  if (box) box.classList.toggle('hidden');
}

async function saveTaskNote(itemId, stageId) {
  const input = document.getElementById(`note-input-${itemId}`);
  const existing = state.progress[itemId] || {};
  await updateChecklistRecord(itemId, stageId, !!existing.completed, (input?.value || '').trim());
  showToast('RCIP milestone note saved.');
}

async function toggleChecklistItem(itemId, stageId, completed) {
  const existing = state.progress[itemId] || {};
  await updateChecklistRecord(itemId, stageId, completed, existing.notes || '');
  showToast(completed ? 'RCIP milestone completed.' : 'RCIP milestone marked incomplete.');
}

async function updateChecklistRecord(itemId, stageId, completed, notes) {
  state.progress[itemId] = { item_id: itemId, stage_id: stageId, completed: !!completed, notes: notes || '', target_date: '' };
  persistBrowserState();
  if (state.environment === 'local') {
    try {
      await fetch('/api/roadmap/progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: itemId, stage_id: stageId, completed: !!completed, notes: notes || '' }),
      });
    } catch (err) {}
  }
  await recomputeRoadmapAndEvaluation();
}

function renderOfficialForms() {
  const container = document.getElementById('official-forms-list');
  if (!container) return;
  container.innerHTML = (state.officialForms || []).map(f => `
    <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; padding:8px 10px; border-radius:8px; background:var(--bg-subtle); border:1px solid var(--border-subtle);">
      <div>
        <div style="font-size:12.5px; font-weight:700;">${esc(f.code)}</div>
        <div style="font-size:11.5px; color:var(--ink-muted);">${esc(f.title)}</div>
      </div>
      <a class="btn btn-sm" href="${esc(f.url)}" target="_blank" rel="noopener">Guide ↗</a>
    </div>
  `).join('');
}

function populateProfileForm() {
  const p = state.profile || {};
  setVal('f-name', p.name);
  setVal('f-email', p.email);
  setChecked('f-in-canada', p.currently_in_canada);
  setChecked('f-wp-exempt', p.in_canada_valid_work_permit);
  setChecked('f-has-spouse', p.has_spouse);
  setVal('f-family-size', p.family_size);
  setVal('f-funds-cad', p.available_funds_cad);
  setVal('f-target-noc', p.target_job_noc_code);
  setVal('f-target-teer', p.target_job_teer);
  setVal('f-target-title', p.target_job_title);
  setVal('f-target-community', p.target_community_id);
  setChecked('f-is-local-grad', p.is_local_graduate);
  setVal('f-grad-type', p.grad_program_type);
  setVal('f-grad-months-since', p.months_since_graduation);
  setVal('f-grad-lived-months', p.grad_lived_in_community_months);
  setChecked('f-grad-public', p.grad_public_institution_in_community);
  setChecked('f-grad-fulltime', p.grad_full_time);
  setChecked('f-grad-entire', p.grad_lived_entire_duration);
  setChecked('f-grad-lang-half', p.grad_over_half_language_study);
  setChecked('f-grad-dist-half', p.grad_over_half_distance_learning);
  setChecked('f-grad-return-sch', p.grad_return_home_scholarship);
  setVal('f-work-hours', p.paid_work_hours_last_3_years);
  setVal('f-exp-teer', p.experience_teer);
  setVal('f-exp-noc', p.experience_noc_code);
  setChecked('f-unpaid-self', p.work_was_self_employed_or_unpaid);
  setVal('f-lang-test', p.language_test_type);
  setVal('f-lang-age', p.language_test_age_months);
  setVal('f-lang-r', p.lang_reading);
  setVal('f-lang-w', p.lang_writing);
  setVal('f-lang-l', p.lang_listening);
  setVal('f-lang-s', p.lang_speaking);
  setVal('f-edu-origin', p.education_origin);
  setVal('f-edu-level', p.education_level);
  setChecked('f-has-eca', p.has_eca);
  setVal('f-eca-org', p.eca_organization);
  setVal('f-eca-age', p.eca_age_years);
  setChecked('f-has-offer', p.has_job_offer);
  setChecked('f-offer-designated', p.offer_from_designated_employer);
  setChecked('f-offer-ft', p.offer_full_time_30h);
  setChecked('f-offer-nonseasonal', p.offer_non_seasonal);
  setChecked('f-offer-indet', p.offer_indeterminate);
  setChecked('f-offer-inside', p.offer_inside_community);
  setChecked('f-has-rec', p.has_community_recommendation);
  setVal('f-rec-date', p.recommendation_date);

  toggleLocalGradBox();
  toggleECABox();
  toggleOfferChecks();
  toggleRecDate();
  updateLiveFundsCalc();
  updateLiveCLB();
}

function setVal(id, val) { const el = document.getElementById(id); if (el && val !== null && val !== undefined) el.value = val; }
function setChecked(id, val) { const el = document.getElementById(id); if (el) el.checked = !!val; }
function numOrNull(id) { const v = document.getElementById(id)?.value; if (v === '' || v === null || v === undefined) return null; const n = Number(v); return Number.isFinite(n) ? n : null; }
function intOrNull(id) { const n = numOrNull(id); return n === null ? null : Math.trunc(n); }
function strVal(id) { return (document.getElementById(id)?.value || '').trim(); }
function boolVal(id) { return !!document.getElementById(id)?.checked; }

function collectProfileFromForm() {
  return {
    name: strVal('f-name'),
    email: strVal('f-email'),
    currently_in_canada: boolVal('f-in-canada'),
    in_canada_valid_work_permit: boolVal('f-wp-exempt'),
    has_spouse: boolVal('f-has-spouse'),
    family_size: intOrNull('f-family-size'),
    available_funds_cad: numOrNull('f-funds-cad'),
    target_community_id: strVal('f-target-community'),
    target_job_noc_code: strVal('f-target-noc'),
    target_job_teer: intOrNull('f-target-teer'),
    target_job_title: strVal('f-target-title'),
    is_local_graduate: boolVal('f-is-local-grad'),
    grad_program_type: strVal('f-grad-type'),
    grad_public_institution_in_community: boolVal('f-grad-public'),
    grad_full_time: boolVal('f-grad-fulltime'),
    months_since_graduation: numOrNull('f-grad-months-since'),
    grad_lived_in_community_months: numOrNull('f-grad-lived-months'),
    grad_lived_entire_duration: boolVal('f-grad-entire'),
    grad_over_half_language_study: boolVal('f-grad-lang-half'),
    grad_over_half_distance_learning: boolVal('f-grad-dist-half'),
    grad_return_home_scholarship: boolVal('f-grad-return-sch'),
    paid_work_hours_last_3_years: numOrNull('f-work-hours'),
    experience_teer: intOrNull('f-exp-teer'),
    experience_noc_code: strVal('f-exp-noc'),
    work_was_self_employed_or_unpaid: boolVal('f-unpaid-self'),
    language_test_type: strVal('f-lang-test'),
    language_test_age_months: numOrNull('f-lang-age'),
    lang_reading: numOrNull('f-lang-r'),
    lang_writing: numOrNull('f-lang-w'),
    lang_listening: numOrNull('f-lang-l'),
    lang_speaking: numOrNull('f-lang-s'),
    education_origin: strVal('f-edu-origin'),
    education_level: strVal('f-edu-level'),
    has_eca: boolVal('f-has-eca'),
    eca_organization: strVal('f-eca-org'),
    eca_age_years: numOrNull('f-eca-age'),
    has_job_offer: boolVal('f-has-offer'),
    offer_from_designated_employer: boolVal('f-offer-designated'),
    offer_full_time_30h: boolVal('f-offer-ft'),
    offer_non_seasonal: boolVal('f-offer-nonseasonal'),
    offer_indeterminate: boolVal('f-offer-indet'),
    offer_inside_community: boolVal('f-offer-inside'),
    has_community_recommendation: boolVal('f-has-rec'),
    recommendation_date: strVal('f-rec-date'),
    detected_skills: state.profile.detected_skills || [],
    experience_summary: state.profile.experience_summary || '',
  };
}

async function saveAndEvaluateProfile() {
  state.profile = collectProfileFromForm();
  persistBrowserState();
  if (state.environment === 'local') {
    try {
      await fetch('/api/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(state.profile),
      });
    } catch (err) {}
  }
  await recomputeRoadmapAndEvaluation();
  showToast('RCIP profile saved and readiness recalculated.');
}

function renderEvaluationScorecard(evaluation) {
  if (!evaluation) return;
  const verdictEl = document.getElementById('eval-verdict-line');
  const pillEl = document.getElementById('eval-score-pill');
  const gridEl = document.getElementById('pillars-scorecard');

  if (verdictEl) verdictEl.textContent = evaluation.verdict;
  if (pillEl) {
    pillEl.textContent = `${evaluation.readiness_score} / 100 (${evaluation.overall_status})`;
    pillEl.className = `pill tabular ${evaluation.readiness_score >= 80 ? 'pill-emerald' : (evaluation.readiness_score >= 40 ? 'pill-amber' : 'pill-red')}`;
  }

  if (gridEl) {
    gridEl.innerHTML = (evaluation.pillars || []).map(p => {
      const statusClass = (p.status === 'PASS' || p.status === 'EXEMPT')
        ? 'pill-emerald'
        : (p.status === 'BLOCKED' ? 'pill-red' : (p.status === 'ACTION_REQUIRED' ? 'pill-amber' : 'pill-blue'));
      const gapsHtml = (p.gaps || []).map(g => `<li style="color:var(--crimson); margin-top:3px;">${esc(g)}</li>`).join('');
      const detailsHtml = (p.details || []).map(d => `<li style="color:var(--ink-muted); margin-top:3px;">${esc(d)}</li>`).join('');
      return `
        <div class="pillar-tile">
          <div class="pillar-head">
            <strong style="font-size:13px;">${esc(p.title)}</strong>
            <span class="pill ${statusClass}">${esc(p.status)}</span>
          </div>
          <div class="tabular" style="font-size:13px; font-weight:700;">${p.score} / ${p.max_score} pts</div>
          <p style="font-size:12px; color:var(--ink-muted); margin-top:5px;">${esc(p.summary)}</p>
          <ul style="font-size:11.5px; padding-left:16px; margin-top:5px;">${detailsHtml}${gapsHtml}</ul>
          <div style="margin-top:8px;"><a style="font-size:11.5px;" href="${esc(p.url)}" target="_blank" rel="noopener">Canada.ca Rules ↗</a></div>
        </div>
      `;
    }).join('');
  }
}

function toggleLocalGradBox() { const b = document.getElementById('local-grad-box'); if (b) b.classList.toggle('hidden', !boolVal('f-is-local-grad')); }
function toggleECABox() { const b = document.getElementById('eca-fields-box'); if (b) b.classList.toggle('hidden', strVal('f-edu-origin') === 'canada'); }
function toggleOfferChecks() { const b = document.getElementById('offer-checks-box'); if (b) b.classList.toggle('hidden', !boolVal('f-has-offer')); }
function toggleRecDate() { const b = document.getElementById('rec-date-box'); if (b) b.classList.toggle('hidden', !boolVal('f-has-rec')); }

async function updateLiveFundsCalc() {
  const readout = document.getElementById('live-funds-readout');
  const bar = document.getElementById('live-funds-bar');
  if (!readout) return;
  const wpExempt = boolVal('f-wp-exempt');
  const size = Math.max(1, intOrNull('f-family-size') || 1);
  const avail = numOrNull('f-funds-cad') || 0;
  try {
    const res = await fetch(`/api/tools/funds?family_size=${size}&in_canada_valid_work_permit=${wpExempt}`);
    const data = await res.json();
    if (wpExempt) {
      readout.className = 'pill pill-emerald tabular';
      readout.textContent = 'Exempt ($0 CAD proof needed — valid work permit)';
      if (bar) bar.style.width = '100%';
    } else {
      const req = Number(data.required_cad || 10507);
      if (bar) bar.style.width = `${Math.min(100, Math.round((avail / req) * 100))}%`;
      if (avail >= req) {
        readout.className = 'pill pill-emerald tabular';
        readout.textContent = `Meets minimum CAD $${req.toLocaleString()} (Family size ${size})`;
      } else {
        readout.className = 'pill pill-amber tabular';
        readout.textContent = `Family size ${size} needs CAD $${req.toLocaleString()} (Shortfall: $${(req - avail).toLocaleString()})`;
      }
    }
  } catch (err) {}
}

async function updateLiveCLB() {
  const readout = document.getElementById('live-clb-readout');
  const cards = document.getElementById('live-clb-cards');
  if (!readout) return;
  const testType = strVal('f-lang-test');
  const r = numOrNull('f-lang-r');
  const w = numOrNull('f-lang-w');
  const l = numOrNull('f-lang-l');
  const s = numOrNull('f-lang-s');
  if (!testType || r === null || w === null || l === null || s === null) {
    readout.className = 'pill pill-blue';
    readout.textContent = 'Enter test & all 4 scores';
    if (cards) cards.innerHTML = '';
    return;
  }
  try {
    const res = await fetch('/api/tools/clb-convert', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ test_type: testType, reading: r, writing: w, listening: l, speaking: s }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error('Error');
    const c = data.conversion;
    const p = c.per_skill_clb;
    readout.className = `pill tabular ${c.overall_clb >= 5 ? 'pill-emerald' : (c.overall_clb >= 4 ? 'pill-amber' : 'pill-red')}`;
    readout.textContent = `Governing CLB/NCLC: ${c.overall_clb}`;
    if (cards) {
      cards.innerHTML = ['reading', 'writing', 'listening', 'speaking'].map(k => {
        const lvl = p[k] || 0;
        const isLowest = lvl === c.overall_clb;
        return `
          <div class="clb-mini-card ${isLowest ? 'is-lowest' : ''}">
            <div style="font-size:11px; color:var(--ink-subtle); font-weight:600; text-transform:capitalize;">${esc(k)}</div>
            <div class="tabular" style="font-size:18px; font-weight:800; margin-top:2px;">CLB ${lvl}</div>
            ${isLowest ? '<div style="font-size:10px; font-weight:700; color:var(--amber);">Governs</div>' : ''}
          </div>
        `;
      }).join('');
    }
  } catch (err) {
    readout.className = 'pill pill-red';
    readout.textContent = 'Check test scores';
    if (cards) cards.innerHTML = '';
  }
}

async function searchNocCatalog() {
  const q = strVal('noc-quick-search');
  const container = document.getElementById('noc-search-results');
  if (!container) return;
  if (!q) { container.innerHTML = ''; return; }
  try {
    const res = await fetch(`/api/tools/noc-search?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    container.innerHTML = (data.results || []).slice(0, 6).map(item => `
      <button type="button" class="prompt-chip" onclick="applyNocChoice('${esc(item.noc)}', ${Number(item.teer)}, '${esc(item.title)}')">
        NOC ${esc(item.noc)} (TEER ${Number(item.teer)}) — ${esc(item.title)}
      </button>
    `).join('');
  } catch (err) { container.innerHTML = ''; }
}

function applyNocChoice(noc, teer, title) {
  setVal('f-target-noc', noc);
  setVal('f-target-teer', String(teer));
  setVal('f-target-title', title);
  showToast(`Applied NOC ${noc} (TEER ${teer}) to target occupation.`);
}

function setupResumeDropzone() {
  const dz = document.getElementById('resume-dropzone');
  if (!dz) return;
  dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('dragover'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
  dz.addEventListener('drop', e => {
    e.preventDefault();
    dz.classList.remove('dragover');
    if (e.dataTransfer?.files?.length) handleResumeFileUpload(e.dataTransfer.files[0]);
  });
}

function applyParsedResumeHints(parsed) {
  if (!parsed) return;
  const p = { ...(state.profile || {}) };
  if (parsed.name && !p.name) p.name = parsed.name;
  if (parsed.email && !p.email) p.email = parsed.email;
  if (parsed.detected_skills?.length) p.detected_skills = parsed.detected_skills;
  if (parsed.experience_summary) p.experience_summary = parsed.experience_summary;
  if (parsed.education_level && !p.education_level) p.education_level = parsed.education_level;
  if (parsed.suggested_nocs?.length && !p.target_job_noc_code) {
    p.target_job_noc_code = parsed.suggested_nocs[0].noc;
    p.target_job_teer = parsed.suggested_nocs[0].teer;
    p.target_job_title = parsed.suggested_nocs[0].title;
  }
  state.profile = p;
  persistBrowserState();
}

async function handleResumeFileUpload(file) {
  if (!file) return;
  if (file.size > MAX_UPLOAD_BYTES) {
    showToast('File exceeds 4.2 MB limit. Please upload a smaller resume or paste text.', true);
    return;
  }
  const form = new FormData();
  form.append('file', file);
  try {
    const res = await fetch('/api/resume/upload', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Upload failed');
    applyParsedResumeHints(data.parsed);
    renderResumeSuggestions(data.parsed);
    populateProfileForm();
    await recomputeRoadmapAndEvaluation();
    showToast(`Parsed ${file.name} and detected NOC suggestions.`);
  } catch (err) {
    showToast(err.message || 'Failed to parse resume file.', true);
  }
}

async function handleResumePaste() {
  const txt = document.getElementById('resume-paste-text')?.value.trim();
  if (!txt) { showToast('Paste your resume text first.', true); return; }
  try {
    const res = await fetch('/api/resume/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume_text: txt }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Parse failed');
    applyParsedResumeHints(data.parsed);
    renderResumeSuggestions(data.parsed);
    populateProfileForm();
    await recomputeRoadmapAndEvaluation();
    showToast('Resume text analyzed.');
  } catch (err) {
    showToast('Failed to parse pasted resume.', true);
  }
}

function renderResumeSuggestions(parsed) {
  const box = document.getElementById('resume-suggestions-box');
  if (!box || !parsed) return;
  box.classList.remove('hidden');
  const skillsHtml = (parsed.detected_skills || []).map(s => `<span class="tag">${esc(s)}</span>`).join('') || '<span style="color:var(--ink-subtle); font-size:12px;">None matched</span>';
  const nocsHtml = (parsed.suggested_nocs || []).map(n => `
    <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; margin-top:7px;">
      <span style="font-size:12.5px;"><strong>NOC ${esc(n.noc)} (TEER ${Number(n.teer)})</strong> — ${esc(n.title)}</span>
      <button type="button" class="btn btn-sm" onclick="applyNocChoice('${esc(n.noc)}', ${Number(n.teer)}, '${esc(n.title)}')">Use as Target</button>
    </div>
  `).join('') || '<div style="font-size:12.5px; color:var(--ink-subtle); margin-top:4px;">No automatic NOC match — search below.</div>';

  box.innerHTML = `
    <div style="font-size:13px; font-weight:700; margin-bottom:6px;">Extracted Resume Signals</div>
    <div class="tag-row" style="margin-bottom:8px;">${skillsHtml}</div>
    <div style="font-size:12px; color:var(--ink-muted);">Top Suggested NOC 2021 Matches:</div>
    ${nocsHtml}
  `;
}

// --------------------------------------------------------------------------
// 14 RCIP Communities
// --------------------------------------------------------------------------

function filterCommunities(prov, btnEl) {
  state.provinceFilter = prov;
  document.querySelectorAll('#rcip-sub-communities .prov-btn').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  renderCommunities();
}

async function loadCommunities() {
  try {
    const res = await fetch('/api/communities');
    const data = await res.json();
    state.communitiesCatalog = data.communities || [];
    renderCommunities();
    populateCommunitySelect();
  } catch (err) {}
}

function populateCommunitySelect() {
  const sel = document.getElementById('f-target-community');
  if (!sel || !state.communitiesCatalog.length) return;
  const current = state.profile?.target_community_id || sel.value || '';
  sel.innerHTML = '<option value="">Select community...</option>' +
    state.communitiesCatalog.map(c => `<option value="${esc(c.id)}">${esc(c.name)}, ${esc(c.province_code)}</option>`).join('');
  if (current) sel.value = current;
}

function renderCommunities() {
  const grid = document.getElementById('communities-grid');
  if (!grid) return;
  const q = strVal('comm-search').toLowerCase();
  const prov = state.provinceFilter.toLowerCase();

  const merged = state.communitiesCatalog.map(c => {
    const sl = state.shortlists[c.id] || {};
    return { ...c, shortlisted: !!sl.shortlisted, notes: sl.notes || '', employers_contacted: Number(sl.employers_contacted || 0) };
  });

  const filtered = merged.filter(c => {
    if (prov === 'shortlisted' && !c.shortlisted) return false;
    if (prov !== 'all' && prov !== 'shortlisted') {
      if (prov !== c.province.toLowerCase() && prov !== c.province_code.toLowerCase()) return false;
    }
    if (q) {
      const hay = [c.name, c.province, c.edo_name, ...(c.key_sectors || []), ...(c.local_institutions || [])].join(' ').toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  if (!filtered.length) {
    grid.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:32px; color:var(--ink-subtle);">No participating communities match that filter.</div>';
    return;
  }

  grid.innerHTML = filtered.map(c => {
    const sectors = (c.key_sectors || []).map(s => `<span class="tag">${esc(s)}</span>`).join('');
    const insts = (c.local_institutions || []).join(', ');
    return `
      <div class="comm-card ${c.shortlisted ? 'shortlisted' : ''}">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
            <div>
              <span class="pill" style="margin-bottom:6px;">${esc(c.province)}</span>
              <h3 style="font-size:16px; font-weight:700;">${esc(c.name)}</h3>
              <div style="font-size:12px; color:var(--ink-muted);">${esc(c.edo_name)}</div>
            </div>
            <button type="button" class="btn btn-sm ${c.shortlisted ? 'btn-emerald' : ''}" onclick="updateCommunityState('${esc(c.id)}', ${!c.shortlisted}, ${c.employers_contacted})">
              ${c.shortlisted ? 'Shortlisted' : 'Shortlist'}
            </button>
          </div>
          <div class="tag-row" style="margin:10px 0;">${sectors}</div>
          <div style="font-size:12px; color:var(--ink-muted); margin-bottom:6px;"><strong>Local Schools:</strong> ${esc(insts)}</div>
          <div style="font-size:11.5px; color:var(--ink-subtle);">${esc(c.verification_note)}</div>
        </div>
        <div style="border-top:1px solid var(--border-subtle); padding-top:10px; display:flex; flex-direction:column; gap:8px;">
          <div style="display:flex; justify-content:space-between; align-items:center; font-size:12px;">
            <span>Employers Contacted: <strong class="tabular">${c.employers_contacted}</strong></span>
            <div style="display:flex; gap:4px;">
              <button type="button" class="btn btn-sm" onclick="updateCommunityState('${esc(c.id)}', ${c.shortlisted}, ${Math.max(0, c.employers_contacted - 1)})">-</button>
              <button type="button" class="btn btn-sm" onclick="updateCommunityState('${esc(c.id)}', true, ${c.employers_contacted + 1})">+</button>
            </div>
          </div>
          <a class="btn btn-primary btn-sm" href="${esc(c.official_url)}" target="_blank" rel="noopener">Visit Official EDO Portal ↗</a>
        </div>
      </div>
    `;
  }).join('');
}

async function updateCommunityState(communityId, shortlisted, employersContacted) {
  const prev = state.shortlists[communityId] || {};
  state.shortlists[communityId] = {
    community_id: communityId,
    shortlisted: !!shortlisted,
    notes: prev.notes || '',
    employers_contacted: Math.max(0, Number(employersContacted || 0)),
  };
  persistBrowserState();
  renderCommunities();
  updateHeroSummary();
  if (state.environment === 'local') {
    try {
      await fetch('/api/communities/shortlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(state.shortlists[communityId]),
      });
    } catch (err) {}
  }
  showToast('Community tracker updated.');
}

// --------------------------------------------------------------------------
// Real-Time Official Gov Sync, Sources Registry, RAG Copilot & RCIP Export
// --------------------------------------------------------------------------

function updateHeroSyncStatus(lastSyncedAt, liveCount) {
  const el = document.getElementById('hero-sync-status');
  if (!el) return;
  if (window.JapaUtils?.resolveHeroSyncStatusText) {
    el.textContent = window.JapaUtils.resolveHeroSyncStatusText(lastSyncedAt, liveCount);
    return;
  }
  if (lastSyncedAt) {
    const cleanTs = String(lastSyncedAt).replace('T', ' ').replace('+00:00', ' UTC');
    el.textContent = `Direct official portals · ${liveCount || 'Live'} live snapshots verified (${cleanTs})`;
  } else {
    el.textContent = 'Direct official sources · No additions or middlemen · Updated in real time';
  }
}

async function maybeAutoRefreshRealTime(healthData) {
  try {
    if (sessionStorage.getItem('japaai_auto_synced') === '1') return;
    if (healthData && Number(healthData.live_global_pages || 0) > 0) return;
    sessionStorage.setItem('japaai_auto_synced', '1');
    const res = await fetch('/api/sync-sources', { method: 'POST' });
    if (!res.ok) return;
    const data = await res.json();
    state.countryCache = {};
    await loadSources();
    updateHeroSyncStatus(data.synced_at, data.live_global_pages);
  } catch (err) {
    // Non-blocking background refresh
  }
}

async function syncSingleCountry(countryId) {
  const btn = document.getElementById(`btn-sync-country-${countryId}`);
  if (btn) { btn.disabled = true; btn.textContent = 'Fetching live...'; }
  try {
    const res = await fetch(`/api/sync-sources?country_id=${encodeURIComponent(countryId)}`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error('Sync failed');
    delete state.countryCache[countryId];
    await openCountryHub(countryId, state.activePathwayId);
    await loadSources();
    updateHeroSyncStatus(data.synced_at, data.live_global_pages);
    if ((data.live_fetched || 0) > 0) {
      showToast(`Live official update fetched (${data.live_fetched} portal page(s) verified).`);
    } else {
      showToast('Official portal link verified; automated scrape restricted by remote site.');
    }
  } catch (err) {
    showToast('Could not reach live official portal right now.', true);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Fetch Live Update'; }
  }
}

async function triggerSourcesSync() {
  const btn = document.getElementById('btn-sync-sources');
  const origHtml = btn ? btn.innerHTML : '';
  if (btn) { btn.disabled = true; btn.textContent = 'Refreshing...'; }
  try {
    const res = await fetch('/api/sync-sources', { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error('Refresh failed');
    state.countryCache = {};
    if (state.activeCountryId && !document.getElementById('country-hub-workspace')?.classList.contains('hidden')) {
      await openCountryHub(state.activeCountryId, state.activePathwayId);
    }
    await loadSources();
    updateHeroSummary();
    updateHeroSyncStatus(data.synced_at, data.live_global_pages);
    showToast(`Real-time official sync complete: ${data.live_fetched || 0} live fetches, ${data.total_indexed} indexed pages.`);
  } catch (err) {
    showToast('Could not refresh official sources right now.', true);
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = origHtml || 'Refresh Gov Data'; }
  }
}
window.triggerCanadaSync = triggerSourcesSync;

async function loadSources() {
  try {
    const res = await fetch('/api/sources');
    const data = await res.json();
    state.sources = data.sources || [];
    const pill = document.getElementById('sources-count-pill');
    if (pill) pill.textContent = `${state.sources.length} official pages`;
    updateHeroSyncStatus(data.last_synced_at, data.live_count);
    const tbody = document.getElementById('sources-table-body');
    if (tbody) {
      tbody.innerHTML = state.sources.map(s => {
        const isLive = s.source_mode === 'live';
        const pillClass = isLive ? 'pill-emerald' : (s.track === 'pilot' ? 'pill-amber' : 'pill-blue');
        const freshLabel = isLive
          ? `LIVE · ${(s.fetched_at || '').slice(0, 10) || 'Now'}`
          : (s.site_last_modified || 'Registry');
        return `
        <tr>
          <td><span class="pill ${pillClass}">${esc(s.track)}</span></td>
          <td>${esc(s.title)}</td>
          <td class="tabular">${esc(freshLabel)}</td>
          <td><a href="${esc(s.url)}" target="_blank" rel="noopener">Open ↗</a></td>
        </tr>
      `;
      }).join('');
    }
    updateHeroSummary();
  } catch (err) {}
}

function askCopilotPrompt(prompt, countryScope = 'all') {
  const input = document.getElementById('chat-input');
  const scopeEl = document.getElementById('copilot-country-scope');
  if (scopeEl && countryScope) scopeEl.value = countryScope;
  if (input) input.value = prompt;
  sendCopilotQuery();
}

async function sendCopilotQuery() {
  const input = document.getElementById('chat-input');
  const history = document.getElementById('chat-history');
  const scopeEl = document.getElementById('copilot-country-scope');
  if (!input || !history) return;
  const query = input.value.trim();
  if (!query) return;
  const countryId = scopeEl ? scopeEl.value : 'all';

  input.value = '';
  history.innerHTML += `<div class="chat-msg user">${esc(query)}</div>`;
  const loadingId = `loading-${Date.now()}`;
  history.innerHTML += `<div id="${loadingId}" class="chat-msg bot">Searching real-time official government sources...</div>`;
  history.scrollTop = history.scrollHeight;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, profile: state.profile || {}, country_id: countryId }),
    });
    const data = await res.json();
    const loadingEl = document.getElementById(loadingId);
    if (loadingEl) loadingEl.remove();

    const formattedAnswer = esc(data.answer || '')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');

    const cites = (data.citations || []).map(c => `
      <a class="citation-link" href="${esc(c.url)}" target="_blank" rel="noopener">${c.source_mode === 'live' ? '[LIVE] ' : ''}${esc(c.title)} ↗</a>
    `).join('');

    history.innerHTML += `
      <div class="chat-msg bot">
        <div>${formattedAnswer}</div>
        <div class="citations-list">${cites}</div>
      </div>
    `;
    history.scrollTop = history.scrollHeight;
  } catch (err) {
    const loadingEl = document.getElementById(loadingId);
    if (loadingEl) loadingEl.textContent = 'Error querying Copilot API.';
  }
}

async function exportRoadmapReport() {
  try {
    const res = await fetch('/api/roadmap/export/html', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        profile: state.profile || {},
        progress: state.progress || {},
        shortlists: state.shortlists || {},
      }),
    });
    if (!res.ok) throw new Error('Export failed');
    const htmlContent = await res.text();
    const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const win = window.open(url, '_blank', 'noopener');
    if (!win) {
      const a = document.createElement('a');
      a.href = url;
      a.download = 'JapaAI_Canada_RCIP_Roadmap.html';
      a.click();
    }
    setTimeout(() => URL.revokeObjectURL(url), 15000);
  } catch (err) {
    showToast('Failed to export RCIP dossier.', true);
  }
}
