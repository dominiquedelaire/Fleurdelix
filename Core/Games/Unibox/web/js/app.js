/* Unibox — assemblage : entrées, animation, interface, sauvegarde. */

const $ = sel => document.querySelector(sel);
const canvas = $('#board');
const renderer = new Renderer(canvas);

const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const STEP_MS = reduceMotion ? 1 : 118;
const PUSH_MS = reduceMotion ? 1 : 148;

const state = {
  index: 0,
  game: null,
  view: { player: { x: 0, y: 0, facing: 'down' }, boxes: [], particles: [] },
  anim: null,
  queue: [],
  progress: { best: {}, reached: 0, sound: true },
  busy: false,
};

/* ----------------------------- sauvegarde ----------------------------- */

function waitForBridge() {
  if (window.pywebview && window.pywebview.api) return Promise.resolve(true);
  return new Promise(resolve => {
    let done = false;
    const finish = ok => { if (!done) { done = true; resolve(ok); } };
    window.addEventListener('pywebviewready', () => finish(true));
    setTimeout(() => finish(!!(window.pywebview && window.pywebview.api)), 900);
  });
}

async function loadProgress() {
  const bridged = await waitForBridge();
  try {
    if (bridged) {
      const raw = await window.pywebview.api.load_progress();
      if (raw) return { ...state.progress, ...JSON.parse(raw) };
    } else {
      const raw = localStorage.getItem('unibox');
      if (raw) return { ...state.progress, ...JSON.parse(raw) };
    }
  } catch (e) { /* première partie, ou stockage indisponible */ }
  return state.progress;
}

function saveProgress() {
  const raw = JSON.stringify(state.progress);
  try {
    if (window.pywebview && window.pywebview.api) window.pywebview.api.save_progress(raw);
    else localStorage.setItem('unibox', raw);
  } catch (e) { /* on continue sans sauvegarde */ }
}

/* -------------------------------- son -------------------------------- */

const audio = {
  ctx: null,
  on: true,
  wake() {
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC) this.ctx = new AC();
    }
    if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume();
  },
  tone(freq, dur, type = 'sine', gain = 0.05, slide = 0) {
    if (!this.on || !this.ctx) return;
    const t = this.ctx.currentTime;
    const o = this.ctx.createOscillator();
    const g = this.ctx.createGain();
    o.type = type;
    o.frequency.setValueAtTime(freq, t);
    if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(30, freq + slide), t + dur);
    g.gain.setValueAtTime(gain, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g).connect(this.ctx.destination);
    o.start(t);
    o.stop(t + dur + 0.02);
  },
  step()    { this.tone(190, 0.05, 'triangle', 0.022); },
  push()    { this.tone(96, 0.16, 'sawtooth', 0.045, -40); },
  seated()  { this.tone(660, 0.16, 'sine', 0.06, 330); },
  blocked() { this.tone(72, 0.07, 'square', 0.02); },
  fanfare() {
    [0, 120, 240, 400].forEach((ms, i) =>
      setTimeout(() => this.tone([523, 659, 784, 1047][i], 0.34, 'triangle', 0.05), ms));
  },
};

/* ------------------------------ niveaux ------------------------------ */

function loadLevel(i, { silent } = {}) {
  state.index = Math.max(0, Math.min(LEVELS.length - 1, i));
  state.game = new Game(LEVELS[state.index]);
  state.queue = [];
  state.anim = null;
  state.view.particles = [];
  state.view.player.facing = 'down';
  syncView();
  renderer.layout(state.game);
  refreshUI();
  $('#winVeil').hidden = true;
  if (state.progress.reached < state.index) {
    state.progress.reached = state.index;
    saveProgress();
  }
  if (!silent) state.progress.last = state.index, saveProgress();
}

function syncView() {
  const g = state.game;
  state.view.player.x = g.player.x;
  state.view.player.y = g.player.y;
  state.view.boxes = g.boxes.map(b => ({ x: b.x, y: b.y, set: g.isGoal(b.x, b.y) }));
}

/* ------------------------------ actions ------------------------------ */

function enqueue(dir) {
  if (state.queue.length > 2 || (state.game && state.game.solved)) return;
  state.queue.push(dir);
  pump();
}

function pump() {
  if (state.anim || !state.queue.length) return;
  const dir = state.queue.shift();
  const res = state.game.step(dir);
  state.view.player.facing = dir;

  if (!res) {
    audio.blocked();
    state.queue = [];
    return;
  }

  state.anim = {
    t0: performance.now(),
    dur: res.pushed ? PUSH_MS : STEP_MS,
    player: { from: res.from, to: res.to },
    box: res.pushed ? { index: res.pushed.index, from: res.pushed.from, to: res.pushed.to } : null,
    landed: res.pushed && res.pushed.nowOnGoal && !res.pushed.wasOnGoal,
    solved: res.solved,
  };

  if (res.pushed) audio.push(); else audio.step();
  refreshStats();
}

