// DrugMind v3.0 — Frontend Application
// No emoji, SVG icons, 3D molecule viewer

const API = window.location.origin;
let allDiscussions = [];
let allRoles = [];
let selectedRoles = [];
let mol3dViewer = null;
let currentMolStyle = 'stick';

// Role SVG icon map
const ROLE_ICONS = {
  medicinal_chemist: 'icon-flask',
  biologist: 'icon-dna',
  pharmacologist: 'icon-shield',
  data_scientist: 'icon-chart',
  project_lead: 'icon-target',
};

// ─── Init ───
document.addEventListener('DOMContentLoaded', async () => {
  await loadStats();
  await loadRoles();
  await loadDiscussions();
  initScenarioTabs();
  initRoleSelector();
  initMolViewer();
});

// ─── Page Navigation ───
function showPage(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  document.querySelector(`[data-page="${page}"]`)?.classList.add('active');
  if (page === 'discuss' && allDiscussions.length === 0) loadDiscussions();
  if (page === 'team' && allRoles.length === 0) loadRoles();
  window.scrollTo({ top: 0, behavior: 'smooth' });
  closeMenu();
}

function toggleMenu() {
  document.getElementById('navLinks').classList.toggle('open');
}
function closeMenu() {
  document.getElementById('navLinks').classList.remove('open');
}

// ─── Data Loading ───
async function loadStats() {
  try {
    const r = await fetch(API + '/api/v2/stats').then(r => r.json());
    document.getElementById('statTwins').textContent = r.twins_count;
    document.getElementById('statDisc').textContent = r.discussions_count;
  } catch(e) { console.warn('Stats load failed:', e); }
}

async function loadRoles() {
  try {
    const r = await fetch(API + '/api/v2/roles').then(r => r.json());
    allRoles = r.roles || [];
    renderTeamShowcase();
    renderTeamGrid();
    initRoleSelector();
  } catch(e) { console.warn('Roles load failed:', e); }
}

async function loadDiscussions() {
  try {
    const r = await fetch(API + '/api/v2/hub').then(r => r.json());
    allDiscussions = r.discussions || [];
    renderFeed('homeFeed', allDiscussions.slice(0, 5));
    renderFeed('discussFeed', allDiscussions);
    initTagsBar();
  } catch(e) { console.warn('Discussions load failed:', e); }
}

// ─── SVG Icon Helper ───
function roleIcon(roleId, size = 24) {
  const iconId = ROLE_ICONS[roleId] || 'icon-cpu';
  return `<svg width="${size}" height="${size}"><use href="#${iconId}"/></svg>`;
}

// ─── Rendering ───
function renderTeamShowcase() {
  const el = document.getElementById('teamShowcase');
  if (!el) return;
  el.innerHTML = allRoles.map(r => `
    <div class="team-card">
      <div class="team-icon">${roleIcon(r.role_id, 48)}</div>
      <div class="team-name">${escapeHtml(r.display_name)}</div>
      <div class="team-role">${r.role_id.replace(/_/g, ' ')}</div>
      <div class="team-expertise">${r.expertise.slice(0, 3).map(e => `<span class="tag">${escapeHtml(e)}</span>`).join('')}</div>
    </div>
  `).join('');
}

function renderTeamGrid() {
  const el = document.getElementById('teamGrid');
  if (!el) return;
  el.innerHTML = allRoles.map(r => {
    const riskPct = ((r.risk_tolerance || 0.5) * 100).toFixed(0);
    return `
    <div class="team-card">
      <div class="team-icon">${roleIcon(r.role_id, 48)}</div>
      <div class="team-name">${escapeHtml(r.display_name)}</div>
      <div class="team-role">${r.role_id.replace(/_/g, ' ')}</div>
      <div class="team-expertise">${r.expertise.map(e => `<span class="tag">${escapeHtml(e)}</span>`).join('')}</div>
      <div class="team-risk">Risk Tolerance: ${riskPct}%</div>
      <div class="team-risk-bar"><div class="team-risk-fill" style="width:${riskPct}%"></div></div>
    </div>`;
  }).join('');
}

