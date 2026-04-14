const DEMO_REEL_SCENES = [
  {
    title: '项目不是死在没有想法，往往死在没人一起判断的深夜。',
    body: 'DrugMind 从最真实的一刻开始接管推进：失败、讨论、工具、结论，然后让项目继续向前走。',
    label: '深夜结果',
    duration: 5200,
  },
  {
    title: '问题一旦被抛进来，五个专业角色会在同一秒上线。',
    body: '药化、生物、药理、数据和项目管理不再分散，他们围绕同一个问题同步进入判断。',
    label: '角色召回',
    duration: 4600,
  },
  {
    title: '讨论不是热闹，而是为了逼近一个能执行的决定。',
    body: '每一句回答都要落到结构方向、风险取舍和下一轮实验的真实动作上。',
    label: '多角度讨论',
    duration: 4800,
  },
  {
    title: '工具和意见被合并成一个决策面，项目终于不再四分五裂。',
    body: 'ADMET、场景模板和化合物策略直接进入同一个推进链，而不是散落在几个页面里。',
    label: '工具合流',
    duration: 4800,
  },
  {
    title: '最后留下来的，不是答案，而是项目继续往前走。',
    body: 'DrugMind 把判断沉淀为下一轮实验、周会口径和 sprint 任务，让团队始终有人在线。',
    label: '推进落地',
    duration: 4800,
  },
];

const subtitleTime = document.getElementById('subtitleTime');
const subtitleTitle = document.getElementById('subtitleTitle');
const subtitleBody = document.getElementById('subtitleBody');
const timelineFill = document.getElementById('timelineFill');
const chapterTrack = document.getElementById('chapterTrack');
const filmFrame = document.getElementById('filmFrame');
const statusChips = Array.from(document.querySelectorAll('#filmStatusRail .status-chip'));
const togglePlaybackBtn = document.getElementById('togglePlaybackBtn');
const restartPlaybackBtn = document.getElementById('restartPlaybackBtn');
const scenes = Array.from(document.querySelectorAll('.film-scene'));
const params = new URLSearchParams(window.location.search);
const isRecordingMode = params.get('record') === '1';
const autoplay = params.get('autoplay') !== '0';

let totalDurationMs = DEMO_REEL_SCENES.reduce((sum, scene) => sum + scene.duration, 0);
let playbackProgressMs = 0;
let activeSceneIndex = 0;
let animationFrameId = null;
let playbackStartedAt = 0;
let isPlaying = false;

window.DRUGMIND_DEMO = {
  totalDurationMs,
};

function initDemoReel() {
  document.body.classList.toggle('is-recording', isRecordingMode);
  if (isRecordingMode) {
    document.getElementById('filmControls')?.remove();
  }
  renderChapterTrack();
  syncScene(0, true);
  bindControls();
  if (autoplay) {
    playDemo();
  }
}

function bindControls() {
  togglePlaybackBtn?.addEventListener('click', () => {
    if (isPlaying) {
      pauseDemo();
      return;
    }
    playDemo();
  });

  restartPlaybackBtn?.addEventListener('click', () => {
    playbackProgressMs = 0;
    syncScene(0, true);
    playDemo();
  });
}

function renderChapterTrack() {
  if (!chapterTrack) return;
  chapterTrack.innerHTML = DEMO_REEL_SCENES.map((scene, index) => `
    <button class="chapter-chip${index === 0 ? ' active' : ''}" type="button" data-index="${index}">
      <span>${String(index + 1).padStart(2, '0')}</span>
      <strong>${scene.label}</strong>
    </button>
  `).join('');

  chapterTrack.querySelectorAll('.chapter-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      const index = Number(chip.dataset.index || 0);
      jumpToScene(index);
    });
  });
}

function jumpToScene(index) {
  let offset = 0;
  for (let i = 0; i < index; i += 1) {
    offset += DEMO_REEL_SCENES[i].duration;
  }
  playbackProgressMs = offset;
  syncScene(index, true);
  if (isPlaying) {
    playbackStartedAt = Date.now() - playbackProgressMs;
  }
}

function syncScene(index, syncProgress = false) {
  const previousSceneIndex = activeSceneIndex;
  activeSceneIndex = index;
  if (syncProgress) {
    let offset = 0;
    for (let i = 0; i < index; i += 1) {
      offset += DEMO_REEL_SCENES[i].duration;
    }
    playbackProgressMs = offset;
  }

  scenes.forEach((scene) => {
    scene.classList.toggle('active', Number(scene.dataset.sceneIndex) === index);
  });

  document.querySelectorAll('.chapter-chip').forEach((chip, chipIndex) => {
    chip.classList.toggle('active', chipIndex === index);
  });
  statusChips.forEach((chip, chipIndex) => {
    chip.classList.toggle('active', chipIndex === index);
  });
  if (filmFrame) {
    filmFrame.dataset.activeScene = String(index);
  }

  const metadata = DEMO_REEL_SCENES[index];
  subtitleTitle.textContent = metadata.title;
  subtitleBody.textContent = metadata.body;
  updateProgress();
  if (previousSceneIndex !== index) {
    flashCut();
  }
}

function updateProgress() {
  const ratio = totalDurationMs ? Math.min(playbackProgressMs / totalDurationMs, 1) : 0;
  timelineFill.style.width = `${ratio * 100}%`;
  subtitleTime.textContent = `${formatTime(playbackProgressMs)} / ${formatTime(totalDurationMs)}`;
}

function formatTime(ms) {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
  const seconds = String(totalSeconds % 60).padStart(2, '0');
  return `${minutes}:${seconds}`;
}

function flashCut() {
  if (!filmFrame) return;
  filmFrame.classList.remove('is-cutting');
  window.requestAnimationFrame(() => {
    filmFrame.classList.add('is-cutting');
    window.setTimeout(() => filmFrame.classList.remove('is-cutting'), 260);
  });
}

function tickDemo() {
  if (!totalDurationMs) return;
  const elapsed = Date.now() - playbackStartedAt;
  playbackProgressMs = Math.min(elapsed, totalDurationMs);

  let accumulated = 0;
  let nextScene = DEMO_REEL_SCENES.length - 1;
  for (let i = 0; i < DEMO_REEL_SCENES.length; i += 1) {
    accumulated += DEMO_REEL_SCENES[i].duration;
    if (playbackProgressMs < accumulated) {
      nextScene = i;
      break;
    }
  }

  if (nextScene !== activeSceneIndex) {
    syncScene(nextScene);
  } else {
    updateProgress();
  }

  if (elapsed >= totalDurationMs) {
    if (isRecordingMode) {
      pauseDemo();
      playbackProgressMs = totalDurationMs;
      updateProgress();
      return;
    }
    playbackProgressMs = 0;
    syncScene(0, true);
    playbackStartedAt = Date.now();
  }
  if (isPlaying) {
    animationFrameId = window.requestAnimationFrame(tickDemo);
  }
}

function playDemo() {
  if (animationFrameId) {
    window.cancelAnimationFrame(animationFrameId);
  }
  isPlaying = true;
  playbackStartedAt = Date.now() - playbackProgressMs;
  if (togglePlaybackBtn) togglePlaybackBtn.textContent = '暂停';
  tickDemo();
}

function pauseDemo() {
  if (animationFrameId) {
    window.cancelAnimationFrame(animationFrameId);
  }
  animationFrameId = null;
  isPlaying = false;
  if (togglePlaybackBtn) togglePlaybackBtn.textContent = '继续';
}

initDemoReel();