function finishAnim() {
  const a = state.anim;
  state.anim = null;
  syncView();

  if (a.landed) {
    audio.seated();
    burst(a.box.to.x, a.box.to.y);
  }
  refreshStats();

  if (a.solved) { state.queue = []; setTimeout(celebrate, 260); return; }
  pump();
}

function burst(x, y) {
  for (let i = 0; i < 16; i++) {
    const ang = (i / 16) * Math.PI * 2 + Math.random();
    const sp = 12 + Math.random() * 22;
    state.view.particles.push({
      x, y,
      ox: 0, oy: -6,
      vx: Math.cos(ang) * sp,
      vy: Math.sin(ang) * sp * 0.55 - 18,
      life: 1,
      size: 2 + Math.random() * 3,
      color: Math.random() < 0.35 ? '#e0b163' : '#5fc9ae',
    });
  }
}

function undo() {
  if (state.anim || state.game.solved) return;
  const r = state.game.undo();
  if (!r) return;
  syncView();
  audio.step();
  refreshStats();
}

function restart() {
  state.game.reset();
  state.queue = [];
  state.anim = null;
  state.view.particles = [];
  syncView();
  refreshStats();
  $('#winVeil').hidden = true;
}

function celebrate() {
  const lvl = LEVELS[state.index];
  const g = state.game;
  const prev = state.progress.best[lvl.id];
  const better = !prev || g.moves < prev.moves;
  if (better) state.progress.best[lvl.id] = { moves: g.moves, pushes: g.pushes };
  state.progress.reached = Math.max(state.progress.reached, state.index + 1);
  saveProgress();
  audio.fanfare();

  $('#winEyebrow').textContent = `Niveau ${state.index + 1} sur ${LEVELS.length}`;
  $('#winTitle').textContent = lvl.name;
  $('#winStats').textContent = `${g.moves} pas, ${g.pushes} poussées.` +
    (lvl.par ? ` Le minimum connu est de ${lvl.par} poussées.` : '');
  $('#winNote').textContent = better && prev ? 'Nouveau meilleur score.'
    : (g.pushes === lvl.par ? 'Poussées optimales.' : '');

  const last = state.index === LEVELS.length - 1;
  $('#btnContinue').textContent = last ? 'Revenir au premier quai' : 'Niveau suivant';
  $('#winVeil').hidden = false;
  $('#btnContinue').focus();
}

/* ----------------------------- interface ----------------------------- */

function refreshStats() {
  const g = state.game;
  $('#statMoves').textContent = g.moves;
  $('#statPushes').textContent = g.pushes;
  $('#statDone').textContent = `${g.placed} / ${g.total}`;
}

function refreshUI() {
  const lvl = LEVELS[state.index];
  $('#levelNum').textContent = state.index + 1;
  $('#levelName').textContent = lvl.name;
  $('#levelHint').textContent = lvl.hint || '';
  $('#progressLabel').textContent = `Niveau ${state.index + 1} sur ${LEVELS.length}`;
  const best = state.progress.best[lvl.id];
  $('#statBest').textContent = best ? `${best.moves} pas` : '—';
  $('#btnPrev').disabled = state.index === 0;
  $('#btnNext').disabled = state.index >= Math.min(LEVELS.length - 1, state.progress.reached);
  refreshStats();
}

function openPicker() {
  const grid = $('#levelGrid');
  grid.innerHTML = '';
  LEVELS.forEach((lvl, i) => {
    const b = document.createElement('button');
    b.className = 'tile';
    const best = state.progress.best[lvl.id];
    const locked = i > state.progress.reached;
    if (best) b.classList.add('done');
    if (i === state.index) b.classList.add('current');
    if (locked) b.classList.add('locked');
    b.innerHTML = `<b>${i + 1}</b><small>${best ? best.moves + ' pas' : (locked ? 'verrouillé' : 'à faire')}</small>`;
    b.title = lvl.name;
    b.disabled = locked;
    b.onclick = () => { $('#levelVeil').hidden = true; loadLevel(i); };
    grid.appendChild(b);
  });
  const done = LEVELS.filter(l => state.progress.best[l.id]).length;
  $('#pickerFoot').textContent = `${done} quai${done > 1 ? 's' : ''} dégagé${done > 1 ? 's' : ''} sur ${LEVELS.length}.`;
  $('#levelVeil').hidden = false;
  $('#btnCloseLevels').focus();
}

/* ------------------------------ entrées ------------------------------ */

const KEYS = {
  ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right',
  w: 'up', s: 'down', a: 'left', d: 'right',
  z: 'up', q: 'left',
};

