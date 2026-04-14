// DrugMind — 前端应用
const PAGE_CONFIG = window.DRUGMIND_CONFIG || {};
const API_STORAGE_KEY = 'drugmind.apiBase';
const API_QUERY_KEY = 'api_base';
const USER_STORAGE_KEY = 'drugmind.currentUser';
const GITHUB_PAGES_HOST = /\.github\.io$/i;
let allDiscussions = [];
let allRoles = [];
let selectedRoles = [];
let allProjects = [];
let platformAgents = [];
let discoveryCapabilities = [];
let discoveryBlueprints = [];
let blatantWhyOverview = null;
let blatantWhyMcpServers = [];
let blatantWhyProviders = null;
let mediPharmaOverview = null;
let mediPharmaHealth = null;
let mediPharmaEcosystem = null;
let selectedWorkbenchProjectId = '';
let selectedRunId = '';
let workbenchData = null;
let h2aThreads = [];
let selectedH2AThreadId = '';
let selectedHomeAgentIds = [];
let selectedCapabilityId = '';
let currentUser = null;
let currentUserIdentity = null;
let tamarindRuntimeStatus = null;
let tamarindAvailableTools = [];
let tamarindJobList = [];
let lastStructuralResearchResult = null;
let lastByScreeningResult = null;
let lastBiologicsPipelineResult = null;
let lastTamarindJobResult = null;
let lastSecondMeSyncResult = null;
let lastMediPharmaResult = null;
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

async function fetchJsonApi(path, options = {}) {
  const response = await fetch(apiUrl(path), options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || payload.error || `HTTP ${response.status}`);
  }
  return payload;
}

function isGitHubPages() {
  return GITHUB_PAGES_HOST.test(window.location.hostname);
}

// ─── 初始化 ───
document.addEventListener('DOMContentLoaded', async () => {
  loadStoredUser();
  initDebugPanel();
  initStoryVideo();
  await loadStats();
  await loadRoles();
  await loadDiscussions();
  initScenarioTabs();
  initRoleSelector();
  await loadSecondMeStatus();
  await loadSecondMeInstances();
  await loadPlatformAgents();
  await loadDrugDiscoveryCatalogs();
  await loadProjects();
});

// ─── 页面切换 ───
function showPage(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  document.querySelector(`[data-page="${page}"]`)?.classList.add('active');
  if (page === 'discuss' && allDiscussions.length === 0) loadDiscussions();
  if (page === 'team' && allRoles.length === 0) loadRoles();
  if (page === 'workbench') {
    if (allProjects.length === 0) {
      loadProjects();
    } else if (selectedWorkbenchProjectId) {
      loadWorkbench(selectedWorkbenchProjectId);
    }
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
  closeMenu();
}

function toggleMenu() {
  document.getElementById('navLinks').classList.toggle('open');
}
function closeMenu() {
  document.getElementById('navLinks').classList.remove('open');
}

function scrollToStoryDemo() {
  const storySection = document.getElementById('storyDemoSection');
  if (!storySection) return;
  storySection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function scrollToH2A() {
  const section = document.getElementById('homeH2ASection');
  if (!section) return;
  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
    renderHomeAgentDeck();
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

// ─── Second Me ───
async function loadSecondMeStatus() {
  const el = document.getElementById('secondMeStatus');
  if (!el) return;
  el.textContent = '检测中...';
  try {
    const payload = await fetch(apiUrl('/api/v2/second-me/status')).then(r => r.json());
    if (payload.status !== 'ready') {
      el.textContent = 'Second Me 未初始化';
      return;
    }
    const mode = payload.capabilities?.mode || 'unknown';
    const instances = payload.capabilities?.instances_count || 0;
    const bindings = payload.bindings || 0;
    el.textContent = `Second Me 已接入 · mode=${mode} · instances=${instances} · bindings=${bindings}`;
  } catch (error) {
    console.warn('Second Me status load failed:', error);
    el.textContent = 'Second Me 状态加载失败';
  }
}

async function loadSecondMeInstances() {
  const el = document.getElementById('secondMeInstances');
  if (!el) return;
  el.innerHTML = '<div class="skeleton" style="height:100px"></div>';
  try {
    const payload = await fetch(apiUrl('/api/v2/second-me')).then(r => r.json());
    const instances = payload.instances || [];
    if (instances.length === 0) {
      el.innerHTML = '<div class="empty-state">还没有接入的 Second Me 分身</div>';
      return;
    }
    el.innerHTML = instances.map((instance) => `
      <div class="response-card">
        <div class="response-header">
          <span class="response-emoji">🔗</span>
          <span class="response-name">${escapeHtml(instance.name || instance.instance_id)}</span>
          <span class="response-role">${escapeHtml(instance.role || '')}</span>
        </div>
        <div class="response-content">
          status=${escapeHtml(instance.status || 'created')}
          ${instance.linked_project_id ? `\nproject=${escapeHtml(instance.linked_project_id)}` : ''}
          ${instance.linked_twin_id ? `\ntwin=${escapeHtml(instance.linked_twin_id)}` : ''}
          ${instance.last_synced_at ? `\nlast_sync=${escapeHtml(instance.last_synced_at)}` : ''}
        </div>
      </div>
    `).join('');
  } catch (error) {
    console.warn('Second Me instances load failed:', error);
    el.innerHTML = '<div class="empty-state">Second Me 列表加载失败</div>';
  }
}

async function createSecondMeInstance() {
  const name = document.getElementById('secondMeName')?.value.trim() || '';
  const role = document.getElementById('secondMeRole')?.value || 'medicinal_chemist';
  const expertiseRaw = document.getElementById('secondMeExpertise')?.value || '';
  const expertise = expertiseRaw.split(',').map(item => item.trim()).filter(Boolean);
  const el = document.getElementById('secondMeInstances');
  if (!name) {
    alert('请输入分身名称');
    return;
  }
  if (el) {
    el.innerHTML = '<div class="skeleton" style="height:100px"></div>';
  }
  try {
    const payload = await fetch(apiUrl('/api/v2/second-me/create'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        role,
        expertise,
        personality: 'balanced',
      }),
    }).then(r => r.json());
    if (payload.error || payload.detail) {
      throw new Error(payload.error || payload.detail);
    }
    document.getElementById('secondMeName').value = '';
    document.getElementById('secondMeExpertise').value = '';
    await loadSecondMeStatus();
    await loadSecondMeInstances();
  } catch (error) {
    console.warn('Second Me create failed:', error);
    if (el) {
      el.innerHTML = `<div class="empty-state">创建失败：${escapeHtml(error.message || 'unknown error')}</div>`;
    }
  }
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
  loadSecondMeStatus();
  loadSecondMeInstances();
  loadPlatformAgents();
  loadDrugDiscoveryCatalogs();
  loadProjects();
}

function clearApiBase() {
  window.localStorage.removeItem(API_STORAGE_KEY);
  document.getElementById('apiBaseInput').value = '';
  API = resolveApiBase();
  refreshApiLabels();
  setDebugResult(`已恢复默认 API 端点：${API}`, 'ok');
  loadStats();
  loadRoles();
  loadDiscussions();
  loadSecondMeStatus();
  loadSecondMeInstances();
  loadPlatformAgents();
  loadDrugDiscoveryCatalogs();
  loadProjects();
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

function initStoryVideo() {
  const video = document.getElementById('storyVideo');
  if (!video) return;
  const prefersReducedMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReducedMotion) {
    video.pause();
    setStoryVideoState(false);
    return;
  }
  video.addEventListener('play', () => setStoryVideoState(true));
  video.addEventListener('pause', () => setStoryVideoState(false));
  video.addEventListener('ended', () => setStoryVideoState(false));
  video.play().catch(() => {
    setStoryVideoState(false);
  });
}

function setStoryVideoState(isPlaying) {
  const status = document.getElementById('storyPlaybackState');
  const button = document.getElementById('storyToggleBtn');
  if (status) {
    status.textContent = isPlaying ? '视频播放中' : '视频已暂停';
    status.classList.toggle('paused', !isPlaying);
  }
  if (button) {
    button.textContent = isPlaying ? '暂停短片' : '播放短片';
  }
}

function toggleStoryVideo() {
  const video = document.getElementById('storyVideo');
  if (!video) return;
  if (video.paused) {
    video.play().catch(() => {
      setStoryVideoState(false);
    });
    return;
  }
  video.pause();
}

function restartStoryVideo() {
  const video = document.getElementById('storyVideo');
  if (!video) return;
  video.currentTime = 0;
  video.play().catch(() => {
    setStoryVideoState(false);
  });
}

function openDemoReel() {
  window.open('demo-reel.html', '_blank', 'noopener,noreferrer');
}

// ─── 用户身份 ───
function loadStoredUser() {
  try {
    const raw = window.localStorage.getItem(USER_STORAGE_KEY);
    currentUser = raw ? JSON.parse(raw) : null;
  } catch (error) {
    currentUser = null;
  }
  currentUserIdentity = null;
  renderCurrentUserCard();
}

function persistCurrentUser(user) {
  currentUser = user || null;
  currentUserIdentity = null;
  if (currentUser) {
    window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(currentUser));
  } else {
    window.localStorage.removeItem(USER_STORAGE_KEY);
  }
  renderCurrentUserCard();
}

function renderCurrentUserCard() {
  const card = document.getElementById('currentUserCard');
  const loginForm = document.getElementById('homeLoginForm');
  const registerForm = document.getElementById('homeRegisterForm');
  if (!card) return;
  if (!currentUser) {
    card.innerHTML = '<div class="empty-state" style="padding:20px">当前未登录，H2A 会话会退化为临时成员身份，无法继承项目权限。</div>';
    if (loginForm) loginForm.style.display = 'grid';
    return;
  }
  const permissions = currentUserIdentity?.effective_permissions || currentUser.permissions || [];
  const accessRole = currentUserIdentity?.workspace_role || currentUser.title || currentUser.system_role || 'Workspace Member';
  const projectLabel = currentUserIdentity?.project_id || selectedWorkbenchProjectId || '';
  card.innerHTML = `
    <div class="h2a-user-head">
      <div>
        <strong>${escapeHtml(currentUser.display_name || currentUser.username || currentUser.user_id)}</strong>
        <p>${escapeHtml(accessRole)} · ${escapeHtml(currentUser.organization || 'DrugMind User')}</p>
      </div>
      <button class="btn btn-sm btn-outline" type="button" onclick="logoutHomeUser()">退出</button>
    </div>
    <div class="timeline-meta">
      <span class="artifact-pill">${escapeHtml(currentUser.user_id)}</span>
      <span class="artifact-pill">${escapeHtml(currentUser.system_role || 'member')}</span>
      ${projectLabel ? `<span class="artifact-pill">project · ${escapeHtml(projectLabel)}</span>` : ''}
    </div>
    <div class="timeline-meta">
      ${permissions.length
        ? permissions.slice(0, 6).map((permission) => `<span class="artifact-pill">${escapeHtml(permission)}</span>`).join('')
        : '<span class="artifact-pill">无显式权限</span>'}
    </div>
  `;
  if (loginForm) loginForm.style.display = 'none';
  if (registerForm) registerForm.style.display = 'none';
}

async function syncCurrentUserIdentity(projectId = selectedWorkbenchProjectId) {
  currentUserIdentity = null;
  if (!currentUser || !projectId) {
    renderCurrentUserCard();
    return;
  }
  try {
    const identity = await fetch(apiUrl(`/api/v2/projects/${projectId}/identity/${currentUser.user_id}`)).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      return data;
    });
    currentUserIdentity = identity;
  } catch (error) {
    console.warn('User identity sync failed:', error);
  }
  renderCurrentUserCard();
}

function toggleRegisterForm() {
  const form = document.getElementById('homeRegisterForm');
  if (!form) return;
  form.style.display = form.style.display === 'none' ? 'grid' : 'none';
}

async function loginHomeUser() {
  const username = document.getElementById('loginUsername')?.value.trim() || '';
  const password = document.getElementById('loginPassword')?.value || '';
  if (!username || !password) {
    showH2AStatus('请输入用户名和密码', 'error');
    return;
  }
  try {
    const login = await fetch(apiUrl('/api/v2/login'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || data.error || `HTTP ${r.status}`);
      return data;
    });
    const profile = await fetch(apiUrl(`/api/v2/users/${login.user_id}`)).then(r => r.json());
    persistCurrentUser(profile);
    await syncCurrentUserIdentity();
    renderH2ASelectors();
    showH2AStatus(`已登录：${profile.display_name || profile.username}`, 'ok');
  } catch (error) {
    console.warn('Login failed:', error);
    showH2AStatus(`登录失败：${error.message}`, 'error');
  }
}

async function registerHomeUser() {
  const displayName = document.getElementById('registerDisplayName')?.value.trim() || '';
  const username = document.getElementById('registerUsername')?.value.trim() || '';
  const email = document.getElementById('registerEmail')?.value.trim() || '';
  const password = document.getElementById('registerPassword')?.value || '';
  if (!displayName || !username || !email || !password) {
    showH2AStatus('请填写完整注册信息', 'error');
    return;
  }
  try {
    const registered = await fetch(apiUrl('/api/v2/register'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username,
        email,
        password,
        display_name: displayName,
        title: 'Project Scientist',
      }),
    }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || data.error || `HTTP ${r.status}`);
      return data;
    });
    const profile = await fetch(apiUrl(`/api/v2/users/${registered.user_id}`)).then(r => r.json());
    persistCurrentUser(profile);
    toggleRegisterForm();
    await syncCurrentUserIdentity();
    renderH2ASelectors();
    showH2AStatus(`已注册并登录：${profile.display_name || profile.username}`, 'ok');
  } catch (error) {
    console.warn('Register failed:', error);
    showH2AStatus(`注册失败：${error.message}`, 'error');
  }
}

function logoutHomeUser() {
  persistCurrentUser(null);
  renderH2ASelectors();
  showH2AStatus('已退出当前身份', 'ok');
}

