// RCIP Canada AI Frontend Controller (Civic Editorial + Vercel Stateless Support)

const STORAGE_KEY = 'rcip_canada_ai_state_v2';
const THEME_KEY = 'rcip_canada_ai_theme';
const MAX_UPLOAD_BYTES = Math.floor(4.2 * 1024 * 1024);
const DONUT_CIRCUMFERENCE = 263.89;

function esc(value) {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

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
// Theme & Local Persistence
// --------------------------------------------------------------------------

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY) || 'light';
  applyTheme(saved);
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme === 'dark' ? 'dark' : 'light');
  localStorage.setItem(THEME_KEY, theme === 'dark' ? 'dark' : 'light');
  const moon = document.getElementById('theme-icon-moon');
  const sun = document.getElementById('theme-icon-sun');
  if (moon && sun) {
    moon.classList.toggle('hidden', theme === 'dark');
    sun.classList.toggle('hidden', theme !== 'dark');
  }
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'light';
  applyTheme(current === 'dark' ? 'light' : 'dark');
}

function loadLocalBrowserState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
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
  setupResumeDropzone();

  try {
    const healthRes = await fetch('/api/health');
    const health = await healthRes.json();
    state.environment = health.environment || 'local';
    const envLabel = document.getElementById('env-storage-label');
    if (envLabel) {
      envLabel.textContent =
        state.environment === 'vercel'
          ? 'Vercel Serverless • Private Browser-Saved Roadmap'
          : 'Local SQLite + Browser-Synced Roadmap';
    }
  } catch (err) {
    console.error(err);
  }

  const localData = loadLocalBrowserState();
  if (localData) {
    state.profile = localData.profile || {};
    state.progress = localData.progress || {};
    state.shortlists = localData.shortlists || {};
  } else if (state.environment === 'local') {
    await hydrateFromLocalServer();
  }

  await Promise.all([loadSources(), loadCommunities()]);
  populateProfileForm();
  await recomputeRoadmapAndEvaluation();
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
    console.error('Local server hydration failed', err);
  }
}

// --------------------------------------------------------------------------
// Navigation & Wizard Controls
// --------------------------------------------------------------------------

function switchTab(tabId) {
  document.querySelectorAll('.ws-tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });
  document.querySelectorAll('.tab-panel').forEach(panel => {
    panel.classList.toggle('active', panel.id === tabId);
  });
}

function toggleMobileDrawer() {
  const drawer = document.getElementById('mobile-drawer');
  if (drawer) drawer.classList.toggle('open');
}

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

function prevWizardStep() {
  setWizardStep(state.wizardStep - 1);
}

function nextWizardStep() {
  setWizardStep(state.wizardStep + 1);
}

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

// --------------------------------------------------------------------------
// Compute Roadmap, Readiness Ring & KPIs
// --------------------------------------------------------------------------

async function recomputeRoadmapAndEvaluation() {
  try {
    const res = await fetch('/api/roadmap/compute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        profile: state.profile || {},
        progress: state.progress || {},
      }),
    });
    const data = await res.json();
    state.roadmap = data.roadmap;
    state.evaluation = data.evaluation;
    state.officialForms = data.official_forms || [];

    updateHeroSummary();
    renderStageRail();
    renderRoadmap();
    renderEvaluationScorecard(state.evaluation);
    renderOfficialForms();
  } catch (err) {
    showToast('Failed to compute RCIP roadmap.', true);
  }
}