window.addEventListener('keydown', e => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  audio.wake();
  const dir = KEYS[e.key] || KEYS[e.key.toLowerCase()];
  if (dir) { e.preventDefault(); enqueue(dir); return; }

  const k = e.key.toLowerCase();
  if (k === 'u') { e.preventDefault(); undo(); }
  else if (k === 'r') { e.preventDefault(); restart(); }
  else if (k === 'l') { e.preventDefault(); openPicker(); }
  else if (k === 'n' && !$('#btnNext').disabled) loadLevel(state.index + 1);
  else if (k === 'p') loadLevel(state.index - 1);
  else if (e.key === 'Escape') { $('#levelVeil').hidden = true; }
  else if (e.key === 'Enter' && !$('#winVeil').hidden) $('#btnContinue').click();
});

canvas.addEventListener('pointerdown', e => {
  audio.wake();
  if (state.game.solved) return;
  const r = canvas.getBoundingClientRect();
  const cell = renderer.cellAt(e.clientX - r.left, e.clientY - r.top);
  if (!cell) return;

  const p = state.game.player;
  const dx = cell.x - p.x, dy = cell.y - p.y;

  // clic sur une caisse voisine : on la pousse
  if (state.game.boxIndex(cell.x, cell.y) >= 0 && Math.abs(dx) + Math.abs(dy) === 1) {
    enqueue(dx === 1 ? 'right' : dx === -1 ? 'left' : dy === 1 ? 'down' : 'up');
    return;
  }
  const path = state.game.pathTo(cell.x, cell.y);
  if (path && path.length && path.length <= 40) {
    state.queue = path.slice();
    pump();
  }
});

document.querySelectorAll('.dpad button').forEach(b => {
  b.addEventListener('click', () => { audio.wake(); enqueue(b.dataset.dir); });
});

$('#btnUndo').onclick = () => { audio.wake(); undo(); };
$('#btnReset').onclick = () => { audio.wake(); restart(); };
$('#btnLevels').onclick = openPicker;
$('#btnCloseLevels').onclick = () => { $('#levelVeil').hidden = true; };
$('#btnPrev').onclick = () => loadLevel(state.index - 1);
$('#btnNext').onclick = () => loadLevel(state.index + 1);
$('#btnReplay').onclick = () => { $('#winVeil').hidden = true; restart(); };
$('#btnContinue').onclick = () => {
  loadLevel(state.index === LEVELS.length - 1 ? 0 : state.index + 1);
};
$('#btnSound').onclick = () => {
  audio.on = !audio.on;
  state.progress.sound = audio.on;
  saveProgress();
  $('#btnSound').textContent = audio.on ? 'Son activé' : 'Son coupé';
  $('#btnSound').setAttribute('aria-pressed', String(audio.on));
  if (audio.on) { audio.wake(); audio.seated(); }
};

window.addEventListener('resize', () => {
  renderer.resize();
  if (state.game) renderer.layout(state.game);
});

/* --------------------------- boucle de rendu -------------------------- */

const easeOut = t => 1 - Math.pow(1 - t, 3);

function frame(now) {
  const a = state.anim;
  if (a) {
    const t = Math.min(1, (now - a.t0) / a.dur);
    const e = easeOut(t);
    state.view.player.x = a.player.from.x + (a.player.to.x - a.player.from.x) * e;
    state.view.player.y = a.player.from.y + (a.player.to.y - a.player.from.y) * e;
    if (a.box) {
      const b = state.view.boxes[a.box.index];
      b.x = a.box.from.x + (a.box.to.x - a.box.from.x) * e;
      b.y = a.box.from.y + (a.box.to.y - a.box.from.y) * e;
    }
    if (t >= 1) finishAnim();
  }

  const ps = state.view.particles;
  for (let i = ps.length - 1; i >= 0; i--) {
    const p = ps[i];
    p.ox += p.vx * 0.016;
    p.oy += p.vy * 0.016;
    p.vy += 62 * 0.016;
    p.life -= 0.018;
    if (p.life <= 0) ps.splice(i, 1);
  }

  if (state.game) renderer.draw(state.game, state.view, now);
  requestAnimationFrame(frame);
}

/* ------------------------------ démarrage ----------------------------- */

(async function boot() {
  state.progress = await loadProgress();
  state.progress.best = state.progress.best || {};
  state.progress.reached = state.progress.reached || 0;

  audio.on = state.progress.sound !== false;
  $('#btnSound').textContent = audio.on ? 'Son activé' : 'Son coupé';
  $('#btnSound').setAttribute('aria-pressed', String(audio.on));

  renderer.resize();
  loadLevel(Math.min(state.progress.last || 0, state.progress.reached), { silent: true });
  requestAnimationFrame(frame);
})();