// ─── Workflow Workbench ───
async function loadPlatformAgents() {
  try {
    const payload = await fetch(apiUrl('/api/v2/platform/agents?active_only=false')).then(r => r.json());
    platformAgents = payload.agents || [];
    renderHomeAgentDeck();
    renderH2ASelectors();
  } catch (error) {
    console.warn('Platform agents load failed:', error);
    platformAgents = [];
  }
}

async function loadDrugDiscoveryCatalogs() {
  const [
    capabilitiesResult,
    blueprintsResult,
    byOverviewResult,
    byServersResult,
    mediOverviewResult,
    mediHealthResult,
  ] = await Promise.allSettled([
    fetchJsonApi('/api/v2/drug-discovery/capabilities'),
    fetchJsonApi('/api/v2/drug-discovery/blueprints'),
    fetchJsonApi('/api/v2/integrations/blatant-why'),
    fetchJsonApi('/api/v2/integrations/blatant-why/mcp-servers'),
    fetchJsonApi('/api/v2/integrations/medi-pharma'),
    fetchJsonApi('/api/v2/integrations/medi-pharma/health'),
  ]);

  discoveryCapabilities = capabilitiesResult.status === 'fulfilled'
    ? (capabilitiesResult.value.capabilities || [])
    : [];
  discoveryBlueprints = blueprintsResult.status === 'fulfilled'
    ? (blueprintsResult.value.blueprints || [])
    : [];
  blatantWhyOverview = byOverviewResult.status === 'fulfilled'
    ? byOverviewResult.value
    : null;
  blatantWhyMcpServers = byServersResult.status === 'fulfilled'
    ? (byServersResult.value.servers || [])
    : [];
  mediPharmaOverview = mediOverviewResult.status === 'fulfilled'
    ? mediOverviewResult.value
    : mediPharmaOverview;
  mediPharmaHealth = mediHealthResult.status === 'fulfilled'
    ? mediHealthResult.value
    : mediPharmaHealth;

  if (capabilitiesResult.status !== 'fulfilled') {
    console.warn('Drug discovery capabilities load failed:', capabilitiesResult.reason);
  }
  if (blueprintsResult.status !== 'fulfilled') {
    console.warn('Drug discovery blueprints load failed:', blueprintsResult.reason);
  }
  if (byOverviewResult.status !== 'fulfilled') {
    console.warn('BY overview load failed:', byOverviewResult.reason);
  }
  if (byServersResult.status !== 'fulfilled') {
    console.warn('BY MCP server load failed:', byServersResult.reason);
  }
  if (mediOverviewResult.status !== 'fulfilled') {
    console.warn('MediPharma overview load failed:', mediOverviewResult.reason);
  }
  if (mediHealthResult.status !== 'fulfilled') {
    console.warn('MediPharma health load failed:', mediHealthResult.reason);
  }

  await refreshBridgeRuntime({
    projectId: selectedWorkbenchProjectId,
    includeJobs: Boolean(selectedWorkbenchProjectId),
    rerender: Boolean(workbenchData?.project),
  });

  if (workbenchData?.project) {
    renderWorkbench();
  }
}

async function refreshBridgeRuntime({ projectId = selectedWorkbenchProjectId, includeJobs = true, rerender = false } = {}) {
  const requests = [
    fetchJsonApi('/api/v2/integrations/blatant-why/providers'),
    fetchJsonApi('/api/v2/integrations/tamarind/status'),
    fetchJsonApi('/api/v2/integrations/tamarind/tools'),
  ];
  if (includeJobs) {
    requests.push(
      fetchJsonApi(
        `/api/v2/integrations/tamarind/jobs?${new URLSearchParams({
          job_name: projectId || '',
          limit: '8',
        }).toString()}`
      )
    );
  }

  const [providersResult, tamarindStatusResult, tamarindToolsResult, tamarindJobsResult] = await Promise.allSettled(requests);

  blatantWhyProviders = providersResult.status === 'fulfilled' ? providersResult.value : blatantWhyProviders;
  tamarindRuntimeStatus = tamarindStatusResult.status === 'fulfilled' ? tamarindStatusResult.value : tamarindRuntimeStatus;
  tamarindAvailableTools = tamarindToolsResult.status === 'fulfilled'
    ? (tamarindToolsResult.value.tools || [])
    : tamarindAvailableTools;
  tamarindJobList = includeJobs && tamarindJobsResult?.status === 'fulfilled'
    ? (tamarindJobsResult.value.jobs || [])
    : (includeJobs ? tamarindJobList : []);

  if (providersResult.status !== 'fulfilled') {
    console.warn('BY providers load failed:', providersResult.reason);
  }
  if (tamarindStatusResult.status !== 'fulfilled') {
    console.warn('Tamarind status load failed:', tamarindStatusResult.reason);
  }
  if (tamarindToolsResult.status !== 'fulfilled') {
    console.warn('Tamarind tools load failed:', tamarindToolsResult.reason);
  }
  if (includeJobs && tamarindJobsResult?.status !== 'fulfilled') {
    console.warn('Tamarind jobs load failed:', tamarindJobsResult.reason);
  }

  if (rerender) {
    renderByBridgePanel();
  }
}

async function refreshDrugDiscoveryCatalogs() {
  await loadDrugDiscoveryCatalogs();
  showWorkbenchMessage('Drug discovery 目录已刷新', 'ok');
}

async function loadProjects() {
  try {
    const payload = await fetch(apiUrl('/api/v2/projects')).then(r => r.json());
    allProjects = payload.projects || [];
    renderProjectSelect();
    if (!selectedWorkbenchProjectId && allProjects.length > 0) {
      selectedWorkbenchProjectId = allProjects[0].project_id;
    }
    if (selectedWorkbenchProjectId) {
      await loadWorkbench(selectedWorkbenchProjectId);
    } else {
      await syncCurrentUserIdentity('');
      renderEmptyWorkbench();
      renderH2ASelectors();
    }
  } catch (error) {
    console.warn('Projects load failed:', error);
    showWorkbenchMessage(`项目列表加载失败：${error.message}`, 'error');
  }
}

function renderProjectSelect() {
  const selects = ['workbenchProjectSelect', 'homeProjectSelect', 'homeH2AProjectSelect']
    .map((id) => document.getElementById(id))
    .filter(Boolean);
  if (!selects.length) return;
  const options = allProjects.length
    ? allProjects.map((project) => `
      <option value="${escapeHtml(project.project_id)}" ${project.project_id === selectedWorkbenchProjectId ? 'selected' : ''}>
        ${escapeHtml(project.name)} · ${escapeHtml(formatStageLabel(project.stage))}
      </option>
    `).join('')
    : '<option value="">暂无项目</option>';
  selects.forEach((select) => {
    select.innerHTML = options;
  });
}

function selectWorkbenchProject(projectId) {
  selectedWorkbenchProjectId = projectId || '';
  if (!selectedWorkbenchProjectId) {
    renderEmptyWorkbench();
    return Promise.resolve();
  }
  return loadWorkbench(selectedWorkbenchProjectId);
}

function selectHomeProject(projectId) {
  return selectWorkbenchProject(projectId);
}

function changeH2AProject(projectId) {
  selectedH2AThreadId = '';
  return selectWorkbenchProject(projectId);
}

async function loadWorkbench(projectId) {
  if (!projectId) {
    renderEmptyWorkbench();
    return;
  }
  if (selectedWorkbenchProjectId && selectedWorkbenchProjectId !== projectId) {
    lastStructuralResearchResult = null;
    lastByScreeningResult = null;
    lastBiologicsPipelineResult = null;
    lastTamarindJobResult = null;
    lastSecondMeSyncResult = null;
    tamarindJobList = [];
  }
  selectedWorkbenchProjectId = projectId;
  renderProjectSelect();
  setWorkbenchLoading();
  try {
    const payload = await fetch(apiUrl(`/api/v2/projects/${projectId}/workbench`)).then(r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    });
    workbenchData = payload;
    await syncCurrentUserIdentity(projectId);
    const runs = payload.workflow_runs || [];
    if (!selectedRunId || !runs.some((run) => run.run_id === selectedRunId)) {
      selectedRunId = runs[0]?.run_id || '';
    }
    await refreshBridgeRuntime({ projectId, includeJobs: true });
    renderWorkbench();
    await loadH2AThreads(projectId);
  } catch (error) {
    console.warn('Workbench load failed:', error);
    workbenchData = null;
    renderEmptyWorkbench(`工作台加载失败：${error.message}`);
    showWorkbenchMessage(`工作台加载失败：${error.message}`, 'error');
  }
}

async function refreshWorkbench() {
  if (!selectedWorkbenchProjectId) {
    await loadProjects();
    return;
  }
  await loadWorkbench(selectedWorkbenchProjectId);
  showWorkbenchMessage('工作台已刷新', 'ok');
}

function showWorkbenchCreateProject() {
  const card = document.getElementById('workbenchCreateProjectCard');
  if (card) card.style.display = 'block';
}

function hideWorkbenchCreateProject() {
  const card = document.getElementById('workbenchCreateProjectCard');
  if (card) card.style.display = 'none';
}

async function createWorkbenchProject() {
  const name = document.getElementById('workbenchProjectName').value.trim();
  const target = document.getElementById('workbenchProjectTarget').value.trim();
  const disease = document.getElementById('workbenchProjectDisease').value.trim();
  if (!name) {
    alert('请输入项目名称');
    return;
  }
  try {
    const payload = await fetch(apiUrl('/api/v2/projects'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        target,
        disease,
        owner_id: 'workspace.lead',
      }),
    }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      return data;
    });
    document.getElementById('workbenchProjectName').value = '';
    document.getElementById('workbenchProjectTarget').value = '';
    document.getElementById('workbenchProjectDisease').value = '';
    hideWorkbenchCreateProject();
    showWorkbenchMessage(`项目已创建：${payload.name}`, 'ok');
    await loadProjects();
    if (payload.project_id) {
      await selectWorkbenchProject(payload.project_id);
      showPage('workbench');
    }
  } catch (error) {
    console.warn('Create project failed:', error);
    showWorkbenchMessage(`创建项目失败：${error.message}`, 'error');
  }
}

async function addWorkspaceMember() {
  if (!selectedWorkbenchProjectId) {
    alert('请先选择项目');
    return;
  }
  const name = document.getElementById('workspaceMemberName').value.trim();
  const role = document.getElementById('workspaceMemberRole').value.trim();
  if (!name) {
    alert('请输入成员名称');
    return;
  }
  try {
    await fetch(apiUrl(`/api/v2/projects/${selectedWorkbenchProjectId}/workspace/members`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: `human.${toSlug(name)}`,
        name,
        role: role || 'Contributor',
        type: 'human',
      }),
    }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      return data;
    });
    document.getElementById('workspaceMemberName').value = '';
    document.getElementById('workspaceMemberRole').value = '';
    showWorkbenchMessage(`已添加成员：${name}`, 'ok');
    await loadWorkbench(selectedWorkbenchProjectId);
  } catch (error) {
    console.warn('Add member failed:', error);
    showWorkbenchMessage(`添加成员失败：${error.message}`, 'error');
  }
}

async function startWorkbenchWorkflow() {
  if (!selectedWorkbenchProjectId) {
    alert('请先选择项目');
    return;
  }
  const templateId = document.getElementById('workflowTemplateSelect').value;
  const topic = document.getElementById('workflowTopicInput').value.trim();
  const autoExecute = document.getElementById('workflowAutoExecute').checked;
  if (!templateId || !topic) {
    alert('请选择模板并输入议题');
    return;
  }
  try {
    const payload = await fetch(apiUrl('/api/v2/workflows/runs'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        template_id: templateId,
        project_id: selectedWorkbenchProjectId,
        topic,
        created_by: 'web.workbench',
        requested_by: 'web.workbench',
        auto_execute: autoExecute,
        max_steps: autoExecute ? 6 : 1,
      }),
    }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      return data;
    });
    document.getElementById('workflowTopicInput').value = '';
    selectedRunId = payload.run?.run_id || payload.run_id || selectedRunId;
    showWorkbenchMessage('Workflow 已启动', 'ok');
    await loadWorkbench(selectedWorkbenchProjectId);
  } catch (error) {
    console.warn('Start workflow failed:', error);
    showWorkbenchMessage(`启动 Workflow 失败：${error.message}`, 'error');
  }
}

function getSelectedRun() {
  const runs = workbenchData?.workflow_runs || [];
  if (!runs.length) return null;
  return runs.find((run) => run.run_id === selectedRunId) || runs[0];
}

function selectRun(runId) {
  selectedRunId = runId;
  renderWorkflowRuns();
}

async function executeSelectedRun(maxSteps = 1) {
  const run = getSelectedRun();
  if (!run) {
    alert('当前没有 workflow run');
    return;
  }
  await executeWorkflowRun(run.run_id, maxSteps);
}

async function executeWorkflowRun(runId, maxSteps = 1) {
  try {
    await fetch(apiUrl(`/api/v2/workflows/runs/${runId}/execute`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        requested_by: 'web.workbench',
        max_steps: maxSteps,
      }),
    }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      return data;
    });
    selectedRunId = runId;
    showWorkbenchMessage(maxSteps > 1 ? 'Workflow 已推进到下一个门控点' : '当前步骤已执行', 'ok');
    await loadWorkbench(selectedWorkbenchProjectId);
  } catch (error) {
    console.warn('Execute run failed:', error);
    showWorkbenchMessage(`执行 Workflow 失败：${error.message}`, 'error');
  }
}

async function executeWorkflowStep(runId, stepId, forceAi = false) {
  try {
    await fetch(apiUrl(`/api/v2/workflows/runs/${runId}/steps/${stepId}/execute`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        requested_by: 'web.workbench',
        force_ai: forceAi,
      }),
    }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      return data;
    });
    selectedRunId = runId;
    showWorkbenchMessage(forceAi ? 'AI 已接管当前步骤' : '步骤执行成功', 'ok');
    await loadWorkbench(selectedWorkbenchProjectId);
  } catch (error) {
    console.warn('Execute step failed:', error);
    showWorkbenchMessage(`执行步骤失败：${error.message}`, 'error');
  }
}