function renderFeed(containerId, discussions) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (discussions.length === 0) {
    el.innerHTML = `<div class="empty-state"><svg width="48" height="48"><use href="#icon-message"/></svg><p>No discussions yet. Be the first to start one.</p></div>`;
    return;
  }
  el.innerHTML = discussions.map(d => `
    <div class="card" onclick="expandDiscussion('${d.session_id}', this)">
      <div class="card-title">${escapeHtml(d.topic)}</div>
      <div class="card-meta">
        <div class="tags">${(d.tags || []).map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('')}</div>
        <span class="meta-text">${d.messages_count || 0} messages &middot; ${d.views || 0} views &middot; ${d.likes || 0} likes</span>
      </div>
      <div class="card-context" style="display:none">${escapeHtml(d.context || '')}</div>
      <div class="card-expanded" style="display:none"></div>
    </div>
  `).join('');
}

function initTagsBar() {
  const allTags = new Set();
  allDiscussions.forEach(d => (d.tags || []).forEach(t => allTags.add(t)));
  const el = document.getElementById('tagsBar');
  if (!el) return;
  el.innerHTML = `<button class="tag-btn active" onclick="filterTag(this, '')">All</button>` +
    [...allTags].map(t => `<button class="tag-btn" onclick="filterTag(this, '${escapeHtml(t)}')">${escapeHtml(t)}</button>`).join('');
}

function filterTag(btn, tag) {
  document.querySelectorAll('.tag-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const filtered = tag ? allDiscussions.filter(d => (d.tags || []).includes(tag)) : allDiscussions;
  renderFeed('discussFeed', filtered);
}

function searchDiscussions() {
  const q = document.getElementById('searchInput').value.toLowerCase();
  const filtered = q ? allDiscussions.filter(d => d.topic.toLowerCase().includes(q) || (d.tags || []).some(t => t.toLowerCase().includes(q))) : allDiscussions;
  renderFeed('discussFeed', filtered);
}

async function expandDiscussion(sessionId, card) {
  const expanded = card.querySelector('.card-expanded');
  if (expanded.style.display !== 'none') {
    expanded.style.display = 'none';
    return;
  }
  expanded.style.display = 'block';
  expanded.innerHTML = '<div class="skeleton" style="height:80px"></div><div class="skeleton" style="height:80px"></div>';
  try {
    const d = await fetch(API + `/api/v2/hub/${sessionId}`).then(r => r.json());
    let html = '';
    if (d.context) html += `<div class="card-context" style="display:block;margin-top:16px;padding-top:16px;border-top:1px solid var(--border)">${escapeHtml(d.context)}</div>`;
    if (d.messages && d.messages.length) {
      html += '<div class="card-messages">';
      d.messages.forEach(m => {
        const iconId = ROLE_ICONS[m.role] || 'icon-cpu';
        html += `<div class="message-item"><div class="message-header"><span class="message-icon"><svg width="20" height="20"><use href="#${iconId}"/></svg></span><span class="message-name">${escapeHtml(m.name)}</span><span class="message-role">${escapeHtml(m.role)}</span></div><div class="message-content">${escapeHtml(m.content).substring(0, 300)}${m.content.length > 300 ? '...' : ''}</div></div>`;
      });
      html += '</div>';
    }
    expanded.innerHTML = html;
  } catch(e) {
    expanded.innerHTML = '<div class="empty-state">Failed to load</div>';
  }
}

// ─── Role Selector (Ask) ───
function initRoleSelector() {
  const el = document.getElementById('roleSelector');
  if (!el || allRoles.length === 0) return;
  selectedRoles = allRoles.map(r => r.role_id);
  el.innerHTML = allRoles.map(r => `
    <div class="role-chip selected" data-role="${r.role_id}" onclick="toggleRoleChip(this)">
      <span class="role-chip-icon">${roleIcon(r.role_id, 18)}</span>
      <span>${escapeHtml(r.display_name)}</span>
    </div>
  `).join('');
}

function toggleRoleChip(chip) {
  chip.classList.toggle('selected');
  const role = chip.dataset.role;
  if (selectedRoles.includes(role)) {
    selectedRoles = selectedRoles.filter(r => r !== role);
  } else {
    selectedRoles.push(role);
  }
}

async function submitAsk() {
  const question = document.getElementById('askQuestion').value.trim();
  if (!question) { alert('Please enter a question'); return; }
  const context = document.getElementById('askContext').value.trim();
  const btn = document.getElementById('askBtn');
  btn.disabled = true; btn.innerHTML = '<svg width="18" height="18" class="spin"><use href="#icon-cpu"/></svg> Thinking...';
  const responsesEl = document.getElementById('askResponses');
  responsesEl.innerHTML = '<div class="skeleton" style="height:120px"></div><div class="skeleton" style="height:120px"></div>';

  try {
    const r = await fetch(API + '/api/v2/quick-ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, context, roles: selectedRoles })
    }).then(r => r.json());

    responsesEl.innerHTML = (r.responses || []).map(r => `
      <div class="response-card">
        <div class="response-header">
          <span class="response-icon">${roleIcon(r.role, 24)}</span>
          <span class="response-name">${escapeHtml(r.name)}</span>
          <span class="response-role">${escapeHtml(r.role)}</span>
        </div>
        <div class="response-content">${escapeHtml(r.message)}</div>
      </div>
    `).join('');
  } catch(e) {
    responsesEl.innerHTML = '<div class="empty-state">Request failed. Please try again.</div>';
  }
  btn.disabled = false; btn.innerHTML = '<svg width="18" height="18"><use href="#icon-lightning"/></svg> Submit Question';
}

