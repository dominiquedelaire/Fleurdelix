/* Unibox — règles du jeu, indépendantes de l'affichage. */

const key = (x, y) => x + ',' + y;

const DIRS = {
  up:    { dx: 0, dy: -1 },
  down:  { dx: 0, dy: 1 },
  left:  { dx: -1, dy: 0 },
  right: { dx: 1, dy: 0 },
};

class Game {
  constructor(def) {
    this.def = def;
    this.reset();
  }

  reset() {
    const rows = this.def.map.split('\n').filter(r => r.length);
    const width = Math.max(...rows.map(r => r.length));

    this.width = width;
    this.height = rows.length;
    this.walls = new Set();
    this.goals = new Set();
    this.floor = new Set();
    this.boxes = [];
    this.player = { x: 0, y: 0 };

    rows.forEach((row, y) => {
      for (let x = 0; x < width; x++) {
        const c = row[x] || ' ';
        if (c === '#') { this.walls.add(key(x, y)); continue; }
        if (c === '-') continue;              // vide hors du quai
        this.floor.add(key(x, y));
        if ('.*+'.includes(c)) this.goals.add(key(x, y));
        if ('$*'.includes(c)) this.boxes.push({ x, y });
        if ('@+'.includes(c)) this.player = { x, y };
      }
    });

    this.history = [];
    this.moves = 0;
    this.pushes = 0;
    this.reindex();
  }

  reindex() {
    this.boxAt = new Map();
    this.boxes.forEach((b, i) => this.boxAt.set(key(b.x, b.y), i));
  }

  isWall(x, y) { return this.walls.has(key(x, y)) || !this.floor.has(key(x, y)); }
  isGoal(x, y) { return this.goals.has(key(x, y)); }
  boxIndex(x, y) { const i = this.boxAt.get(key(x, y)); return i === undefined ? -1 : i; }

  get placed() { return this.boxes.filter(b => this.isGoal(b.x, b.y)).length; }
  get total() { return this.boxes.length; }
  get solved() { return this.placed === this.total; }

  /* Tente un déplacement. Renvoie null si bloqué, sinon un compte rendu
     que l'affichage utilise pour animer et pour les effets sonores. */
  step(dir) {
    if (this.solved) return null;
    const d = DIRS[dir];
    if (!d) return null;

    const from = { ...this.player };
    const to = { x: from.x + d.dx, y: from.y + d.dy };
    if (this.isWall(to.x, to.y)) return null;

    const bi = this.boxIndex(to.x, to.y);
    let pushed = null;

    if (bi >= 0) {
      const dest = { x: to.x + d.dx, y: to.y + d.dy };
      if (this.isWall(dest.x, dest.y) || this.boxIndex(dest.x, dest.y) >= 0) return null;

      const box = this.boxes[bi];
      const wasOnGoal = this.isGoal(box.x, box.y);
      box.x = dest.x; box.y = dest.y;
      this.reindex();
      pushed = {
        index: bi,
        from: { ...to },
        to: dest,
        wasOnGoal,
        nowOnGoal: this.isGoal(dest.x, dest.y),
      };
      this.pushes++;
    }

    this.player = to;
    this.moves++;
    this.history.push({ dir, pushed: pushed ? pushed.index : -1, from });

    return { dir, from, to, pushed, solved: this.solved };
  }

  undo() {
    const last = this.history.pop();
    if (!last) return null;

    const d = DIRS[last.dir];
    const playerFrom = { ...this.player };
    this.player = { ...last.from };
    this.moves--;

    let pulled = null;
    if (last.pushed >= 0) {
      const box = this.boxes[last.pushed];
      const boxFrom = { x: box.x, y: box.y };
      box.x -= d.dx; box.y -= d.dy;
      this.reindex();
      this.pushes--;
      pulled = { index: last.pushed, from: boxFrom, to: { x: box.x, y: box.y } };
    }

    return { from: playerFrom, to: this.player, pulled };
  }

  /* Chemin le plus court vers une case libre, pour le déplacement à la souris.
     Renvoie une liste de directions, ou null. */
  pathTo(tx, ty) {
    if (this.isWall(tx, ty) || this.boxIndex(tx, ty) >= 0) return null;
    const start = key(this.player.x, this.player.y);
    const goal = key(tx, ty);
    if (start === goal) return [];

    const prev = new Map([[start, null]]);
    const queue = [this.player];
    while (queue.length) {
      const p = queue.shift();
      for (const [name, d] of Object.entries(DIRS)) {
        const n = { x: p.x + d.dx, y: p.y + d.dy };
        const k = key(n.x, n.y);
        if (prev.has(k) || this.isWall(n.x, n.y) || this.boxIndex(n.x, n.y) >= 0) continue;
        prev.set(k, { from: key(p.x, p.y), dir: name });
        if (k === goal) {
          const path = [];
          let cur = k;
          while (prev.get(cur)) { path.unshift(prev.get(cur).dir); cur = prev.get(cur).from; }
          return path;
        }
        queue.push(n);
      }
    }
    return null;
  }
}

if (typeof module !== 'undefined') module.exports = { Game, DIRS, key };