async function approveWorkflowStep(runId, stepId, approved) {
  try {
    await fetch(apiUrl(`/api/v2/workflows/runs/${runId}/steps/${stepId}/approve`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        approved,
        approver_id: 'workspace.reviewer',
        note: approved ? 'Approved from workbench' : 'Rejected from workbench',
      }),
    }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      return data;
    });
    selectedRunId = runId;
    showWorkbenchMessage(approved ? '审批已通过' : '审批已拒绝', approved ? 'ok' : 'error');
    await loadWorkbench(selectedWorkbenchProjectId);
  } catch (error) {
    console.warn('Approve step failed:', error);
    showWorkbenchMessage(`审批失败：${error.message}`, 'error');
  }
}

async function assignStepOwner(runId, stepId, selectId) {
  const select = document.getElementById(selectId);
  const value = select?.value || '';
  if (!value) {
    alert('请选择一个 owner');
    return;
  }
  const [ownerType, ownerId] = value.split('::');
  const ownerLabel = select.options[select.selectedIndex]?.textContent || ownerId;
  try {
    await fetch(apiUrl(`/api/v2/workflows/runs/${runId}/steps/${stepId}/assign`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        owner_type: ownerType,
        owner_id: ownerId,
        owner_label: ownerLabel,
        assigned_by: 'web.workbench',
      }),
    }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      return data;
    });
    selectedRunId = runId;
    showWorkbenchMessage(`Owner 已切换到 ${ownerLabel}`, 'ok');
    await loadWorkbench(selectedWorkbenchProjectId);
  } catch (error) {
    console.warn('Assign owner failed:', error);
    showWorkbenchMessage(`切换 owner 失败：${error.message}`, 'error');
  }
}

async function manualCompleteWorkflowStep(runId, stepId) {
  const output = window.prompt('输入人工执行结果摘要');
  if (output === null) return;
  const note = window.prompt('可选备注', 'Completed by human owner') || '';
  try {
    await fetch(apiUrl(`/api/v2/workflows/runs/${runId}/steps/${stepId}/complete`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        output,
        note,
      }),
    }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      return data;
    });
    selectedRunId = runId;
    showWorkbenchMessage('人工步骤已完成', 'ok');
    await loadWorkbench(selectedWorkbenchProjectId);
  } catch (error) {
    console.warn('Complete step failed:', error);
    showWorkbenchMessage(`人工完成失败：${error.message}`, 'error');
  }
}

function setWorkbenchLoading() {
  const skeleton = '<div class="skeleton" style="height:120px"></div>';
  const summary = document.getElementById('workbenchProjectSummary');
  const implementation = document.getElementById('workbenchImplementationPanel');
  const secondMe = document.getElementById('workbenchSecondMePanel');
  const capability = document.getElementById('workbenchCapabilityPanel');
  const byBridge = document.getElementById('workbenchByBridgePanel');
  const mediPharma = document.getElementById('workbenchMediPharmaPanel');
  const members = document.getElementById('workspaceMembersList');
  const timeline = document.getElementById('artifactTimeline');
  const runs = document.getElementById('workflowRunsPanel');
  if (summary) summary.innerHTML = skeleton;
  if (implementation) implementation.innerHTML = skeleton + skeleton;
  if (secondMe) secondMe.innerHTML = skeleton;
  if (capability) capability.innerHTML = skeleton + skeleton;
  if (byBridge) byBridge.innerHTML = skeleton + skeleton;
  if (mediPharma) mediPharma.innerHTML = skeleton + skeleton;
  if (members) members.innerHTML = skeleton;
  if (timeline) timeline.innerHTML = skeleton + skeleton;
  if (runs) runs.innerHTML = skeleton + skeleton;
}

function renderEmptyWorkbench(message = '请选择一个项目') {
  const summary = document.getElementById('workbenchProjectSummary');
  const implementation = document.getElementById('workbenchImplementationPanel');
  const secondMe = document.getElementById('workbenchSecondMePanel');
  const capability = document.getElementById('workbenchCapabilityPanel');
  const byBridge = document.getElementById('workbenchByBridgePanel');
  const mediPharma = document.getElementById('workbenchMediPharmaPanel');
  const members = document.getElementById('workspaceMembersList');
  const timeline = document.getElementById('artifactTimeline');
  const runs = document.getElementById('workflowRunsPanel');
  const stage = document.getElementById('workbenchProjectStage');
  if (summary) summary.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
  if (implementation) implementation.innerHTML = '<div class="empty-state">暂无 implementation 数据</div>';
  if (secondMe) secondMe.innerHTML = '<div class="empty-state">暂无 Second Me 绑定</div>';
  if (capability) capability.innerHTML = '<div class="empty-state">暂无 capability 数据</div>';
  if (byBridge) byBridge.innerHTML = '<div class="empty-state">暂无 BY 桥接数据</div>';
  if (mediPharma) mediPharma.innerHTML = '<div class="empty-state">暂无 MediPharma 数据</div>';
  if (members) members.innerHTML = '<div class="empty-state">暂无成员</div>';
  if (timeline) timeline.innerHTML = '<div class="empty-state">暂无时间线数据</div>';
  if (runs) runs.innerHTML = '<div class="empty-state">还没有 workflow run</div>';
  if (stage) stage.textContent = '未选择';
  workbenchData = null;
  blatantWhyProviders = null;
  tamarindRuntimeStatus = null;
  tamarindAvailableTools = [];
  tamarindJobList = [];
  mediPharmaHealth = null;
  mediPharmaEcosystem = null;
  lastStructuralResearchResult = null;
  lastTamarindJobResult = null;
  lastMediPharmaResult = null;
  h2aThreads = [];
  selectedH2AThreadId = '';
  renderHomeSurface();
  renderH2ASelectors();
  renderH2AThreadList();
  renderH2AConversation();
}

function renderWorkbench() {
  renderProjectSummary();
  renderImplementationPanel();
  renderCapabilityPanel();
  renderSecondMePanel();
  renderByBridgePanel();
  renderMediPharmaPanel();
  renderWorkspaceMembers();
  renderWorkflowTemplateSelect();
  renderArtifactTimeline();
  renderWorkflowRuns();
  renderHomeSurface();
  renderH2ASelectors();
}

function renderProjectSummary() {
  const summary = document.getElementById('workbenchProjectSummary');
  const stageBadge = document.getElementById('workbenchProjectStage');
  if (!summary) return;
  if (!workbenchData?.project) {
    summary.innerHTML = '<div class="empty-state">请选择一个项目</div>';
    if (stageBadge) stageBadge.textContent = '未选择';
    return;
  }

  const { project, workspace = {}, compounds = [], workflow_runs: runs = [], second_me_bindings: bindings = [], timeline = [], implementation = {} } = workbenchData;
  const currentRun = getSelectedRun();
  const implementationState = implementation.state || {};
  const currentPhase = implementation.current_phase || {};
  const recentExecutions = implementation.recent_executions || [];
  const memoryCount = timeline.filter((item) => item.item_type === 'memory').length;
  const decisionCount = timeline.filter((item) => item.item_type === 'decision').length;
  const humanMembers = (workspace.members || []).filter((member) => (member.type || 'human') === 'human');
  if (stageBadge) stageBadge.textContent = formatStageLabel(project.stage);

  summary.innerHTML = `
    <div class="workbench-title-row">
      <div>
        <div class="workbench-project-name">${escapeHtml(project.name)}</div>
        <div class="workbench-project-meta">
          ${escapeHtml(project.target || '未设置靶点')} · ${escapeHtml(project.disease || '未设置疾病')}<br>
          项目 ID: ${escapeHtml(project.project_id)}
        </div>
      </div>
      <span class="status-badge ${statusClass(project.status)}">${escapeHtml(formatStatus(project.status))}</span>
    </div>
    <div class="workbench-metric-grid">
      <div class="workbench-metric">
        <div class="workbench-metric-label">活跃流程</div>
        <div class="workbench-metric-value">${runs.length}</div>
      </div>
      <div class="workbench-metric">
        <div class="workbench-metric-label">化合物</div>
        <div class="workbench-metric-value">${compounds.length}</div>
      </div>
      <div class="workbench-metric">
        <div class="workbench-metric-label">记忆条目</div>
        <div class="workbench-metric-value">${memoryCount}</div>
      </div>
      <div class="workbench-metric">
        <div class="workbench-metric-label">关键决策</div>
        <div class="workbench-metric-value">${decisionCount}</div>
      </div>
      <div class="workbench-metric">
        <div class="workbench-metric-label">Capabilities</div>
        <div class="workbench-metric-value">${(implementation.available_capabilities || []).length}</div>
      </div>
      <div class="workbench-metric">
        <div class="workbench-metric-label">Executions</div>
        <div class="workbench-metric-value">${recentExecutions.length}</div>
      </div>
    </div>
    <div class="workbench-meta-list">
      <div class="workbench-meta-row"><span>Workspace Owner</span><strong>${escapeHtml(workspace.owner_id || '未设置')}</strong></div>
      <div class="workbench-meta-row"><span>人工成员</span><strong>${humanMembers.length}</strong></div>
      <div class="workbench-meta-row"><span>默认 AI Agent</span><strong>${(workspace.default_agents || []).length}</strong></div>
      <div class="workbench-meta-row"><span>Second Me Bindings</span><strong>${bindings.length}</strong></div>
      <div class="workbench-meta-row"><span>当前 Run</span><strong>${escapeHtml(currentRun?.template_name || '暂无')}</strong></div>
      <div class="workbench-meta-row"><span>Blueprint</span><strong>${escapeHtml(implementation.blueprint?.name || '未激活')}</strong></div>
      <div class="workbench-meta-row"><span>当前 Phase</span><strong>${escapeHtml(currentPhase.name || formatStageLabel(project.stage))}</strong></div>
      <div class="workbench-meta-row"><span>Phase Status</span><strong>${escapeHtml(formatStatus(implementationState.status || project.status || 'active'))}</strong></div>
      <div class="workbench-meta-row"><span>项目模态</span><strong>${escapeHtml(project.modality || 'small_molecule')}</strong></div>
      <div class="workbench-meta-row"><span>预算</span><strong>${Number(project.budget_total || 0).toLocaleString()}</strong></div>
    </div>
  `;
}

function renderImplementationPanel() {
  const container = document.getElementById('workbenchImplementationPanel');
  if (!container) return;
  if (!workbenchData?.project) {
    container.innerHTML = '<div class="empty-state">请选择一个项目</div>';
    return;
  }

  const implementation = workbenchData.implementation || {};
  const blueprint = implementation.blueprint || {};
  const currentPhase = implementation.current_phase || {};
  const state = implementation.state || {};
  const phases = blueprint.phases || [];
  const availableCapabilities = implementation.available_capabilities || [];
  const recentExecutions = implementation.recent_executions || [];
  const selectedBlueprint = blueprint.blueprint_id || discoveryBlueprints[0]?.blueprint_id || '';
  const progress = phases.length
    ? Math.round(((Number(implementation.phase_index || 0) + 1) / phases.length) * 100)
    : 0;

  container.innerHTML = `
    <div class="workbench-panel-stack">
      <div class="workbench-form-grid compact">
        <select id="implementationBlueprintSelect" class="input">
          ${(discoveryBlueprints.length ? discoveryBlueprints : [blueprint]).filter((item) => item && item.blueprint_id).map((item) => `
            <option value="${escapeHtml(item.blueprint_id)}" ${item.blueprint_id === selectedBlueprint ? 'selected' : ''}>
              ${escapeHtml(item.name || item.blueprint_id)}
            </option>
          `).join('')}
        </select>
        <textarea id="implementationBootstrapNote" class="textarea small" rows="2" placeholder="可选说明，例如：切换到 biologics 蓝图，准备进入结构研究。"></textarea>
        <button class="btn btn-outline full" type="button" onclick="bootstrapProjectImplementation()">重新激活 Implementation</button>
      </div>

      <div class="capability-highlight">
        <div class="workbench-capability-head">
          <div>
            <strong>${escapeHtml(currentPhase.name || '未激活 Phase')}</strong>
            <p>${escapeHtml(currentPhase.description || blueprint.description || '暂无 implementation 描述')}</p>
          </div>
          <span class="status-badge ${statusClass(state.status || 'active')}">${escapeHtml(formatStatus(state.status || 'active'))}</span>
        </div>
        <div class="workbench-progress-rail">
          <div class="workbench-progress-fill" style="width:${progress}%"></div>
        </div>
        <div class="timeline-meta">
          <span class="artifact-pill">blueprint · ${escapeHtml(blueprint.name || blueprint.blueprint_id || 'N/A')}</span>
          <span class="artifact-pill">phase · ${escapeHtml(currentPhase.phase_id || 'N/A')}</span>
          <span class="artifact-pill">progress · ${progress}%</span>
          <span class="artifact-pill">recent executions · ${recentExecutions.length}</span>
        </div>
      </div>

      <div class="phase-strip">
        ${phases.length ? phases.map((phase, index) => `
          <article class="phase-chip ${phase.phase_id === currentPhase.phase_id ? 'active' : ''}">
            <span>${String(index + 1).padStart(2, '0')}</span>
            <strong>${escapeHtml(phase.name)}</strong>
            <p>${escapeHtml(phase.objective || phase.description || '')}</p>
          </article>
        `).join('') : '<div class="empty-state">暂无 phase 配置</div>'}
      </div>

      <div class="workbench-meta-list">
        <div class="workbench-meta-row"><span>Active Capabilities</span><strong>${availableCapabilities.length}</strong></div>
        <div class="workbench-meta-row"><span>Exit Criteria</span><strong>${(currentPhase.exit_criteria || []).length}</strong></div>
        <div class="workbench-meta-row"><span>Recommended Workflows</span><strong>${(currentPhase.recommended_workflows || []).length}</strong></div>
        <div class="workbench-meta-row"><span>Success Metrics</span><strong>${(currentPhase.success_metrics || []).length}</strong></div>
      </div>

      <div class="timeline-meta">
        ${(availableCapabilities || []).slice(0, 8).map((capability) => `
          <span class="artifact-pill">capability · ${escapeHtml(capability.name)}</span>
        `).join('') || '<span class="artifact-pill">暂无激活 capability</span>'}
      </div>

      <div class="workbench-checklist">
        ${(currentPhase.exit_criteria || []).map((item) => `<div>• ${escapeHtml(item)}</div>`).join('') || '<div>暂无 exit criteria</div>'}
      </div>
    </div>
  `;
}