function updateHeroSummary() {
  const ev = state.evaluation || {};
  const rm = state.roadmap || {};
  const score = Number(ev.readiness_score || 0);

  const scoreEl = document.getElementById('kpi-score');
  const ringEl = document.getElementById('hero-donut-ring');
  const verdictEl = document.getElementById('kpi-verdict');
  const progEl = document.getElementById('kpi-progress');
  const progBar = document.getElementById('kpi-progress-bar');
  const trackEl = document.getElementById('kpi-track');
  const branchEl = document.getElementById('kpi-branch');
  const pagesEl = document.getElementById('kpi-pages');
  const shortEl = document.getElementById('kpi-shortlisted');
  const tabRoadmapBadge = document.getElementById('tab-badge-roadmap');
  const tabScoreBadge = document.getElementById('tab-badge-score');

  if (scoreEl) scoreEl.textContent = `${score}%`;
  if (ringEl) {
    const offset = DONUT_CIRCUMFERENCE * (1 - Math.max(0, Math.min(100, score)) / 100);
    ringEl.style.strokeDashoffset = String(offset.toFixed(2));
    ringEl.style.stroke = score >= 80 ? 'var(--emerald)' : (score >= 40 ? 'var(--amber)' : 'var(--brand)');
  }
  if (verdictEl) verdictEl.textContent = ev.verdict || 'Profile incomplete';

  const done = rm.completed_items || 0;
  const total = rm.total_items || 0;
  const pct = rm.completion_percent || 0;
  if (progEl) progEl.textContent = `${done} / ${total} steps (${pct}%)`;
  if (progBar) progBar.style.width = `${pct}%`;
  if (tabRoadmapBadge) tabRoadmapBadge.textContent = `${done}/${total}`;
  if (tabScoreBadge) tabScoreBadge.textContent = `${score}%`;

  const trackObj = ev.program_track || {};
  if (trackEl) trackEl.textContent = trackObj.track === 'pilot' ? 'Pilot (<= Dec 31, 2026)' : 'Permanent 2027';

  const ctx = ev.applicant_context || {};
  const branchParts = [
    ctx.location_branch === 'inside_canada' ? 'Inside Canada' : 'Outside Canada',
    ctx.funds_exempt ? 'Funds Exempt' : 'Funds Required',
  ];
  if (ctx.local_grad_exempt) branchParts.push('Local Grad Exempt');
  if (branchEl) branchEl.textContent = branchParts.join(' · ');

  if (pagesEl) pagesEl.textContent = `${state.sources.length} Canada.ca pages`;
  const shortCount = Object.values(state.shortlists || {}).filter(s => s && s.shortlisted).length;
  if (shortEl) shortEl.textContent = `${shortCount} shortlisted`;
}