// ─── ADMET ───
async function runAdmet() {
  const smiles = document.getElementById('smilesInput').value.trim();
  if (!smiles) { alert('Please enter a SMILES expression'); return; }
  const el = document.getElementById('admetResult');
  el.innerHTML = '<div class="skeleton" style="height:200px"></div>';

  try {
    const r = await fetch(API + '/api/v2/admet', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ smiles })
    }).then(r => r.json());

    if (r.error) { el.innerHTML = `<div class="empty-state">${r.error}</div>`; return; }

    const rows = [
      ['Molecular Weight (MW)', r.mw, r.mw < 500],
      ['logP', r.logp, r.logp >= 0 && r.logp <= 5],
      ['HBD', r.hbd, r.hbd <= 5],
      ['HBA', r.hba, r.hba <= 10],
      ['TPSA', r.tpsa, r.tpsa < 140],
      ['QED', r.qed, r.qed > 0.5],
      ['SA Score', r.sa_score, r.sa_score < 5],
      ['Lipinski Violations', r.lipinski_violations, r.lipinski_violations === 0],
    ];

    el.innerHTML = `<table class="admet-table">
      <thead><tr><th>Property</th><th>Value</th><th>Verdict</th></tr></thead>
      <tbody>${rows.map(([name, val, ok]) => `
        <tr><td>${name}</td><td>${val !== null ? Number(val).toFixed(2) : 'N/A'}</td>
        <td><span class="verdict ${ok ? 'verdict-pass' : 'verdict-warn'}">${ok ? 'Pass' : 'Warning'}</span></td></tr>
      `).join('')}</tbody>
    </table>`;

    // Auto-load molecule in 3D viewer
    document.getElementById('molSmiles').value = smiles;
    loadMolecule();
  } catch(e) {
    el.innerHTML = '<div class="empty-state">Assessment failed</div>';
  }
}

// ─── 3D Molecule Viewer ───
function initMolViewer() {
  const el = document.getElementById('mol3d');
  if (!el || typeof $3Dmol === 'undefined') return;
  try {
    mol3dViewer = $3Dmol.createViewer(el, {
      backgroundColor: '#0a0a14',
      antialias: true,
    });
    // Load default molecule (Aspirin)
    loadMoleculeFromSmiles('CC(=O)Oc1ccccc1C(=O)O');
    document.getElementById('molSmiles').value = 'CC(=O)Oc1ccccc1C(=O)O';
  } catch(e) {
    console.warn('3Dmol init failed:', e);
  }
}

function loadMolecule() {
  const smiles = document.getElementById('molSmiles').value.trim();
  if (!smiles) { alert('Please enter a SMILES expression'); return; }
  loadMoleculeFromSmiles(smiles);
}