function renderCapabilityPanel() {
  const container = document.getElementById('workbenchCapabilityPanel');
  if (!container) return;
  if (!workbenchData?.project) {
    container.innerHTML = '<div class="empty-state">请选择一个项目</div>';
    return;
  }

  const implementation = workbenchData.implementation || {};
  const availableCapabilities = implementation.available_capabilities?.length
    ? implementation.available_capabilities
    : discoveryCapabilities;
  const recentExecutions = implementation.recent_executions || [];
  const currentPhase = implementation.current_phase || {};

  if (!selectedCapabilityId || !availableCapabilities.some((item) => item.capability_id === selectedCapabilityId)) {
    selectedCapabilityId = availableCapabilities[0]?.capability_id || '';
  }

  const capability = availableCapabilities.find((item) => item.capability_id === selectedCapabilityId)
    || discoveryCapabilities.find((item) => item.capability_id === selectedCapabilityId)
    || null;

  container.innerHTML = `
    <div class="workbench-panel-stack">
      <div class="workbench-form-grid compact">
        <select id="capabilitySelect" class="input" onchange="selectCapability(this.value)">
          ${availableCapabilities.map((item) => `
            <option value="${escapeHtml(item.capability_id)}" ${item.capability_id === selectedCapabilityId ? 'selected' : ''}>
              ${escapeHtml(item.name)} · ${escapeHtml(item.category)}
            </option>
          `).join('') || '<option value="">暂无 capability</option>'}
        </select>
        <textarea id="capabilityPayloadInput" class="textarea small" rows="3" placeholder='可选 JSON input_payload，例如：{"compound_limit": 12, "compound_ids": ["cmpd_1"]}'></textarea>
        <label class="checkbox-row">
          <input type="checkbox" id="capabilitySyncToSecondMe">
          <span>执行后同步到 Second Me</span>
        </label>
        <button class="btn btn-primary full" type="button" onclick="executeSelectedCapability()">执行 Capability</button>
      </div>

      ${capability ? `
        <div class="capability-highlight">
          <div class="workbench-capability-head">
            <div>
              <strong>${escapeHtml(capability.name)}</strong>
              <p>${escapeHtml(capability.description || '暂无描述')}</p>
            </div>
            <span class="artifact-pill">${escapeHtml(capability.category)}</span>
          </div>
          <div class="timeline-meta">
            <span class="artifact-pill">phase · ${escapeHtml(currentPhase.name || formatStageLabel(workbenchData.project.stage))}</span>
            ${capability.stage_ids?.map((stageId) => `<span class="artifact-pill">${escapeHtml(stageId)}</span>`).join('') || ''}
          </div>
          <div class="timeline-meta">
            ${(capability.required_inputs || []).map((item) => `<span class="artifact-pill">input · ${escapeHtml(item)}</span>`).join('') || '<span class="artifact-pill">input · none</span>'}
            ${(capability.outputs || []).map((item) => `<span class="artifact-pill">output · ${escapeHtml(item)}</span>`).join('') || ''}
          </div>
          <div class="timeline-meta">
            ${(capability.recommended_agents || []).map((item) => `<span class="artifact-pill">agent · ${escapeHtml(item)}</span>`).join('') || '<span class="artifact-pill">agent · auto</span>'}
            ${(capability.tool_ids || []).map((item) => `<span class="artifact-pill">tool · ${escapeHtml(item)}</span>`).join('')}
          </div>
        </div>
      ` : '<div class="empty-state">暂无 capability 详情</div>'}

      <div class="execution-feed">
        ${recentExecutions.length ? recentExecutions.slice(0, 6).map((execution) => `
          <article class="execution-card">
            <div class="execution-card-head">
              <strong>${escapeHtml(execution.capability_name)}</strong>
              <span class="status-badge ${statusClass(execution.status)}">${escapeHtml(formatStatus(execution.status))}</span>
            </div>
            <p>${escapeHtml(execution.summary || '暂无摘要')}</p>
            <div class="timeline-meta">
              <span class="artifact-pill">${escapeHtml(formatDateTime(execution.updated_at || execution.created_at))}</span>
              ${execution.triggered_by ? `<span class="artifact-pill">by · ${escapeHtml(execution.triggered_by)}</span>` : ''}
              ${(execution.related_agents || []).slice(0, 3).map((item) => `<span class="artifact-pill">agent · ${escapeHtml(item)}</span>`).join('')}
              ${(execution.related_compounds || []).slice(0, 3).map((item) => `<span class="artifact-pill">compound · ${escapeHtml(item)}</span>`).join('')}
              ${execution.second_me_sync?.status ? `<span class="artifact-pill">Second Me · ${escapeHtml(execution.second_me_sync.status)}</span>` : ''}
            </div>
          </article>
        `).join('') : '<div class="empty-state">当前 phase 还没有 capability execution</div>'}
      </div>
    </div>
  `;
}

function renderSecondMePanel() {
  const container = document.getElementById('workbenchSecondMePanel');
  if (!container) return;
  if (!workbenchData?.project) {
    container.innerHTML = '<div class="empty-state">请选择一个项目</div>';
    return;
  }

  const bindings = workbenchData.second_me_bindings || [];
  const selectedInstanceId = bindings[0]?.instance_id || '';
  container.innerHTML = `
    <div class="workbench-panel-stack">
      <div class="workbench-form-grid compact">
        <select id="secondMeInstanceSelect" class="input">
          ${bindings.map((binding) => `
            <option value="${escapeHtml(binding.instance_id)}" ${binding.instance_id === selectedInstanceId ? 'selected' : ''}>
              ${escapeHtml(binding.instance_name || binding.instance_id)} · ${escapeHtml(binding.status || 'linked')}
            </option>
          `).join('') || '<option value="">暂无绑定实例</option>'}
        </select>
        <button class="btn btn-outline full" type="button" onclick="syncProjectSecondMe()">同步项目到 Second Me</button>
      </div>

      ${lastSecondMeSyncResult ? `
        <div class="capability-highlight">
          <div class="workbench-capability-head">
            <div>
              <strong>最近一次同步</strong>
              <p>${escapeHtml(lastSecondMeSyncResult.summary || lastSecondMeSyncResult.message || '同步已完成')}</p>
            </div>
            <span class="status-badge ${statusClass(lastSecondMeSyncResult.status || 'synced')}">${escapeHtml(formatStatus(lastSecondMeSyncResult.status || 'synced'))}</span>
          </div>
        </div>
      ` : ''}

      <div class="execution-feed">
        ${bindings.length ? bindings.map((binding) => `
          <article class="execution-card">
            <div class="execution-card-head">
              <strong>${escapeHtml(binding.instance_name || binding.instance_id)}</strong>
              <span class="status-badge ${statusClass(binding.status)}">${escapeHtml(formatStatus(binding.status || 'linked'))}</span>
            </div>
            <p>${escapeHtml(binding.last_sync_summary || '该绑定已准备好接收项目上下文同步。')}</p>
            <div class="timeline-meta">
              <span class="artifact-pill">instance · ${escapeHtml(binding.instance_id)}</span>
              ${binding.last_synced_at ? `<span class="artifact-pill">last sync · ${escapeHtml(formatDateTime(binding.last_synced_at))}</span>` : ''}
              ${(binding.linked_workflows || []).slice(0, 2).map((item) => `<span class="artifact-pill">workflow · ${escapeHtml(item)}</span>`).join('')}
              ${(binding.linked_memory_entries || []).slice(0, 2).map((item) => `<span class="artifact-pill">memory · ${escapeHtml(item)}</span>`).join('')}
              ${binding.share_url ? `<a class="artifact-pill artifact-link" href="${escapeHtml(binding.share_url)}" target="_blank" rel="noopener noreferrer">share url</a>` : ''}
            </div>
          </article>
        `).join('') : '<div class="empty-state">当前项目还没有 Second Me binding，请先到工具页创建并绑定实例。</div>'}
      </div>
    </div>
  `;
}

function getByBridgeFormState() {
  const project = workbenchData?.project || {};
  return {
    target: document.getElementById('byResearchTargetInput')?.value.trim() || project.target || project.name || '',
    modality: document.getElementById('byModalitySelect')?.value || project.modality || 'small_molecule',
    pdbRows: Math.max(1, Number(document.getElementById('byPdbRowsInput')?.value || 4)),
    sabdabLimit: Math.max(1, Number(document.getElementById('bySabdabLimitInput')?.value || 4)),
    complexity: document.getElementById('byComplexitySelect')?.value || 'standard',
    seeds: Math.max(1, Number(document.getElementById('bySeedsInput')?.value || 8)),
    designsPerSeed: Math.max(1, Number(document.getElementById('byDesignsInput')?.value || 8)),
    scaffolds: (document.getElementById('byScaffoldsInput')?.value || '')
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean),
    waitForCompletion: Boolean(document.getElementById('byWaitForCompletion')?.checked),
  };
}

function tamarindJobName(job = {}) {
  return job.jobName || job.job_name || job.name || job.id || 'unknown_job';
}

function tamarindJobStatus(job = {}) {
  return job.status || job.jobStatus || job.state || job.phase || 'unknown';
}

function tamarindToolLabel(tool) {
  if (!tool) return 'unknown';
  if (typeof tool === 'string') return tool;
  return tool.name || tool.id || tool.tool || 'tool';
}