function renderStageRail() {
  const rail = document.getElementById('stage-rail');
  const rm = state.roadmap;
  if (!rail || !rm) return;

  const allActive = state.focusedStageId === null;
  let html = `
    <button type="button" class="rail-btn ${allActive ? 'active' : ''}" onclick="focusRoadmapStage(null)">
      All 6 Stages
    </button>
  `;

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
    if (ctx.local_grad_exempt) {
      badges.push('<span class="pill pill-emerald">Local Graduate Exempt</span>');
    }
    badgeWrap.innerHTML = badges.join('');
  }

  const showAll = !!document.getElementById('toggle-show-all-steps')?.checked;
  const stagesEl = document.getElementById('roadmap-stages-container');
  if (stagesEl) {
    const stagesToRender = (roadmap.stages || []).filter(
      s => !state.focusedStageId || s.stage_id === state.focusedStageId
    );
    stagesEl.innerHTML = stagesToRender.map(stage => {
      const visibleItems = showAll ? stage.items : stage.items.filter(i => i.applicable);
      const itemsHtml = visibleItems.map(item => {
        const formsHtml = (item.forms || []).map(f => `<span class="form-chip">${esc(f)}</span>`).join('');
        const inactiveBadge = !item.applicable
          ? `<span class="pill">Inactive for branch (${esc(item.applies_to)})</span>`
          : '';
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
                <button type="button" class="btn btn-ghost btn-sm" onclick="toggleTaskNoteBox('${esc(item.id)}')">
                  ${noteText ? 'Edit Note' : '+ Note'}
                </button>
              </div>
              <div id="note-box-${esc(item.id)}" class="note-box ${noteText ? '' : 'hidden'}">
                <input type="text" id="note-input-${esc(item.id)}" class="input" style="font-size:12px; padding:6px 10px;"
                       value="${esc(noteText)}" placeholder="Add personal reminder or document reference...">
                <button type="button" class="btn btn-sm" onclick="saveTaskNote('${esc(item.id)}', '${esc(stage.stage_id)}')">Save</button>
              </div>
            </div>
          </div>
        `;
      }).join('');

      return `
        <div class="stage-block">
          <div class="stage-block-head">
            <div>
              <h3 style="font-size:16.5px; font-weight:700;">${esc(stage.title)}</h3>
            </div>
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
    if (actions.length === 0) {
      planEl.innerHTML = '<div class="pill pill-emerald">All 6 core eligibility pillars satisfied. Ready to submit PR Portal dossier.</div>';
    } else {
      planEl.innerHTML = actions.map(a => `
        <div class="action-item priority-${esc(a.priority)}">
          <div style="font-weight:700; margin-bottom:2px;">[${esc(a.priority)}] ${esc(a.pillar)}</div>
          <div style="color:var(--ink-muted); margin-bottom:4px;">${esc(a.action)}</div>
          <a href="${esc(a.url)}" target="_blank" rel="noopener">Verify on Canada.ca ↗</a>
        </div>
      `).join('');
    }
  }
}

function toggleTaskNoteBox(itemId) {
  const box = document.getElementById(`note-box-${itemId}`);
  if (box) box.classList.toggle('hidden');
}

async function saveTaskNote(itemId, stageId) {
  const input = document.getElementById(`note-input-${itemId}`);
  const existing = state.progress[itemId] || {};
  const completed = !!existing.completed;
  const notes = (input?.value || '').trim();
  await updateChecklistRecord(itemId, stageId, completed, notes);
  showToast('Milestone note saved.');
}

async function toggleChecklistItem(itemId, stageId, completed) {
  const existing = state.progress[itemId] || {};
  await updateChecklistRecord(itemId, stageId, completed, existing.notes || '');
  showToast(completed ? 'Milestone completed.' : 'Milestone marked incomplete.');
}

async function updateChecklistRecord(itemId, stageId, completed, notes) {
  state.progress[itemId] = {
    item_id: itemId,
    stage_id: stageId,
    completed: !!completed,
    notes: notes || '',
    target_date: '',
  };
  persistBrowserState();

  if (state.environment === 'local') {
    try {
      await fetch('/api/roadmap/progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: itemId, stage_id: stageId, completed: !!completed, notes: notes || '' }),
      });
    } catch (err) {
      console.warn('Local SQLite progress sync failed', err);
    }
  }
  await recomputeRoadmapAndEvaluation();
}

function renderOfficialForms() {
  const container = document.getElementById('official-forms-list');
  if (!container) return;
  container.innerHTML = (state.officialForms || []).map(f => `
    <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; padding:9px 11px; border-radius:8px; background:var(--bg-subtle); border:1px solid var(--border-subtle);">
      <div>
        <div style="font-size:12.5px; font-weight:700;">${esc(f.code)}</div>
        <div style="font-size:11.5px; color:var(--ink-muted);">${esc(f.title)}</div>
      </div>
      <a class="btn btn-sm" href="${esc(f.url)}" target="_blank" rel="noopener">Guide ↗</a>
    </div>
  `).join('');
}

// --------------------------------------------------------------------------
// Profile Intake, Evaluation, Resume & Tools
// --------------------------------------------------------------------------

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

function setVal(id, val) {
  const el = document.getElementById(id);
  if (el && val !== null && val !== undefined) el.value = val;
}

function setChecked(id, val) {
  const el = document.getElementById(id);
  if (el) el.checked = !!val;
}

function numOrNull(id) {
  const v = document.getElementById(id)?.value;
  if (v === '' || v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function intOrNull(id) {
  const n = numOrNull(id);
  return n === null ? null : Math.trunc(n);
}

function strVal(id) {
  return (document.getElementById(id)?.value || '').trim();
}

function boolVal(id) {
  return !!document.getElementById(id)?.checked;
}

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
    } catch (err) {
      console.warn('Local SQLite save failed', err);
    }
  }
  await recomputeRoadmapAndEvaluation();
  showToast('Profile saved and RCIP readiness recalculated.');
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
      const gapsHtml = (p.gaps || []).map(g => `<li style="color:var(--brand); margin-top:3px;">${esc(g)}</li>`).join('');
      const detailsHtml = (p.details || []).map(d => `<li style="color:var(--ink-muted); margin-top:3px;">${esc(d)}</li>`).join('');
      return `
        <div class="pillar-tile">
          <div class="pillar-head">
            <strong style="font-size:13px;">${esc(p.title)}</strong>
            <span class="pill ${statusClass}">${esc(p.status)}</span>
          </div>
          <div class="tabular" style="font-size:13px; font-weight:700;">${p.score} / ${p.max_score} pts</div>
          <p style="font-size:12px; color:var(--ink-muted); margin-top:5px;">${esc(p.summary)}</p>
          <ul style="font-size:11.5px; padding-left:16px; margin-top:5px;">
            ${detailsHtml}
            ${gapsHtml}
          </ul>
          <div style="margin-top:8px;">
            <a style="font-size:11.5px;" href="${esc(p.url)}" target="_blank" rel="noopener">Canada.ca Rules ↗</a>
          </div>
        </div>
      `;
    }).join('');
  }
}

function toggleLocalGradBox() {
  const box = document.getElementById('local-grad-box');
  if (box) box.classList.toggle('hidden', !boolVal('f-is-local-grad'));
}

function toggleECABox() {
  const box = document.getElementById('eca-fields-box');
  if (box) box.classList.toggle('hidden', strVal('f-edu-origin') === 'canada');
}