function loadMoleculeFromSmiles(smiles) {
  if (!mol3dViewer) return;
  try {
    // Use PubChem REST API to get 3D SDF
    const url = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/${encodeURIComponent(smiles)}/SDF?record_type=3d`;
    fetch(url)
      .then(r => {
        if (!r.ok) throw new Error('PubChem fetch failed');
        return r.text();
      })
      .then(sdf => {
        mol3dViewer.removeAllModels();
        const model = mol3dViewer.addModel(sdf, 'sdf');
        applyMolStyle();
        mol3dViewer.zoomTo();
        mol3dViewer.render();
      })
      .catch(() => {
        // Fallback: try 2D
        const url2d = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/${encodeURIComponent(smiles)}/SDF`;
        fetch(url2d)
          .then(r => r.text())
          .then(sdf => {
            mol3dViewer.removeAllModels();
            mol3dViewer.addModel(sdf, 'sdf');
            applyMolStyle();
            mol3dViewer.zoomTo();
            mol3dViewer.render();
          })
          .catch(e => {
            console.warn('Molecule load failed:', e);
          });
      });
  } catch(e) {
    console.warn('Molecule render error:', e);
  }
}

function applyMolStyle() {
  if (!mol3dViewer) return;
  mol3dViewer.setStyle({}, {});
  if (currentMolStyle === 'stick') {
    mol3dViewer.setStyle({}, { stick: { radius: 0.15 }, sphere: { scale: 0.25 } });
  } else if (currentMolStyle === 'sphere') {
    mol3dViewer.setStyle({}, { sphere: { scale: 0.4 } });
  } else if (currentMolStyle === 'cartoon') {
    mol3dViewer.setStyle({}, { stick: { radius: 0.1 }, sphere: { scale: 0.3 }, cartoon: {} });
  }
}

function toggleMolStyle() {
  const styles = ['stick', 'sphere', 'cartoon'];
  const idx = styles.indexOf(currentMolStyle);
  currentMolStyle = styles[(idx + 1) % styles.length];
  applyMolStyle();
  if (mol3dViewer) mol3dViewer.render();
}

function resetMolView() {
  if (mol3dViewer) {
    mol3dViewer.zoomTo();
    mol3dViewer.render();
  }
}

// ─── Scenario Templates ───
const scenarios = [
  { name: 'Target Assessment', desc: 'How to systematically evaluate a new target for druggability?',
    items: ['Literature survey: disease relevance, genetic evidence', 'Structural assessment: bindable pockets available?', 'Competitive analysis: how many programs, what stage?', 'Differentiation strategy: me-better or first-in-class?', 'Experiment design: minimum viable validation', 'Go/No-Go criteria: what data supports progression?'] },
  { name: 'Lead Optimization', desc: 'Core optimization directions in Hit-to-Lead stage',
    items: ['Potency optimization: IC50/EC50 to nM level', 'Selectivity assessment: off-target risk screening', 'ADMET initial: logP, solubility, metabolic stability', 'hERG risk: IC50 > 30uM threshold', 'Synthetic accessibility: SA Score < 5', 'Patent strategy: structural novelty analysis'] },
  { name: 'Go/No-Go Decision', desc: 'Should this compound continue receiving investment?',
    items: ['Efficacy data: animal model results?', 'Safety data: toxicology assessment?', 'PK/PD: does it support QD dosing?', 'CMC feasibility: scale-up possible? Cost?', 'Competitive landscape: competitor progress?', 'Commercial assessment: projected peak sales?'] }
];

function initScenarioTabs() {
  const tabs = document.getElementById('scenarioTabs');
  if (!tabs) return;
  tabs.innerHTML = scenarios.map((s, i) => `<button class="scenario-tab ${i === 0 ? 'active' : ''}" onclick="showScenario(${i}, this)">${s.name}</button>`).join('');
  showScenario(0);
}

function showScenario(idx, btn) {
  if (btn) {
    document.querySelectorAll('.scenario-tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
  }
  const s = scenarios[idx];
  document.getElementById('scenarioContent').innerHTML = `
    <p style="color:var(--text-secondary);margin-bottom:16px">${s.desc}</p>
    <ul class="scenario-checklist">${s.items.map(i => `<li>${i}</li>`).join('')}</ul>
  `;
}

// ─── Utilities ───
function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