function renderByBridgePanel() {
  const container = document.getElementById('workbenchByBridgePanel');
  if (!container) return;
  if (!workbenchData?.project) {
    container.innerHTML = '<div class="empty-state">请选择一个项目</div>';
    return;
  }

  const implementation = workbenchData.implementation || {};
  const byProject = implementation.blatant_why || {};
  const project = workbenchData.project || {};
  const compute = tamarindRuntimeStatus || blatantWhyOverview?.compute || {};
  const providerCatalog = blatantWhyProviders?.live_providers || blatantWhyOverview?.mcp_bridge?.live_providers || {};
  const modality = project.modality || byProject.modality || 'small_molecule';
  const pipelineSteps = Array.isArray(byProject.pipeline)
    ? byProject.pipeline.map((step) => ({
        title: step.phase,
        copy: `${step.owner} · ${step.focus}`,
      }))
    : (byProject.research_plan?.queries || []).map((query) => ({
        title: query.tool,
        copy: `${query.server_id} · ${query.objective}`,
      }));
  const researchResult = lastStructuralResearchResult || null;
  const pipelineResult = lastBiologicsPipelineResult?.campaign || lastBiologicsPipelineResult || null;
  const recentJobs = tamarindJobList || [];

  container.innerHTML = `
    <div class="workbench-panel-stack">
      <div class="workbench-form-grid compact">
        <input type="text" id="byResearchTargetInput" class="input" value="${escapeHtml(project.target || project.name || '')}" placeholder="Research target，例如 EGFR / ERBB2">
        <div class="input-row">
          <input type="number" id="byPdbRowsInput" class="input" min="1" value="4" placeholder="PDB hits">
          <input type="number" id="bySabdabLimitInput" class="input" min="1" value="4" placeholder="SAbDab hits">
        </div>
        <select id="byModalitySelect" class="input">
          ${['small_molecule', 'nanobody', 'antibody', 'protein'].map((item) => `
            <option value="${item}" ${item === modality ? 'selected' : ''}>${item}</option>
          `).join('')}
        </select>
        <div class="input-row">
          <input type="number" id="bySeedsInput" class="input" min="1" value="8" placeholder="Seeds">
          <input type="number" id="byDesignsInput" class="input" min="1" value="8" placeholder="Designs / Seed">
        </div>
        <input type="text" id="byScaffoldsInput" class="input" placeholder="可选 scaffold，逗号分隔">
        <select id="byComplexitySelect" class="input">
          <option value="light">light</option>
          <option value="standard" selected>standard</option>
          <option value="heavy">heavy</option>
        </select>
        <label class="checkbox-row">
          <input type="checkbox" id="byWaitForCompletion">
          <span>提交 Tamarind 后等待任务完成并尝试回收 result</span>
        </label>
        <div class="workbench-inline-actions">
          <button class="btn btn-outline" type="button" onclick="runStructuralResearchPreview()">Research Preview</button>
          <button class="btn btn-outline" type="button" onclick="executeStructuralResearchStep()">执行 Research Step</button>
          <button class="btn btn-outline" type="button" onclick="runBlatantWhyScreening()">运行 BY Screening</button>
        </div>
        <div class="workbench-inline-actions">
          <button class="btn btn-outline" type="button" onclick="runBlatantWhyBiologicsPipeline()">生成 Biologics Pipeline</button>
          <button class="btn btn-primary" type="button" onclick="submitTamarindBiologicsJob()">提交 Tamarind Job</button>
          <button class="btn btn-outline" type="button" onclick="refreshBridgeRuntimeManual()">刷新 Runtime</button>
        </div>
      </div>

      <div class="workbench-metric-grid">
        <div class="workbench-metric">
          <div class="workbench-metric-label">Research Providers</div>
          <div class="workbench-metric-value">${Object.keys(providerCatalog).length}</div>
        </div>
        <div class="workbench-metric">
          <div class="workbench-metric-label">Tamarind Status</div>
          <div class="workbench-metric-value">${escapeHtml(formatStatus(compute.status || (compute.enabled ? 'configured' : 'not_configured')))}</div>
        </div>
        <div class="workbench-metric">
          <div class="workbench-metric-label">Recent Jobs</div>
          <div class="workbench-metric-value">${recentJobs.length}</div>
        </div>
        <div class="workbench-metric">
          <div class="workbench-metric-label">Latest SAbDab Hits</div>
          <div class="workbench-metric-value">${researchResult?.sabdab?.count || 0}</div>
        </div>
      </div>

      <div class="capability-highlight">
        <div class="workbench-capability-head">
          <div>
            <strong>BY Adapter · ${escapeHtml(project.name)}</strong>
            <p>${escapeHtml(blatantWhyOverview?.runtime_adaptation?.campaign_model || '把 research → design → screening → ranking 适配到 DrugMind implementation。')}</p>
          </div>
          <span class="artifact-pill">${escapeHtml(modality)}</span>
        </div>
        <div class="timeline-meta">
          <span class="artifact-pill">compute · ${escapeHtml(compute.provider || 'tamarind')}</span>
          <span class="artifact-pill">status · ${escapeHtml(compute.status || (compute.enabled ? 'configured' : 'dry-run'))}</span>
          <span class="artifact-pill">servers · ${blatantWhyMcpServers.length}</span>
          <span class="artifact-pill">tools · ${tamarindAvailableTools.length}</span>
          <span class="artifact-pill">source · BY</span>
        </div>
        <div class="timeline-meta">
          ${Object.entries(providerCatalog).map(([providerId, provider]) => `
            <span class="artifact-pill">${escapeHtml(providerId)} · ${escapeHtml((provider.capabilities || []).length.toString())} caps</span>
          `).join('') || '<span class="artifact-pill">实时 provider 信息加载中</span>'}
          ${tamarindAvailableTools.slice(0, 6).map((tool) => `
            <span class="artifact-pill">tool · ${escapeHtml(tamarindToolLabel(tool))}</span>
          `).join('') || ''}
        </div>
      </div>

      <div class="phase-strip">
        ${pipelineSteps.length ? pipelineSteps.slice(0, 6).map((step, index) => `
          <article class="phase-chip ${index === 0 ? 'active' : ''}">
            <span>${String(index + 1).padStart(2, '0')}</span>
            <strong>${escapeHtml(step.title)}</strong>
            <p>${escapeHtml(step.copy)}</p>
          </article>
        `).join('') : '<div class="empty-state">暂无 BY pipeline 映射</div>'}
      </div>

      <div class="timeline-meta">
        ${blatantWhyMcpServers.slice(0, 5).map((server) => `<span class="artifact-pill">${escapeHtml(server.name)} · ${escapeHtml(server.domain)}</span>`).join('') || '<span class="artifact-pill">暂无 MCP server</span>'}
      </div>

      ${researchResult ? `
        <article class="execution-card">
          <div class="execution-card-head">
            <strong>Structural Research Bundle</strong>
            <span class="status-badge ${statusClass('completed')}">completed</span>
          </div>
          <p>${escapeHtml(researchResult.evidence_summary?.headline || '已完成结构研究检索')}</p>
          <div class="timeline-meta">
            <span class="artifact-pill">target · ${escapeHtml(researchResult.target || project.target || 'N/A')}</span>
            <span class="artifact-pill">UniProt · ${escapeHtml(researchResult.top_recommendation?.uniprot_accession || 'N/A')}</span>
            <span class="artifact-pill">PDB · ${(researchResult.pdb?.structures || []).length}</span>
            <span class="artifact-pill">SAbDab · ${researchResult.sabdab?.count || 0}</span>
          </div>
          <div class="timeline-meta">
            ${(researchResult.evidence_summary?.top_structure_titles || []).slice(0, 3).map((title) => `
              <span class="artifact-pill">structure · ${escapeHtml(title)}</span>
            `).join('') || '<span class="artifact-pill">暂无结构标题</span>'}
          </div>
        </article>
      ` : ''}

      ${lastByScreeningResult ? `
        <article class="execution-card">
          <div class="execution-card-head">
            <strong>BY Screening Result</strong>
            <span class="status-badge ${statusClass(lastByScreeningResult.campaign_recommendation?.gate || 'completed')}">${escapeHtml(lastByScreeningResult.campaign_recommendation?.gate || 'completed')}</span>
          </div>
          <p>${escapeHtml(lastByScreeningResult.campaign_recommendation?.rationale || '已完成小分子筛选')}</p>
          <div class="timeline-meta">
            <span class="artifact-pill">ranked · ${(lastByScreeningResult.screening?.ranked || []).length}</span>
            <span class="artifact-pill">pareto · ${(lastByScreeningResult.pareto_front || []).length}</span>
          </div>
        </article>
      ` : ''}

      ${pipelineResult ? `
        <article class="execution-card">
          <div class="execution-card-head">
            <strong>Biologics Pipeline Contract</strong>
            <span class="status-badge ${statusClass(pipelineResult.design_estimate?.tier || 'planned')}">${escapeHtml(pipelineResult.design_estimate?.tier || 'planned')}</span>
          </div>
          <p>${escapeHtml(pipelineResult.screening_contract?.ranking_rule || 'Biologics pipeline 已生成')}</p>
          <div class="timeline-meta">
            <span class="artifact-pill">modality · ${escapeHtml(pipelineResult.modality || 'N/A')}</span>
            <span class="artifact-pill">designs · ${pipelineResult.design_estimate?.total_designs || 0}</span>
            <span class="artifact-pill">runtime · ${pipelineResult.design_estimate?.estimated_minutes || 0} min</span>
          </div>
        </article>
      ` : ''}

      ${lastTamarindJobResult ? `
        <article class="execution-card">
          <div class="execution-card-head">
            <strong>Tamarind Job Runtime</strong>
            <span class="status-badge ${statusClass(lastTamarindJobResult.status || 'running')}">${escapeHtml(lastTamarindJobResult.status || 'running')}</span>
          </div>
          <p>${escapeHtml(lastTamarindJobResult.note || lastTamarindJobResult.error || '任务已提交或已刷新状态')}</p>
          <div class="timeline-meta">
            ${lastTamarindJobResult.job_name ? `<span class="artifact-pill">job · ${escapeHtml(lastTamarindJobResult.job_name)}</span>` : ''}
            ${lastTamarindJobResult.job_type ? `<span class="artifact-pill">type · ${escapeHtml(lastTamarindJobResult.job_type)}</span>` : ''}
            ${lastTamarindJobResult.provider ? `<span class="artifact-pill">provider · ${escapeHtml(lastTamarindJobResult.provider)}</span>` : ''}
          </div>
        </article>
      ` : ''}

      <div class="execution-feed">
        ${recentJobs.length ? recentJobs.map((job) => `
          <article class="execution-card">
            <div class="execution-card-head">
              <strong>${escapeHtml(tamarindJobName(job))}</strong>
              <span class="status-badge ${statusClass(tamarindJobStatus(job))}">${escapeHtml(tamarindJobStatus(job))}</span>
            </div>
            <p>${escapeHtml(job.jobType || job.job_type || job.type || 'Tamarind job')}</p>
            <div class="timeline-meta">
              ${(job.createdAt || job.created_at) ? `<span class="artifact-pill">created · ${escapeHtml(formatDateTime(job.createdAt || job.created_at))}</span>` : ''}
              ${(job.updatedAt || job.updated_at) ? `<span class="artifact-pill">updated · ${escapeHtml(formatDateTime(job.updatedAt || job.updated_at))}</span>` : ''}
            </div>
            <div class="workbench-inline-actions">
              <button class="btn btn-sm btn-outline" type="button" onclick='pollTamarindJob(${JSON.stringify(tamarindJobName(job))})'>轮询</button>
              <button class="btn btn-sm btn-outline" type="button" onclick='loadTamarindJobResult(${JSON.stringify(tamarindJobName(job))})'>结果</button>
            </div>
          </article>
        `).join('') : '<div class="empty-state">暂无 Tamarind job。没有 API Key 时这里会保持为空。</div>'}
      </div>
    </div>
  `;
}

function mediPharmaDefaultPayload(action) {
  const project = workbenchData?.project || {};
  const compounds = workbenchData?.compounds || [];
  const firstCompound = compounds[0] || {};
  switch (action) {
    case 'discover_targets':
      return {
        disease: project.disease || '',
        max_papers: 30,
        top_n: 8,
        disease_burden: 0.8,
        unmet_need: 0.8,
      };
    case 'run_screening':
      return {
        target_chembl_id: project.target_chembl_id || '',
        max_compounds: Math.max(compounds.length, 100),
        top_n: 20,
        use_docking: false,
      };
    case 'generate':
      return {
        target_name: project.target || project.name || '',
        scaffold: firstCompound.smiles || '',
        n_generate: 120,
        top_n: 12,
        target_mw: 400,
        target_logp: 2.5,
      };
    case 'predict_admet':
      return {
        smiles: firstCompound.smiles || '',
      };
    case 'batch_predict_admet':
      return {
        smiles_list: compounds.map((item) => item.smiles).filter(Boolean).slice(0, 12),
      };
    case 'optimize':
      return {
        smiles: firstCompound.smiles || '',
        max_generations: 12,
        population_size: 24,
      };
    case 'run_pipeline':
      return {
        disease: project.disease || '',
        target: project.target || '',
        target_chembl_id: project.target_chembl_id || '',
        max_papers: 20,
        max_compounds: 200,
        n_generate: 80,
        top_n: 10,
        auto_mode: true,
      };
    case 'knowledge_report':
      return {
        target: project.target || '',
        disease: project.disease || '',
        include_patents: true,
        include_clinical: true,
      };
    default:
      return {};
  }
}

function syncMediPharmaPayloadTemplate(force = false) {
  const action = document.getElementById('mediPharmaActionSelect')?.value || 'discover_targets';
  const input = document.getElementById('mediPharmaPayloadInput');
  if (!input) return;
  if (!force && input.value.trim()) return;
  input.value = JSON.stringify(mediPharmaDefaultPayload(action), null, 2);
}

function summarizeMediPharmaResult(result) {
  if (!result) return '暂无结果';
  if (result.note) return result.note;
  if (result.error) return result.error;
  const response = result.response || {};
  if (response.summary) return response.summary;
  if (response.report) return response.report;
  if (Array.isArray(response.key_insights) && response.key_insights.length) {
    return response.key_insights.slice(0, 2).join('；');
  }
  if (Array.isArray(response.stages_completed) && response.stages_completed.length) {
    return `已完成 ${response.stages_completed.length} 个 pipeline stages`;
  }
  if (response.content) {
    return String(response.content).slice(0, 160);
  }
  return '调用已完成';
}

function renderMediPharmaPanel() {
  const container = document.getElementById('workbenchMediPharmaPanel');
  if (!container) return;
  if (!workbenchData?.project) {
    container.innerHTML = '<div class="empty-state">请选择一个项目</div>';
    return;
  }

  const project = workbenchData.project || {};
  const mediPharma = workbenchData.medi_pharma || mediPharmaOverview || {};
  const status = mediPharmaHealth?.status || mediPharma?.status?.status || 'unknown';
  const baseUrl = mediPharmaHealth?.base_url || mediPharma?.client?.base_url || '';
  const features = mediPharma?.client?.features || [];
  const latest = lastMediPharmaResult || null;

  container.innerHTML = `
    <div class="workbench-panel-stack">
      <div class="workbench-metric-grid">
        <div class="workbench-metric">
          <div class="workbench-metric-label">Runtime</div>
          <div class="workbench-metric-value">${escapeHtml(formatStatus(status))}</div>
        </div>
        <div class="workbench-metric">
          <div class="workbench-metric-label">Endpoints</div>
          <div class="workbench-metric-value">${features.length || 10}</div>
        </div>
        <div class="workbench-metric">
          <div class="workbench-metric-label">Project</div>
          <div class="workbench-metric-value">${escapeHtml(project.modality || 'small_molecule')}</div>
        </div>
        <div class="workbench-metric">
          <div class="workbench-metric-label">Compounds</div>
          <div class="workbench-metric-value">${(workbenchData.compounds || []).length}</div>
        </div>
      </div>

      <div class="capability-highlight">
        <div class="workbench-capability-head">
          <div>
            <strong>MediPharma v2.0.0</strong>
            <p>通过 DrugMind 统一桥接靶点发现、筛选、分子生成、ADMET、优化和知识引擎。</p>
          </div>
          <span class="status-badge ${statusClass(status)}">${escapeHtml(formatStatus(status))}</span>
        </div>
        <div class="timeline-meta">
          <span class="artifact-pill">base · ${escapeHtml(baseUrl || '未配置')}</span>
          <span class="artifact-pill">source · medi-pharma</span>
          ${(features || []).slice(0, 6).map((item) => `<span class="artifact-pill">${escapeHtml(item)}</span>`).join('')}
        </div>
      </div>

      <div class="workbench-form-grid compact">
        <select id="mediPharmaActionSelect" class="input" onchange="syncMediPharmaPayloadTemplate(true)">
          ${[
            ['discover_targets', 'Target Discovery'],
            ['run_screening', 'Virtual Screening'],
            ['generate', 'Molecule Generation'],
            ['predict_admet', 'ADMET Single'],
            ['batch_predict_admet', 'ADMET Batch'],
            ['optimize', 'Lead Optimization'],
            ['run_pipeline', 'Pipeline Run'],
            ['knowledge_report', 'Knowledge Report'],
            ['ecosystem', 'Ecosystem'],
            ['health', 'Health'],
          ].map(([value, label]) => `<option value="${value}">${escapeHtml(label)}</option>`).join('')}
        </select>
        <textarea id="mediPharmaPayloadInput" class="textarea small" rows="6" placeholder='可选 JSON input_payload'></textarea>
        <div class="workbench-inline-actions">
          <button class="btn btn-primary" type="button" onclick="executeMediPharmaAction()">执行 MediPharma</button>
          <button class="btn btn-outline" type="button" onclick="refreshMediPharmaRuntimeManual()">刷新状态</button>
          <button class="btn btn-outline" type="button" onclick="loadMediPharmaEcosystem()">生态概览</button>
        </div>
      </div>

      ${latest ? `
        <article class="execution-card">
          <div class="execution-card-head">
            <strong>Latest MediPharma Result</strong>
            <span class="status-badge ${statusClass(latest.status || 'completed')}">${escapeHtml(formatStatus(latest.status || 'completed'))}</span>
          </div>
          <p>${escapeHtml(summarizeMediPharmaResult(latest))}</p>
          <div class="timeline-meta">
            ${latest.response?.total_candidates !== undefined ? `<span class="artifact-pill">targets · ${latest.response.total_candidates}</span>` : ''}
            ${latest.response?.hits_found !== undefined ? `<span class="artifact-pill">hits · ${latest.response.hits_found}</span>` : ''}
            ${latest.response?.valid_molecules !== undefined ? `<span class="artifact-pill">valid · ${latest.response.valid_molecules}</span>` : ''}
            ${latest.response?.candidates_found !== undefined ? `<span class="artifact-pill">optimized · ${latest.response.candidates_found}</span>` : ''}
            ${Array.isArray(latest.response?.stages_completed) ? `<span class="artifact-pill">stages · ${latest.response.stages_completed.length}</span>` : ''}
            ${Array.isArray(latest.response?.key_insights) ? `<span class="artifact-pill">insights · ${latest.response.key_insights.length}</span>` : ''}
          </div>
        </article>
      ` : ''}

      ${mediPharmaEcosystem ? `
        <article class="execution-card">
          <div class="execution-card-head">
            <strong>MediPharma Ecosystem</strong>
            <span class="status-badge ${statusClass(mediPharmaEcosystem.status || 'ready')}">${escapeHtml(formatStatus(mediPharmaEcosystem.status || 'ready'))}</span>
          </div>
          <p>${escapeHtml(summarizeMediPharmaResult(mediPharmaEcosystem))}</p>
        </article>
      ` : ''}
    </div>
  `;

  syncMediPharmaPayloadTemplate();
}