function toggleOfferChecks() {
  const box = document.getElementById('offer-checks-box');
  if (box) box.classList.toggle('hidden', !boolVal('f-has-offer'));
}

function toggleRecDate() {
  const box = document.getElementById('rec-date-box');
  if (box) box.classList.toggle('hidden', !boolVal('f-has-rec'));
}

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
      const ratio = Math.min(100, Math.round((avail / req) * 100));
      if (bar) bar.style.width = `${ratio}%`;
      if (avail >= req) {
        readout.className = 'pill pill-emerald tabular';
        readout.textContent = `Meets minimum CAD $${req.toLocaleString()} (Family size ${size})`;
      } else {
        readout.className = 'pill pill-amber tabular';
        readout.textContent = `Family size ${size} needs CAD $${req.toLocaleString()} (Shortfall: $${(req - avail).toLocaleString()})`;
      }
    }
  } catch (err) {
    // non-fatal
  }
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
    if (!res.ok) throw new Error(data.detail || 'Error');
    const c = data.conversion;
    const p = c.per_skill_clb;
    readout.className = `pill tabular ${c.overall_clb >= 5 ? 'pill-emerald' : (c.overall_clb >= 4 ? 'pill-amber' : 'pill-red')}`;
    readout.textContent = `Governing CLB/NCLC: ${c.overall_clb}`;

    if (cards) {
      const skills = [
        { key: 'reading', label: 'Reading' },
        { key: 'writing', label: 'Writing' },
        { key: 'listening', label: 'Listening' },
        { key: 'speaking', label: 'Speaking' },
      ];
      cards.innerHTML = skills.map(sk => {
        const lvl = p[sk.key] || 0;
        const isLowest = lvl === c.overall_clb;
        return `
          <div class="clb-mini-card ${isLowest ? 'is-lowest' : ''}">
            <div style="font-size:11px; color:var(--ink-subtle); font-weight:600;">${esc(sk.label)}</div>
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
  if (!q) {
    container.innerHTML = '';
    return;
  }
  try {
    const res = await fetch(`/api/tools/noc-search?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    container.innerHTML = (data.results || []).slice(0, 6).map(item => `
      <button type="button" class="prompt-chip"
              onclick="applyNocChoice('${esc(item.noc)}', ${Number(item.teer)}, '${esc(item.title)}')">
        NOC ${esc(item.noc)} (TEER ${Number(item.teer)}) — ${esc(item.title)}
      </button>
    `).join('');
  } catch (err) {
    container.innerHTML = '';
  }
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
  dz.addEventListener('dragover', e => {
    e.preventDefault();
    dz.classList.add('dragover');
  });
  dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
  dz.addEventListener('drop', e => {
    e.preventDefault();
    dz.classList.remove('dragover');
    if (e.dataTransfer?.files?.length) {
      handleResumeFileUpload(e.dataTransfer.files[0]);
    }
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
    showToast('File exceeds 4.2 MB Vercel limit. Please upload a smaller PDF/DOCX or paste text.', true);
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
  if (!txt) {
    showToast('Paste your resume text first.', true);
    return;
  }
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
      <span style="font-size:12.5px;"><strong>NOC ${esc(n.noc)} (TEER ${Number(n.teer)})</strong> — ${esc(n.title)} <em>(matched: ${esc((n.matched_keywords || []).join(', '))})</em></span>
      <button type="button" class="btn btn-sm" onclick="applyNocChoice('${esc(n.noc)}', ${Number(n.teer)}, '${esc(n.title)}')">Use as Target</button>
    </div>
  `).join('') || '<div style="font-size:12.5px; color:var(--ink-subtle); margin-top:4px;">No automatic NOC match — search your exact job title below.</div>';

  box.innerHTML = `
    <div style="font-size:13px; font-weight:700; margin-bottom:6px;">Extracted Resume Signals</div>
    <div class="tag-row" style="margin-bottom:8px;">${skillsHtml}</div>
    <div style="font-size:12px; color:var(--ink-muted);">Top Suggested NOC 2021 Matches (verify duties on noc.esdc.gc.ca):</div>
    ${nocsHtml}
  `;
}

// --------------------------------------------------------------------------
// 14 Participating Communities
// --------------------------------------------------------------------------

function filterCommunities(prov, btnEl) {
  state.provinceFilter = prov;
  document.querySelectorAll('.prov-btn').forEach(b => b.classList.remove('active'));
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
  } catch (err) {
    showToast('Could not load participating communities.', true);
  }
}

function populateCommunitySelect() {
  const sel = document.getElementById('f-target-community');
  if (!sel || !state.communitiesCatalog.length) return;
  const current = state.profile?.target_community_id || sel.value || '';
  sel.innerHTML =
    '<option value="">Select community...</option>' +
    state.communitiesCatalog
      .map(c => `<option value="${esc(c.id)}">${esc(c.name)}, ${esc(c.province_code)}</option>`)
      .join('');
  if (current) sel.value = current;
}

function renderCommunities() {
  const grid = document.getElementById('communities-grid');
  if (!grid) return;

  const q = strVal('comm-search').toLowerCase();
  const prov = state.provinceFilter.toLowerCase();

  const merged = state.communitiesCatalog.map(c => {
    const sl = state.shortlists[c.id] || {};
    return {
      ...c,
      shortlisted: !!sl.shortlisted,
      notes: sl.notes || '',
      employers_contacted: Number(sl.employers_contacted || 0),
    };
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
            <button type="button" class="btn btn-sm ${c.shortlisted ? 'btn-emerald' : ''}"
                    onclick="updateCommunityState('${esc(c.id)}', ${!c.shortlisted}, ${c.employers_contacted})">
              ${c.shortlisted ? 'Shortlisted' : 'Shortlist'}
            </button>
          </div>
          <div class="tag-row" style="margin:10px 0;">${sectors}</div>
          <div style="font-size:12px; color:var(--ink-muted); margin-bottom:6px;">
            <strong>Local Schools:</strong> ${esc(insts)}
          </div>
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
    } catch (err) {
      console.warn('Local SQLite shortlist sync failed', err);
    }
  }
  showToast('Community tracker updated.');
}

// --------------------------------------------------------------------------
// Live Canada.ca Sync, Official Sources, RAG Copilot & Stateless Export
// --------------------------------------------------------------------------

async function triggerCanadaSync() {
  const btn = document.getElementById('btn-sync-canada');
  const origHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Syncing Canada.ca...';
  }
  try {
    const res = await fetch('/api/sync-canada', { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error('Sync failed');
    await loadSources();
    updateHeroSummary();
    showToast(`Canada.ca synced: ${data.total_indexed} pages indexed (${data.inserted} new, ${data.updated} updated).`);
  } catch (err) {
    showToast('Live Canada.ca sync encountered an error.', true);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origHtml || 'Sync Canada.ca';
    }
  }
}

async function loadSources() {
  try {
    const res = await fetch('/api/sources');
    const data = await res.json();
    state.sources = data.sources || [];
    const pill = document.getElementById('sources-count-pill');
    if (pill) pill.textContent = `${state.sources.length} official pages`;

    const tbody = document.getElementById('sources-table-body');
    if (tbody) {
      tbody.innerHTML = state.sources.map(s => `
        <tr>
          <td><span class="pill ${s.track === 'pilot' ? 'pill-amber' : 'pill-red'}">${esc(s.track)}</span></td>
          <td>${esc(s.title)}</td>
          <td class="tabular">${esc(s.site_last_modified || 'N/A')}</td>
          <td><a href="${esc(s.url)}" target="_blank" rel="noopener">Open ↗</a></td>
        </tr>
      `).join('');
    }
    updateHeroSummary();
  } catch (err) {
    console.error(err);
  }
}

function askCopilotPrompt(prompt) {
  const input = document.getElementById('chat-input');
  if (input) input.value = prompt;
  sendCopilotQuery();
}

async function sendCopilotQuery() {
  const input = document.getElementById('chat-input');
  const history = document.getElementById('chat-history');
  if (!input || !history) return;
  const query = input.value.trim();
  if (!query) return;

  input.value = '';
  history.innerHTML += `<div class="chat-msg user">${esc(query)}</div>`;
  const loadingId = `loading-${Date.now()}`;
  history.innerHTML += `<div id="${loadingId}" class="chat-msg bot">Searching indexed Canada.ca RCIP pages...</div>`;
  history.scrollTop = history.scrollHeight;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, profile: state.profile || {} }),
    });
    const data = await res.json();
    const loadingEl = document.getElementById(loadingId);
    if (loadingEl) loadingEl.remove();

    const formattedAnswer = esc(data.answer || '')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');

    const cites = (data.citations || []).map(c => `
      <a class="citation-link" href="${esc(c.url)}" target="_blank" rel="noopener">${esc(c.title)} ↗</a>
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
      a.download = 'RCIP_Canada_Roadmap_Report.html';
      a.click();
    }
    setTimeout(() => URL.revokeObjectURL(url), 15000);
  } catch (err) {
    showToast('Failed to export roadmap report.', true);
  }
}
