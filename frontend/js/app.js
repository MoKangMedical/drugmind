// DrugMind — 前端应用
const PAGE_CONFIG = window.DRUGMIND_CONFIG || {};
const API_STORAGE_KEY = 'drugmind.apiBase';
const API_QUERY_KEY = 'api_base';
const GITHUB_PAGES_HOST = /\.github\.io$/i;
let allDiscussions = [];
let allRoles = [];
let selectedRoles = [];
let API = resolveApiBase();

function normalizeApiBase(url) {
  if (!url) return '';
  return url.replace(/\/+$/, '');
}

function resolveApiBase() {
  const params = new URLSearchParams(window.location.search);
  const queryApi = normalizeApiBase(params.get(API_QUERY_KEY) || '');
  const storedApi = normalizeApiBase(window.localStorage.getItem(API_STORAGE_KEY) || '');
  const configuredApi = normalizeApiBase(PAGE_CONFIG.defaultApiBase || '');
  const sameOrigin = normalizeApiBase(window.location.origin);
  if (queryApi) return queryApi;
  if (storedApi) return storedApi;
  if (configuredApi) return configuredApi;
  return sameOrigin;
}

function apiUrl(path) {
  const base = normalizeApiBase(API);
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${base}${normalizedPath}`;
}

function isGitHubPages() {
  return GITHUB_PAGES_HOST.test(window.location.hostname);
}

// ─── 初始化 ───
document.addEventListener('DOMContentLoaded', async () => {
  initDebugPanel();
  await loadStats();
  await loadRoles();
  await loadDiscussions();
  initScenarioTabs();
  initRoleSelector();
});

// ─── 页面切换 ───
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

// ─── 数据加载 ───
async function loadStats() {
  try {
    const r = await fetch(apiUrl('/api/v2/stats')).then(r => r.json());
    document.getElementById('statTwins').textContent = r.twins_count;
    document.getElementById('statDisc').textContent = r.discussions_count;
  } catch(e) { console.warn('Stats load failed:', e); }
}

async function loadRoles() {
  try {
    const r = await fetch(apiUrl('/api/v2/roles')).then(r => r.json());
    allRoles = r.roles || [];
    renderTeamShowcase();
    renderTeamGrid();
    initRoleSelector();
  } catch(e) { console.warn('Roles load failed:', e); }
}

async function loadDiscussions() {
  try {
    const r = await fetch(apiUrl('/api/v2/hub')).then(r => r.json());
    allDiscussions = r.discussions || [];
    renderFeed('homeFeed', allDiscussions.slice(0, 5));
    renderFeed('discussFeed', allDiscussions);
    initTagsBar();
  } catch(e) { console.warn('Discussions load failed:', e); }
}

// ─── 渲染 ───
function renderTeamShowcase() {
  const el = document.getElementById('teamShowcase');
  if (!el) return;
  el.innerHTML = allRoles.map(r => `
    <div class="team-card">
      <span class="team-emoji">${r.emoji}</span>
      <div class="team-name">${r.display_name}</div>
      <div class="team-role">${r.role_id}</div>
      <div class="team-expertise">${r.expertise.slice(0, 3).map(e => `<span class="tag">${e}</span>`).join('')}</div>
    </div>
  `).join('');
}

function renderTeamGrid() {
  const el = document.getElementById('teamGrid');
  if (!el) return;
  el.innerHTML = allRoles.map(r => `
    <div class="team-card">
      <span class="team-emoji">${r.emoji}</span>
      <div class="team-name">${r.display_name}</div>
      <div class="team-role">${r.role_id.replace('_', ' ')}</div>
      <div class="team-expertise">${r.expertise.map(e => `<span class="tag">${e}</span>`).join('')}</div>
      <div class="team-risk">风险承受度: ${((r.risk_tolerance || 0.5) * 100).toFixed(0)}%</div>
    </div>
  `).join('');
}

function renderFeed(containerId, discussions) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (discussions.length === 0) {
    el.innerHTML = `<div class="empty-state"><span class="empty-state-icon">💬</span>暂无讨论，成为第一个发起讨论的人</div>`;
    return;
  }
  el.innerHTML = discussions.map(d => `
    <div class="card" onclick="expandDiscussion('${d.session_id}', this)">
      <div class="card-title">${escapeHtml(d.topic)}</div>
      <div class="card-meta">
        <div class="tags">${(d.tags || []).map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('')}</div>
        <span class="meta-text">💬 ${d.messages_count || 0} · 👀 ${d.views || 0} · ❤️ ${d.likes || 0}</span>
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
  el.innerHTML = `<button class="tag-btn active" onclick="filterTag(this, '')">全部</button>` +
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
    const d = await fetch(apiUrl(`/api/v2/hub/${sessionId}`)).then(r => r.json());
    let html = '';
    if (d.context) html += `<div class="card-context" style="display:block;margin-top:16px;padding-top:16px;border-top:1px solid var(--border)">${escapeHtml(d.context)}</div>`;
    if (d.messages && d.messages.length) {
      html += '<div class="card-messages">';
      d.messages.forEach(m => {
        html += `<div class="message-item"><div class="message-header"><span class="message-emoji">${m.emoji}</span><span class="message-name">${escapeHtml(m.name)}</span><span class="message-role">${escapeHtml(m.role)}</span></div><div class="message-content">${escapeHtml(m.content).substring(0, 300)}${m.content.length > 300 ? '...' : ''}</div></div>`;
      });
      html += '</div>';
    }
    expanded.innerHTML = html;
  } catch(e) {
    expanded.innerHTML = '<div class="empty-state">加载失败</div>';
  }
}