async function runStructuralResearchPreview() {
  if (!selectedWorkbenchProjectId) {
    alert('请先选择项目');
    return;
  }
  const form = getByBridgeFormState();
  try {
    lastStructuralResearchResult = await fetchJsonApi('/api/v2/integrations/blatant-why/research', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: selectedWorkbenchProjectId,
        target: form.target,
        modality: form.modality,
        pdb_rows: form.pdbRows,
        sabdab_limit: form.sabdabLimit,
      }),
    });
    renderByBridgePanel();
    showWorkbenchMessage(
      `Structural research 完成：UniProt=${lastStructuralResearchResult.top_recommendation?.uniprot_accession || 'N/A'}`,
      'ok'
    );
  } catch (error) {
    console.warn('Structural research preview failed:', error);
    showWorkbenchMessage(`Structural research 失败：${error.message}`, 'error');
  }
}

async function executeStructuralResearchStep() {
  if (!selectedWorkbenchProjectId) {
    alert('请先选择项目');
    return;
  }
  const form = getByBridgeFormState();
  try {
    const execution = await fetchJsonApi(
      `/api/v2/projects/${selectedWorkbenchProjectId}/capabilities/capability.structural_research/execute`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          input_payload: {
            target: form.target,
            modality: form.modality,
            pdb_rows: form.pdbRows,
            sabdab_limit: form.sabdabLimit,
          },
          triggered_by: 'web.workbench.by_bridge',
        }),
      }
    );
    lastStructuralResearchResult = execution.structured_output || null;
    await loadWorkbench(selectedWorkbenchProjectId);
    showWorkbenchMessage(`Research step 已写入 artifact：${execution.capability_name || 'Structural Research'}`, 'ok');
  } catch (error) {
    console.warn('Structural research capability failed:', error);
    showWorkbenchMessage(`Research step 执行失败：${error.message}`, 'error');
  }
}

function selectCapability(capabilityId) {
  selectedCapabilityId = capabilityId || '';
  renderCapabilityPanel();
}

function parseWorkbenchJsonInput(inputId) {
  const raw = document.getElementById(inputId)?.value.trim() || '';
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
      throw new Error('必须是 JSON object');
    }
    return parsed;
  } catch (error) {
    throw new Error(`JSON 输入无效：${error.message}`);
  }
}

async function bootstrapProjectImplementation() {
  if (!selectedWorkbenchProjectId) {
    alert('请先选择项目');
    return;
  }
  const blueprintId = document.getElementById('implementationBlueprintSelect')?.value || '';
  const note = document.getElementById('implementationBootstrapNote')?.value.trim() || '';
  try {
    await fetchJsonApi(`/api/v2/projects/${selectedWorkbenchProjectId}/implementation/bootstrap`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        blueprint_id: blueprintId,
        activated_by: 'web.workbench',
        note,
      }),
    });
    showWorkbenchMessage('Implementation blueprint 已激活', 'ok');
    await loadWorkbench(selectedWorkbenchProjectId);
  } catch (error) {
    console.warn('Bootstrap implementation failed:', error);
    showWorkbenchMessage(`激活 implementation 失败：${error.message}`, 'error');
  }
}

async function executeSelectedCapability() {
  if (!selectedWorkbenchProjectId) {
    alert('请先选择项目');
    return;
  }
  const capabilityId = document.getElementById('capabilitySelect')?.value || selectedCapabilityId;
  if (!capabilityId) {
    alert('请选择一个 capability');
    return;
  }
  let inputPayload = {};
  try {
    inputPayload = parseWorkbenchJsonInput('capabilityPayloadInput');
  } catch (error) {
    showWorkbenchMessage(error.message, 'error');
    return;
  }
  const syncToSecondMe = Boolean(document.getElementById('capabilitySyncToSecondMe')?.checked);
  try {
    const execution = await fetchJsonApi(`/api/v2/projects/${selectedWorkbenchProjectId}/capabilities/${encodeURIComponent(capabilityId)}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input_payload: inputPayload,
        triggered_by: 'web.workbench.capability',
        sync_to_second_me: syncToSecondMe,
      }),
    });
    showWorkbenchMessage(`Capability 已执行：${execution.capability_name || capabilityId}`, 'ok');
    await loadWorkbench(selectedWorkbenchProjectId);
  } catch (error) {
    console.warn('Execute capability failed:', error);
    showWorkbenchMessage(`执行 capability 失败：${error.message}`, 'error');
  }
}

async function syncProjectSecondMe() {
  if (!selectedWorkbenchProjectId) {
    alert('请先选择项目');
    return;
  }
  const instanceId = document.getElementById('secondMeInstanceSelect')?.value || '';
  if (!instanceId) {
    showWorkbenchMessage('当前项目还没有可用的 Second Me 实例', 'error');
    return;
  }
  try {
    lastSecondMeSyncResult = await fetchJsonApi(`/api/v2/projects/${selectedWorkbenchProjectId}/second-me/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        instance_id: instanceId,
        workflow_run_id: selectedRunId || undefined,
      }),
    });
    showWorkbenchMessage('Second Me 项目同步已完成', 'ok');
    await loadWorkbench(selectedWorkbenchProjectId);
  } catch (error) {
    console.warn('Second Me sync failed:', error);
    showWorkbenchMessage(`Second Me 同步失败：${error.message}`, 'error');
  }
}

async function runBlatantWhyScreening() {
  if (!selectedWorkbenchProjectId) {
    alert('请先选择项目');
    return;
  }
  try {
    lastByScreeningResult = await fetchJsonApi('/api/v2/integrations/blatant-why/screening', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: selectedWorkbenchProjectId }),
    });
    renderByBridgePanel();
    showWorkbenchMessage(`BY screening 完成，gate = ${lastByScreeningResult.campaign_recommendation?.gate || 'N/A'}`, 'ok');
  } catch (error) {
    console.warn('BY screening failed:', error);
    showWorkbenchMessage(`BY screening 失败：${error.message}`, 'error');
  }
}

async function runBlatantWhyBiologicsPipeline() {
  return runBlatantWhyBiologicsPipelineWithMode(false);
}

async function submitTamarindBiologicsJob() {
  return runBlatantWhyBiologicsPipelineWithMode(true);
}

async function runBlatantWhyBiologicsPipelineWithMode(submitJob) {
  if (!selectedWorkbenchProjectId) {
    alert('请先选择项目');
    return;
  }
  const form = getByBridgeFormState();
  try {
    const payload = await fetchJsonApi('/api/v2/integrations/blatant-why/biologics-pipeline', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: selectedWorkbenchProjectId,
        modality: form.modality,
        scaffolds: form.scaffolds.length ? form.scaffolds : undefined,
        seeds: form.seeds,
        designs_per_seed: form.designsPerSeed,
        complexity: form.complexity,
        submit_job: submitJob,
        wait_for_completion: form.waitForCompletion,
      }),
    });
    lastBiologicsPipelineResult = payload.campaign || payload;
    lastTamarindJobResult = payload.tamarind_job || null;
    await refreshBridgeRuntime({ projectId: selectedWorkbenchProjectId, includeJobs: true });
    renderByBridgePanel();
    showWorkbenchMessage(
      submitJob
        ? `Tamarind job 已提交：${lastTamarindJobResult?.job_name || 'submitted'}`
        : `Biologics pipeline 已生成：${lastBiologicsPipelineResult.modality}`,
      'ok'
    );
  } catch (error) {
    console.warn('BY biologics pipeline failed:', error);
    showWorkbenchMessage(`${submitJob ? 'Tamarind 提交' : 'Biologics pipeline'} 失败：${error.message}`, 'error');
  }
}

async function refreshBridgeRuntimeManual() {
  try {
    await refreshBridgeRuntime({ projectId: selectedWorkbenchProjectId, includeJobs: true, rerender: true });
    showWorkbenchMessage('BY / Tamarind runtime 已刷新', 'ok');
  } catch (error) {
    console.warn('Bridge runtime refresh failed:', error);
    showWorkbenchMessage(`刷新 runtime 失败：${error.message}`, 'error');
  }
}

async function executeMediPharmaAction() {
  if (!selectedWorkbenchProjectId) {
    alert('请先选择项目');
    return;
  }
  const action = document.getElementById('mediPharmaActionSelect')?.value || 'discover_targets';
  let inputPayload = {};
  try {
    inputPayload = parseWorkbenchJsonInput('mediPharmaPayloadInput');
  } catch (error) {
    showWorkbenchMessage(error.message, 'error');
    return;
  }
  try {
    lastMediPharmaResult = await fetchJsonApi('/api/v2/integrations/medi-pharma/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action,
        project_id: selectedWorkbenchProjectId,
        input_payload: inputPayload,
      }),
    });
    renderMediPharmaPanel();
    showWorkbenchMessage(`MediPharma 已执行：${action}`, 'ok');
  } catch (error) {
    console.warn('MediPharma execution failed:', error);
    showWorkbenchMessage(`MediPharma 执行失败：${error.message}`, 'error');
  }
}

async function refreshMediPharmaRuntimeManual() {
  try {
    mediPharmaHealth = await fetchJsonApi('/api/v2/integrations/medi-pharma/health');
    renderMediPharmaPanel();
    showWorkbenchMessage('MediPharma 状态已刷新', 'ok');
  } catch (error) {
    console.warn('MediPharma runtime refresh failed:', error);
    showWorkbenchMessage(`MediPharma 状态刷新失败：${error.message}`, 'error');
  }
}

async function loadMediPharmaEcosystem() {
  try {
    mediPharmaEcosystem = await fetchJsonApi('/api/v2/integrations/medi-pharma/ecosystem');
    renderMediPharmaPanel();
    showWorkbenchMessage('MediPharma 生态概览已加载', 'ok');
  } catch (error) {
    console.warn('MediPharma ecosystem load failed:', error);
    showWorkbenchMessage(`MediPharma 生态概览失败：${error.message}`, 'error');
  }
}

async function pollTamarindJob(jobName) {
  try {
    lastTamarindJobResult = await fetchJsonApi(`/api/v2/integrations/tamarind/jobs/${encodeURIComponent(jobName)}/poll`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        interval_seconds: 5,
        timeout_seconds: 30,
        include_result: true,
      }),
    });
    await refreshBridgeRuntime({ projectId: selectedWorkbenchProjectId, includeJobs: true });
    renderByBridgePanel();
    showWorkbenchMessage(`Tamarind job 已轮询：${jobName}`, 'ok');
  } catch (error) {
    console.warn('Tamarind poll failed:', error);
    showWorkbenchMessage(`Tamarind 轮询失败：${error.message}`, 'error');
  }
}

async function loadTamarindJobResult(jobName) {
  try {
    lastTamarindJobResult = await fetchJsonApi(`/api/v2/integrations/tamarind/jobs/${encodeURIComponent(jobName)}/result`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    renderByBridgePanel();
    showWorkbenchMessage(`已尝试读取 Tamarind result：${jobName}`, 'ok');
  } catch (error) {
    console.warn('Tamarind result load failed:', error);
    showWorkbenchMessage(`读取 Tamarind result 失败：${error.message}`, 'error');
  }
}

function renderWorkspaceMembers() {
  const membersEl = document.getElementById('workspaceMembersList');
  if (!membersEl) return;
  const members = workbenchData?.workspace?.members || [];
  if (members.length === 0) {
    membersEl.innerHTML = '<div class="empty-state">暂无成员，先加一个 human owner</div>';
    return;
  }
  membersEl.innerHTML = members.map((member) => `
    <div class="workbench-member">
      <div>
        <div class="workbench-member-name">${escapeHtml(member.name || member.user_id || member.id || 'Unnamed')}</div>
        <div class="workbench-member-role">${escapeHtml(member.role || member.type || 'Contributor')}</div>
      </div>
      <span class="owner-pill ${escapeHtml((member.type || 'human') === 'user' ? 'user' : 'human')}">${escapeHtml((member.type || 'human') === 'user' ? 'User' : 'Human')}</span>
    </div>
  `).join('');
}

function renderWorkflowTemplateSelect() {
  const select = document.getElementById('workflowTemplateSelect');
  if (!select) return;
  const templates = workbenchData?.workflow_templates || [];
  if (!templates.length) {
    select.innerHTML = '<option value="">暂无模板</option>';
    return;
  }
  select.innerHTML = templates.map((template) => `
    <option value="${escapeHtml(template.template_id)}">${escapeHtml(template.name)} · ${escapeHtml(template.category)}</option>
  `).join('');
}

function renderArtifactTimeline() {
  const container = document.getElementById('artifactTimeline');
  if (!container) return;
  const timeline = (workbenchData?.timeline || []).slice(0, 36);
  if (!timeline.length) {
    container.innerHTML = '<div class="empty-state">暂无时间线数据</div>';
    return;
  }
  container.innerHTML = timeline.map((item) => `
    <article class="timeline-item">
      <div class="timeline-item-header">
        <div class="timeline-title">${timelineIcon(item.item_type)} ${escapeHtml(item.title)}</div>
        <div class="timeline-time">${escapeHtml(formatDateTime(item.timestamp))}</div>
      </div>
      <div class="timeline-summary">${escapeHtml(item.summary || '暂无摘要')}</div>
      <div class="timeline-meta">
        <span class="status-badge ${statusClass(item.status)}">${escapeHtml(formatStatus(item.status || item.item_type))}</span>
        ${item.actor ? `<span class="artifact-pill">actor · ${escapeHtml(item.actor)}</span>` : ''}
        <span class="artifact-pill">${escapeHtml(item.item_type)}</span>
        ${renderTimelineMeta(item)}
      </div>
    </article>
  `).join('');
}

function renderTimelineMeta(item) {
  const meta = item.meta || {};
  const chips = [];
  if (meta.memory_type) chips.push(`<span class="artifact-pill">memory · ${escapeHtml(meta.memory_type)}</span>`);
  if (meta.step_id) chips.push(`<span class="artifact-pill">step · ${escapeHtml(meta.step_id)}</span>`);
  if (meta.owner_type) chips.push(`<span class="artifact-pill">owner · ${escapeHtml(meta.owner_type)}</span>`);
  if (meta.sender_type) chips.push(`<span class="artifact-pill">sender · ${escapeHtml(meta.sender_type)}</span>`);
  if (meta.mode) chips.push(`<span class="artifact-pill">mode · ${escapeHtml(meta.mode)}</span>`);
  if (meta.messages_count) chips.push(`<span class="artifact-pill">messages · ${meta.messages_count}</span>`);
  if (Array.isArray(meta.agent_ids) && meta.agent_ids.length > 1) chips.push(`<span class="artifact-pill">agents · ${meta.agent_ids.length}</span>`);
  if (meta.confidence !== undefined) chips.push(`<span class="artifact-pill">confidence · ${Number(meta.confidence).toFixed(2)}</span>`);
  if (Array.isArray(meta.artifacts) && meta.artifacts.length) {
    meta.artifacts.slice(0, 3).forEach((artifact) => {
      chips.push(`<span class="artifact-pill">${escapeHtml(artifact.type)} · ${escapeHtml(artifact.summary || artifact.id)}</span>`);
    });
  }
  return chips.join('');
}

function renderWorkflowRuns() {
  const panel = document.getElementById('workflowRunsPanel');
  if (!panel) return;
  const runs = workbenchData?.workflow_runs || [];
  if (!runs.length) {
    panel.innerHTML = '<div class="empty-state">还没有 workflow run</div>';
    return;
  }

  panel.innerHTML = runs.map((run) => {
    const currentIndex = Number(run.current_step_index || 0);
    const isSelected = run.run_id === (selectedRunId || runs[0].run_id);
    const meta = [
      `created by ${run.created_by || 'system'}`,
      `updated ${formatDateTime(run.updated_at)}`,
    ];
    return `
      <article class="workflow-run ${isSelected ? 'selected' : ''}" onclick="selectRun('${escapeHtml(run.run_id)}')">
        <div class="workflow-run-header">
          <div>
            <div class="workflow-run-title">${escapeHtml(run.template_name)}</div>
            <div class="workflow-run-topic">${escapeHtml(run.topic)}</div>
            <div class="workflow-run-meta">
              <span class="status-badge ${statusClass(run.status)}">${escapeHtml(formatStatus(run.status))}</span>
              ${meta.map((item) => `<span class="artifact-pill">${escapeHtml(item)}</span>`).join('')}
            </div>
          </div>
          <div class="workbench-inline-actions" onclick="event.stopPropagation()">
            <button class="btn btn-sm btn-outline" type="button" onclick="executeWorkflowRun('${escapeHtml(run.run_id)}')">执行当前步</button>
            <button class="btn btn-sm btn-outline" type="button" onclick="executeWorkflowRun('${escapeHtml(run.run_id)}', 6)">推进到门控</button>
          </div>
        </div>
        <div class="run-step-list">
          ${run.steps.map((step, index) => renderStepCard(run, step, index, currentIndex)).join('')}
        </div>
      </article>
    `;
  }).join('');
}

function renderStepCard(run, step, index, currentIndex) {
  const isCurrent = index === currentIndex && !['completed', 'rejected', 'failed'].includes(step.status);
  const ownerSelectId = `owner_${toSlug(run.run_id)}_${toSlug(step.step_id)}`;
  const approvalBadge = step.approval_required
    ? `<span class="artifact-pill">approval · ${escapeHtml(formatStatus(step.approval_status))}</span>`
    : '';
  const tools = (step.tool_ids || []).slice(0, 4).map((toolId) => `<span class="artifact-pill">${escapeHtml(toolId)}</span>`).join('');
  const skills = (step.required_skills || []).slice(0, 4).map((skillId) => `<span class="artifact-pill">${escapeHtml(skillId)}</span>`).join('');
  const artifacts = (step.artifacts || []).map((artifact) => `
    <span class="artifact-pill">${escapeHtml(artifact.type)} · ${escapeHtml(artifact.summary || artifact.id)}</span>
  `).join('');
  return `
    <section class="run-step ${isCurrent ? 'current' : ''}">
      <div class="run-step-header">
        <div class="run-step-subhead">
          <span class="run-step-index">${index + 1}</span>
          <div class="run-step-name">${escapeHtml(step.name)}</div>
        </div>
        <div class="run-step-tags">
          <span class="status-badge ${statusClass(step.status)}">${escapeHtml(formatStatus(step.status))}</span>
          <span class="owner-pill ${escapeHtml(step.owner_type)}">${escapeHtml(step.owner_type)} · ${escapeHtml(step.owner_label || step.owner_id || step.agent_id)}</span>
          ${approvalBadge}
        </div>
      </div>
      <div class="run-step-description">${escapeHtml(step.description)}</div>
      ${step.executor_summary ? `<div class="run-step-summary">${escapeHtml(step.executor_summary)}</div>` : ''}
      <div class="run-step-owner-row">
        <div class="owner-select-row">
          <select id="${ownerSelectId}" class="input">
            ${buildOwnerOptions(step)}
          </select>
          <button class="btn btn-sm btn-outline" type="button" onclick="assignStepOwner('${escapeHtml(run.run_id)}', '${escapeHtml(step.step_id)}', '${ownerSelectId}')">切换 Owner</button>
        </div>
        <div class="run-step-tags">
          ${tools}
          ${skills}
        </div>
      </div>
      <div class="run-step-actions">
        <div class="run-step-artifacts">${artifacts || '<span class="artifact-pill">暂无 artifact</span>'}</div>
        <div class="workbench-inline-actions">
          ${renderStepActions(run, step, isCurrent)}
        </div>
      </div>
      ${(step.output || (step.notes || []).length) ? `
        <details>
          <summary>展开查看输出、备注和执行细节</summary>
          ${step.output ? `<div class="run-step-output">${escapeHtml(step.output)}</div>` : ''}
          ${(step.notes || []).length ? `<div class="timeline-meta" style="margin-top:12px">${step.notes.map((note) => `<span class="artifact-pill">${escapeHtml(note)}</span>`).join('')}</div>` : ''}
        </details>
      ` : ''}
    </section>
  `;
}

function renderStepActions(run, step, isCurrent) {
  if (!isCurrent) return '<span class="artifact-pill">等待上一步完成</span>';
  const actions = [];
  if (step.status === 'awaiting_approval') {
    actions.push(`<button class="btn btn-sm btn-primary" type="button" onclick="approveWorkflowStep('${escapeHtml(run.run_id)}', '${escapeHtml(step.step_id)}', true)">批准</button>`);
    actions.push(`<button class="btn btn-sm btn-outline" type="button" onclick="approveWorkflowStep('${escapeHtml(run.run_id)}', '${escapeHtml(step.step_id)}', false)">拒绝</button>`);
    return actions.join('');
  }
  if (step.owner_type === 'human') {
    actions.push(`<button class="btn btn-sm btn-primary" type="button" onclick="manualCompleteWorkflowStep('${escapeHtml(run.run_id)}', '${escapeHtml(step.step_id)}')">人工完成</button>`);
    actions.push(`<button class="btn btn-sm btn-outline" type="button" onclick="executeWorkflowStep('${escapeHtml(run.run_id)}', '${escapeHtml(step.step_id)}', true)">AI 接管</button>`);
    return actions.join('');
  }
  if (!['completed', 'failed', 'rejected'].includes(step.status)) {
    actions.push(`<button class="btn btn-sm btn-primary" type="button" onclick="executeWorkflowStep('${escapeHtml(run.run_id)}', '${escapeHtml(step.step_id)}')">执行</button>`);
  }
  return actions.join('') || '<span class="artifact-pill">已完成</span>';
}

function buildOwnerOptions(step) {
  const options = [];
  platformAgents.forEach((agent) => {
    options.push({
      value: `agent::${agent.agent_id}`,
      label: `AI · ${agent.name}`,
      selected: step.owner_type === 'agent' && step.owner_id === agent.agent_id,
    });
  });
  (workbenchData?.workspace?.members || []).forEach((member) => {
    const ownerId = member.user_id || member.id || member.name;
    options.push({
      value: `human::${ownerId}`,
      label: `Human · ${member.name || ownerId}`,
      selected: step.owner_type === 'human' && step.owner_id === ownerId,
    });
  });
  if (!options.length) {
    return '<option value="">暂无 owner</option>';
  }
  return options.map((option) => `
    <option value="${escapeHtml(option.value)}" ${option.selected ? 'selected' : ''}>${escapeHtml(option.label)}</option>
  `).join('');
}

function renderHomeSurface() {
  renderHomeWorkbenchSnapshot();
  renderHomeAgentDeck();
}

function renderHomeWorkbenchSnapshot() {
  const snapshot = document.getElementById('homeWorkbenchSnapshot');
  const runPreview = document.getElementById('homeRunPreview');
  if (!snapshot || !runPreview) return;
  if (!workbenchData?.project) {
    snapshot.innerHTML = '<div class="empty-state">先创建一个项目，首页会直接出现工作台快照。</div>';
    runPreview.innerHTML = '<div class="empty-state">暂无 active workflow</div>';
    return;
  }

  const { project, workspace = {}, timeline = [], h2a_threads: threads = [], implementation = {} } = workbenchData;
  const currentRun = getSelectedRun();
  const humanMembers = (workspace.members || []).filter((member) => (member.type || 'human') !== 'agent');
  const currentPhase = implementation.current_phase || {};
  const recentExecutions = implementation.recent_executions || [];
  snapshot.innerHTML = `
    <div class="home-workbench-summary">
      <div class="home-workbench-head">
        <div>
          <div class="home-workbench-title">${escapeHtml(project.name)}</div>
          <div class="home-workbench-copy">${escapeHtml(project.target || '未设置靶点')} · ${escapeHtml(project.disease || '未设置疾病')} · ${escapeHtml(currentPhase.name || formatStageLabel(project.stage))}</div>
        </div>
        <span class="status-badge ${statusClass(project.status)}">${escapeHtml(formatStatus(project.status))}</span>
      </div>
      <div class="home-workbench-grid">
        <div class="home-workbench-metric"><span>人工成员</span><strong>${humanMembers.length}</strong></div>
        <div class="home-workbench-metric"><span>Workflow Runs</span><strong>${(workbenchData.workflow_runs || []).length}</strong></div>
        <div class="home-workbench-metric"><span>Timeline Items</span><strong>${timeline.length}</strong></div>
        <div class="home-workbench-metric"><span>H2A Threads</span><strong>${threads.length}</strong></div>
        <div class="home-workbench-metric"><span>Capabilities</span><strong>${(implementation.available_capabilities || []).length}</strong></div>
        <div class="home-workbench-metric"><span>Executions</span><strong>${recentExecutions.length}</strong></div>
      </div>
    </div>
  `;

  if (!currentRun) {
    runPreview.innerHTML = '<div class="empty-state">当前项目还没有 workflow run</div>';
    return;
  }

  const currentStep = currentRun.steps?.[currentRun.current_step_index] || null;
  const recentTimeline = (timeline || []).slice(0, 3).map((item) => `
    <span class="artifact-pill">${timelineIcon(item.item_type)} ${escapeHtml(item.title)}</span>
  `).join('');
  runPreview.innerHTML = `
    <div class="home-run-card">
      <strong>${escapeHtml(currentRun.template_name)}</strong>
      <div class="home-run-copy">${escapeHtml(currentRun.topic)}</div>
      <div class="timeline-meta" style="margin-top:12px">
        <span class="status-badge ${statusClass(currentRun.status)}">${escapeHtml(formatStatus(currentRun.status))}</span>
        ${currentStep ? `<span class="artifact-pill">current · ${escapeHtml(currentStep.name)}</span>` : ''}
        ${currentStep?.owner_label ? `<span class="artifact-pill">owner · ${escapeHtml(currentStep.owner_label)}</span>` : ''}
        ${currentPhase?.name ? `<span class="artifact-pill">phase · ${escapeHtml(currentPhase.name)}</span>` : ''}
      </div>
      <div class="home-run-steps">${recentTimeline || '<span class="artifact-pill">暂无最近 artifact</span>'}</div>
    </div>
  `;
}

function renderHomeAgentDeck() {
  const container = document.getElementById('homeAgentDeck');
  if (!container) return;
  if (!platformAgents.length) {
    container.innerHTML = '<div class="empty-state">Agent registry 加载中</div>';
    return;
  }
  container.innerHTML = platformAgents.map((agent) => `
    <div class="home-agent-row">
      <div>
        <strong>${timelineIconForAgent(agent.agent_id)} ${escapeHtml(agent.name)}</strong>
        <p>${escapeHtml(agent.description || '')}</p>
      </div>
      <div class="timeline-meta">
        <span class="artifact-pill">${escapeHtml(agent.category)}</span>
        <span class="artifact-pill">${escapeHtml(agent.execution_mode || 'expert')}</span>
      </div>
    </div>
  `).join('');
}

async function loadH2AThreads(projectId = selectedWorkbenchProjectId) {
  if (!projectId) {
    h2aThreads = [];
    selectedH2AThreadId = '';
    renderH2ASelectors();
    renderH2AThreadList();
    renderH2AConversation();
    return;
  }
  try {
    const payload = await fetch(apiUrl(`/api/v2/projects/${projectId}/h2a/threads`)).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      return data;
    });
    h2aThreads = payload.threads || [];
    if (!selectedH2AThreadId || !h2aThreads.some((thread) => thread.thread_id === selectedH2AThreadId)) {
      selectedH2AThreadId = h2aThreads[0]?.thread_id || '';
    }
    renderH2ASelectors();
    renderH2AThreadList();
    renderH2AConversation();
  } catch (error) {
    console.warn('H2A threads load failed:', error);
    showH2AStatus(`H2A 线程加载失败：${error.message}`, 'error');
  }
}