// ─── 角色选择（提问） ───
function initRoleSelector() {
  const el = document.getElementById('roleSelector');
  if (!el || allRoles.length === 0) return;
  selectedRoles = allRoles.map(r => r.role_id);
  el.innerHTML = allRoles.map(r => `
    <div class="role-chip selected" data-role="${r.role_id}" onclick="toggleRoleChip(this)">
      <span class="role-chip-emoji">${r.emoji}</span>
      <span>${r.display_name}</span>
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
  if (!question) { alert('请输入问题'); return; }
  const context = document.getElementById('askContext').value.trim();
  const btn = document.getElementById('askBtn');
  btn.disabled = true; btn.textContent = 'AI思考中...';
  const responsesEl = document.getElementById('askResponses');
  responsesEl.innerHTML = '<div class="skeleton" style="height:120px"></div><div class="skeleton" style="height:120px"></div>';

  try {
    const r = await fetch(apiUrl('/api/v2/quick-ask'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, context, roles: selectedRoles })
    }).then(r => r.json());

    responsesEl.innerHTML = (r.responses || []).map(r => `
      <div class="response-card">
        <div class="response-header">
          <span class="response-emoji">${r.emoji}</span>
          <span class="response-name">${escapeHtml(r.name)}</span>
          <span class="response-role">${escapeHtml(r.role)}</span>
        </div>
        <div class="response-content">${escapeHtml(r.message)}</div>
      </div>
    `).join('');
  } catch(e) {
    responsesEl.innerHTML = '<div class="empty-state">请求失败，请重试</div>';
  }
  btn.disabled = false; btn.textContent = '提交问题';
}

// ─── ADMET ───
async function runAdmet() {
  const smiles = document.getElementById('smilesInput').value.trim();
  if (!smiles) { alert('请输入SMILES表达式'); return; }
  const el = document.getElementById('admetResult');
  el.innerHTML = '<div class="skeleton" style="height:200px"></div>';

  try {
    const r = await fetch(apiUrl('/api/v2/admet'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ smiles })
    }).then(r => r.json());

    if (r.error) { el.innerHTML = `<div class="empty-state">${r.error}</div>`; return; }

    const rows = [
      ['分子量 (MW)', r.mw, r.mw < 500],
      ['logP', r.logp, r.logp >= 0 && r.logp <= 5],
      ['HBD', r.hbd, r.hbd <= 5],
      ['HBA', r.hba, r.hba <= 10],
      ['TPSA', r.tpsa, r.tpsa < 140],
      ['QED', r.qed, r.qed > 0.5],
      ['SA Score', r.sa_score, r.sa_score < 5],
      ['Lipinski违规', r.lipinski_violations, r.lipinski_violations === 0],
    ];

    el.innerHTML = `<table class="admet-table">
      <thead><tr><th>指标</th><th>值</th><th>评价</th></tr></thead>
      <tbody>${rows.map(([name, val, ok]) => `
        <tr><td>${name}</td><td>${val !== null ? val.toFixed(2) : 'N/A'}</td>
        <td class="${ok ? 'admet-ok' : 'admet-warn'}">${ok ? '✅ 合格' : '⚠️ 需关注'}</td></tr>
      `).join('')}</tbody>
    </table>`;
  } catch(e) {
    el.innerHTML = '<div class="empty-state">评估失败</div>';
  }
}

// ─── 场景模板 ───
const scenarios = [
  { name: '新靶点评估', desc: '拿到一个新的靶点，如何系统评估其成药性？',
    items: ['文献调研：疾病关联性、遗传学证据', '结构评估：是否有可结合的口袋？', '竞争分析：已有多少项目？走到哪个阶段？', '差异化策略：me-better还是first-in-class？', '实验设计：最小可行验证实验', 'Go/No-Go标准：什么数据支持推进？'] },
  { name: '先导化合物优化', desc: 'Hit-to-Lead阶段的核心优化方向',
    items: ['活性优化：IC50/EC50达到nM级别', '选择性评估：脱靶风险筛查', 'ADMET初评：logP, solubility, metabolic stability', 'hERG风险评估：IC50 > 30μM', '合成路线：SA Score < 5', '专利策略：结构新颖性分析'] },
  { name: 'Go/No-Go决策', desc: '一个化合物是否应该继续投入？',
    items: ['疗效数据：动物模型是否有效？', '安全性数据：毒理学评估结果？', 'PK/PD：体内药代动力学是否支持每日一次给药？', 'CMC可行性：能否放大生产？成本如何？', '竞争格局：同期竞品进展如何？', '商业评估：预期峰值销售是多少？'] }
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

function initDebugPanel() {
  document.getElementById('frontendHostLabel').textContent = window.location.origin;
  document.getElementById('apiBaseInput').value = API;
  renderPresetList();
  refreshApiLabels();
  if (isGitHubPages() && !PAGE_CONFIG.defaultApiBase && !window.localStorage.getItem(API_STORAGE_KEY) && !new URLSearchParams(window.location.search).get(API_QUERY_KEY)) {
    setDebugResult('当前运行在 GitHub Pages。请先配置一个 HTTPS API Base URL，再调试动态功能。', 'warn');
  }
}

function renderPresetList() {
  const presetList = document.getElementById('presetList');
  const presets = [];
  if (!isGitHubPages()) {
    presets.push(window.location.origin);
  }
  (PAGE_CONFIG.preferredApiBases || []).forEach((item) => {
    const normalized = normalizeApiBase(item);
    if (normalized && !presets.includes(normalized)) presets.push(normalized);
  });
  if (presets.length === 0) {
    presetList.innerHTML = '<span class="debug-help">暂无预置端点</span>';
    return;
  }
  presetList.innerHTML = presets.map((preset) => `
    <button class="preset-btn" type="button" onclick="applyPresetApi('${escapeHtml(preset)}')">${escapeHtml(preset)}</button>
  `).join('');
}

function applyPresetApi(apiBase) {
  document.getElementById('apiBaseInput').value = apiBase;
}

function toggleDebugPanel() {
  document.getElementById('debugPanel').classList.toggle('open');
}

function saveApiBase() {
  const nextBase = normalizeApiBase(document.getElementById('apiBaseInput').value.trim());
  API = nextBase || normalizeApiBase(window.location.origin);
  if (nextBase) {
    window.localStorage.setItem(API_STORAGE_KEY, nextBase);
  } else {
    window.localStorage.removeItem(API_STORAGE_KEY);
  }
  refreshApiLabels();
  setDebugResult(`已保存 API 端点：${API}`, 'ok');
  loadStats();
  loadRoles();
  loadDiscussions();
}

function clearApiBase() {
  window.localStorage.removeItem(API_STORAGE_KEY);
  document.getElementById('apiBaseInput').value = '';
  API = resolveApiBase();
  refreshApiLabels();
  setDebugResult(`已恢复默认 API 端点：${API}`, 'ok');
}

function refreshApiLabels() {
  document.getElementById('apiBaseLabel').textContent = API;
  document.getElementById('envModeBadge').textContent = isGitHubPages() ? 'GitHub Pages' : 'Local / Custom Host';
  const docsUrl = `${normalizeApiBase(API)}/docs`;
  const mcpUrl = `${normalizeApiBase(API)}/api/mcp`;
  document.getElementById('apiDocsLink').href = docsUrl;
  document.getElementById('mcpLink').href = mcpUrl;
  document.getElementById('aboutApiDocsLink').href = docsUrl;
  document.getElementById('aboutMcpLink').href = mcpUrl;
}

async function testApiConnection() {
  const statusEl = document.getElementById('apiHealthStatus');
  statusEl.textContent = '检测中...';
  statusEl.className = 'env-status pending';
  try {
    const response = await fetch(apiUrl('/health'));
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    statusEl.textContent = '连接正常';
    statusEl.className = 'env-status ok';
    setDebugResult(`健康检查通过：status=${payload.status}, version=${payload.version}`, 'ok');
  } catch (error) {
    statusEl.textContent = '连接失败';
    statusEl.className = 'env-status error';
    setDebugResult(`API 检测失败：${error.message}`, 'error');
  }
}

function setDebugResult(message, mode = '') {
  const result = document.getElementById('debugResult');
  result.textContent = message;
  result.className = `debug-result ${mode}`.trim();
}

// ─── 工具函数 ───
function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