function renderH2ASelectors() {
  const projectSelect = document.getElementById('homeH2AProjectSelect');
  const humanSelect = document.getElementById('homeHumanSelect');
  const agentSelector = document.getElementById('homeAgentSelector');
  const agentSummary = document.getElementById('homeAgentSelectionSummary');
  if (projectSelect) {
    renderProjectSelect();
  }
  if (humanSelect) {
    const members = workbenchData?.workspace?.members || [];
    const fallbackMembers = currentUser ? [
      {
        user_id: currentUser.user_id,
        name: currentUser.display_name || currentUser.username || currentUser.user_id,
        role: currentUser.title || 'Workspace Member',
        type: 'user',
      },
      ...members.filter((member) => (member.user_id || member.id || member.name) !== currentUser.user_id),
    ] : members;
    if (!fallbackMembers.length) {
      humanSelect.innerHTML = '<option value="">先登录或先在工作台里添加 human member</option>';
    } else {
      humanSelect.innerHTML = fallbackMembers.map((member) => {
        const humanId = member.user_id || member.id || member.name;
        return `<option value="${escapeHtml(humanId)}">${escapeHtml(member.name || humanId)} · ${escapeHtml(member.role || 'Member')}</option>`;
      }).join('');
    }
    humanSelect.disabled = !!currentUser;
  }
  if (agentSelector) {
    const availableAgentIds = new Set(platformAgents.map((agent) => agent.agent_id));
    selectedHomeAgentIds = selectedHomeAgentIds.filter((agentId) => availableAgentIds.has(agentId));
    const defaultAgentIds = (workbenchData?.workspace?.default_agents || []).slice(0, 3);
    if (!selectedHomeAgentIds.length) {
      selectedHomeAgentIds = defaultAgentIds.length ? defaultAgentIds : platformAgents.slice(0, 2).map((agent) => agent.agent_id);
    }
    agentSelector.innerHTML = platformAgents.map((agent) => {
      const selected = selectedHomeAgentIds.includes(agent.agent_id);
      return `
        <button
          type="button"
          class="role-chip ${selected ? 'selected' : ''}"
          onclick="toggleHomeAgent('${escapeHtml(agent.agent_id)}', this)"
        >
          <span class="role-chip-emoji">${timelineIconForAgent(agent.agent_id)}</span>
          <span>${escapeHtml(agent.name)}</span>
        </button>
      `;
    }).join('');
  }
  if (agentSummary) {
    const selectedAgents = platformAgents.filter((agent) => selectedHomeAgentIds.includes(agent.agent_id));
    agentSummary.textContent = selectedAgents.length
      ? `当前群聊已选择 ${selectedAgents.length} 个 agent：${selectedAgents.slice(0, 3).map((agent) => agent.name).join(' / ')}${selectedAgents.length > 3 ? ' ...' : ''}`
      : '至少选择一个 agent';
  }
}

function toggleHomeAgent(agentId, chip) {
  if (selectedHomeAgentIds.includes(agentId)) {
    if (selectedHomeAgentIds.length === 1) return;
    selectedHomeAgentIds = selectedHomeAgentIds.filter((id) => id !== agentId);
  } else {
    selectedHomeAgentIds.push(agentId);
  }
  chip.classList.toggle('selected', selectedHomeAgentIds.includes(agentId));
  renderH2ASelectors();
}

function renderH2AThreadList() {
  const list = document.getElementById('homeThreadList');
  if (!list) return;
  if (!h2aThreads.length) {
    list.innerHTML = '<div class="empty-state">还没有 H2A 线程</div>';
    return;
  }
  list.innerHTML = h2aThreads.map((thread) => {
    const lastMessage = thread.messages?.[thread.messages.length - 1];
    const agentLabels = (thread.agent_labels || []).filter(Boolean);
    if (!agentLabels.length && thread.agent_label) agentLabels.push(thread.agent_label);
    const title = thread.title || `${thread.human_label} ↔ ${agentLabels.slice(0, 2).join(' + ') || thread.agent_label}`;
    return `
      <article class="h2a-thread-item ${thread.thread_id === selectedH2AThreadId ? 'active' : ''}" onclick="selectH2AThread('${escapeHtml(thread.thread_id)}')">
        <strong>${escapeHtml(title)}</strong>
        <p>${escapeHtml(lastMessage?.content || '线程已创建，等待第一条消息')}</p>
        <div class="h2a-thread-meta">
          <span class="artifact-pill">${escapeHtml(thread.human_label)}</span>
          <span class="artifact-pill">${escapeHtml(thread.mode || 'single')}</span>
          <span class="artifact-pill">${(thread.agent_ids || []).length} agents</span>
          ${(agentLabels.slice(0, 3)).map((label) => `<span class="artifact-pill">${escapeHtml(label)}</span>`).join('')}
          <span class="artifact-pill">${thread.messages?.length || 0} messages</span>
        </div>
      </article>
    `;
  }).join('');
}

function renderH2AConversation() {
  const container = document.getElementById('homeConversation');
  if (!container) return;
  const thread = h2aThreads.find((item) => item.thread_id === selectedH2AThreadId);
  if (!thread) {
    container.innerHTML = '<div class="empty-state">先创建或选择一个线程</div>';
    return;
  }
  if (!thread.messages?.length) {
    container.innerHTML = '<div class="empty-state">线程已创建，发送第一条消息开始 H2A 对话</div>';
    return;
  }
  const agentLabels = (thread.agent_labels || []).filter(Boolean);
  if (!agentLabels.length && thread.agent_label) agentLabels.push(thread.agent_label);
  const summaryBlock = `
    <article class="h2a-conversation-meta">
      <strong>${escapeHtml(thread.title || `${thread.human_label} ↔ ${agentLabels.join(' / ')}`)}</strong>
      <p>Human 以 ${escapeHtml(thread.human_label)} 身份接入，当前线程模式为 ${escapeHtml(thread.mode || 'single')}，会话由 ${agentLabels.length || 1} 个 agent 并行响应。</p>
      <div class="timeline-meta">
        <span class="artifact-pill">${escapeHtml(thread.human_label)}</span>
        <span class="artifact-pill">${escapeHtml(thread.mode || 'single')}</span>
        ${agentLabels.map((label) => `<span class="artifact-pill">${escapeHtml(label)}</span>`).join('')}
      </div>
    </article>
  `;
  container.innerHTML = summaryBlock + thread.messages.map((message) => `
    <article class="h2a-message ${escapeHtml(message.sender_type)}">
      <div class="h2a-message-head">
        <strong>${escapeHtml(message.sender_label)}</strong>
        <span>${escapeHtml(formatDateTime(message.created_at))}</span>
      </div>
      <div class="h2a-message-body">${escapeHtml(message.content)}</div>
    </article>
  `).join('');
  container.scrollTop = container.scrollHeight;
}

function selectH2AThread(threadId) {
  selectedH2AThreadId = threadId;
  const thread = h2aThreads.find((item) => item.thread_id === threadId);
  if (thread?.agent_ids?.length) {
    selectedHomeAgentIds = [...thread.agent_ids];
  }
  renderH2AThreadList();
  renderH2ASelectors();
  const humanSelect = document.getElementById('homeHumanSelect');
  if (thread && humanSelect && !currentUser) {
    humanSelect.value = thread.human_id;
  }
  renderH2AConversation();
}

async function createH2AThread() {
  const projectId = document.getElementById('homeH2AProjectSelect')?.value || selectedWorkbenchProjectId;
  const humanSelect = document.getElementById('homeHumanSelect');
  const message = document.getElementById('homeH2AMessage')?.value.trim() || '';
  const humanId = currentUser?.user_id || humanSelect?.value || '';
  const humanLabel = currentUser?.display_name || currentUser?.username || humanSelect?.options[humanSelect.selectedIndex]?.textContent?.split(' · ')[0] || humanId;
  const agentIds = selectedHomeAgentIds.filter(Boolean);
  if (!projectId || !humanId || !agentIds.length) {
    showH2AStatus('请先选择项目、human 身份和至少一个 agent', 'error');
    return;
  }
  try {
    const payload = await fetch(apiUrl(`/api/v2/projects/${projectId}/h2a/threads`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        human_id: humanId,
        human_label: humanLabel,
        agent_ids: agentIds,
        message,
      }),
    }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      return data;
    });
    const thread = payload.thread || payload;
    selectedH2AThreadId = thread.thread_id;
    document.getElementById('homeH2AMessage').value = '';
    showH2AStatus(`H2A 线程已创建，已接入 ${thread.agent_ids?.length || 1} 个 agent`, 'ok');
    await loadWorkbench(projectId);
  } catch (error) {
    console.warn('Create H2A thread failed:', error);
    showH2AStatus(`创建线程失败：${error.message}`, 'error');
  }
}

async function sendH2AMessage() {
  const messageInput = document.getElementById('homeH2AMessage');
  const message = messageInput?.value.trim() || '';
  if (!message) {
    showH2AStatus('请输入消息内容', 'error');
    return;
  }
  if (!selectedH2AThreadId) {
    await createH2AThread();
    return;
  }
  try {
    const payload = await fetch(apiUrl(`/api/v2/h2a/threads/${selectedH2AThreadId}/messages`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      return data;
    });
    messageInput.value = '';
    const thread = payload.thread;
    h2aThreads = [thread, ...h2aThreads.filter((item) => item.thread_id !== thread.thread_id)];
    selectedH2AThreadId = thread.thread_id;
    renderH2AThreadList();
    renderH2AConversation();
    showH2AStatus(`Agent 团队已回复，本轮 ${payload.agent_messages?.length || 1} 条`, 'ok');
    await loadWorkbench(thread.project_id);
  } catch (error) {
    console.warn('Send H2A message failed:', error);
    showH2AStatus(`发送失败：${error.message}`, 'error');
  }
}

async function refreshH2AThread() {
  if (!selectedH2AThreadId) {
    await loadH2AThreads();
    return;
  }
  try {
    const thread = await fetch(apiUrl(`/api/v2/h2a/threads/${selectedH2AThreadId}`)).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      return data;
    });
    h2aThreads = [thread, ...h2aThreads.filter((item) => item.thread_id !== thread.thread_id)];
    renderH2AThreadList();
    renderH2AConversation();
    showH2AStatus('线程已刷新', 'ok');
  } catch (error) {
    console.warn('Refresh H2A thread failed:', error);
    showH2AStatus(`刷新线程失败：${error.message}`, 'error');
  }
}

function showH2AStatus(message, mode = '') {
  const el = document.getElementById('homeH2AStatus');
  if (!el) return;
  el.textContent = message;
  el.className = `workbench-message ${mode}`.trim();
  el.style.display = message ? 'block' : 'none';
}

function showWorkbenchMessage(message, mode = '') {
  const el = document.getElementById('workbenchMessage');
  if (!el) return;
  el.textContent = message;
  el.className = `workbench-message ${mode}`.trim();
  el.style.display = message ? 'block' : 'none';
}

function timelineIcon(type) {
  const icons = {
    memory: '🧠',
    decision: '🧭',
    discussion: '💬',
    workflow_run: '🛰️',
    workflow_step: '⚙️',
    approval: '✅',
    second_me: '🔗',
    h2a_thread: '🤝',
    h2a_message: '💭',
  };
  return icons[type] || '•';
}

function timelineIconForAgent(agentId) {
  if (agentId === 'agent.orchestrator') return '🛰️';
  if (agentId === 'agent.reviewer') return '✅';
  if (agentId === 'agent.integration') return '🔗';
  return '🤖';
}

function formatStatus(status) {
  if (!status) return 'unknown';
  return status.replace(/_/g, ' ');
}

function statusClass(status) {
  return (status || 'unknown').replace(/[^a-z0-9_-]/gi, '_');
}

function formatStageLabel(stage) {
  const map = {
    target_id: '靶点确认',
    screening: '虚拟筛选',
    hit_to_lead: 'Hit-to-Lead',
    lead_opt: '先导优化',
    candidate: '候选化合物',
    preclinical: '临床前',
    clinical: '临床',
  };
  return map[stage] || stage || '未设置';
}

function formatDateTime(value) {
  if (!value) return 'N/A';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function toSlug(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '') || 'item';
}

// ─── 工具函数 ───
function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
