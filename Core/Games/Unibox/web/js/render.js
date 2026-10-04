/* Unibox — rendu isométrique.

   Une seule projection : x et y de la grille deviennent les deux diagonales
   de l'écran, et tout ce qui a de la hauteur (murs, caisses, cariste) est
   dessiné du fond vers l'avant. Rien n'est chargé depuis un fichier : les
   volumes sont peints face par face, donc nets à n'importe quelle échelle. */

const PALETTE = {
  hazeA:     '#241d33',
  hazeB:     '#14101c',

  floor:     '#473d63',
  floorAlt:  '#4f456d',
  grout:     '#251f39',

  wallTop:   '#2a2340',
  wallLeft:  '#201a30',
  wallRight: '#181324',
  wallEdge:  '#463b64',

  oakTop:    '#d5934f',
  oakLeft:   '#b0713a',
  oakRight:  '#8b5628',
  oakEdge:   '#f2b678',

  setTop:    '#5fc9ae',
  setLeft:   '#3fa189',
  setRight:  '#2d7b68',
  setEdge:   '#9df0dc',

  brass:     '#e0b163',
  vest:      '#f6ead6',
  vestLow:   '#cdbda4',
  band:      '#f0a852',
  goal:      '#4fb8a0',
  player:    '#f0a852',
  playerLow: '#b0721f',
  visor:     '#241a2e',
  cast:      'rgba(11,7,18,.30)',
  contact:   'rgba(10,7,16,.34)',
};

/* Bruit stable par case : deux dalles voisines ne sont jamais identiques. */
function jitter(x, y) {
  const n = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453;
  return n - Math.floor(n);
}

function rgb(hex) {
  let h = hex.slice(1);
  if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

function mix(a, b, t) {
  const pa = rgb(a), pb = rgb(b);
  const c = pa.map((v, i) => Math.round(v + (pb[i] - v) * t));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

const TILE_W = 68;    // largeur d'une dalle avant mise à l'échelle
const TILE_H = 34;    // sa hauteur apparente : rapport 2:1, l'angle classique
const WALL_H = 16;   // assez bas pour ne pas masquer la case de derrière

class Renderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.dpr = 1;
    this.geom = null;
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.canvas.width = Math.max(1, Math.round(rect.width * this.dpr));
    this.canvas.height = Math.max(1, Math.round(rect.height * this.dpr));
    this.cw = rect.width;
    this.ch = rect.height;
  }

  /* Échelle et centrage : le quai entier doit tenir dans la fenêtre. */
  layout(game) {
    const W = game.width, H = game.height;
    const padX = 56, padY = this.cw < 700 ? 96 : 76;
    const availW = Math.max(120, this.cw - padX * 2);
    const availH = Math.max(120, this.ch - padY * 2);

    const spanX = (W + H) * TILE_W / 2;
    const spanY = (W + H) * TILE_H / 2 + WALL_H + 26;
    const s = Math.max(0.3, Math.min(1.7, Math.min(availW / spanX, availH / spanY)));

    const tw = TILE_W * s, th = TILE_H * s, wallH = WALL_H * s;
    const minSX = -(H - 1) * tw / 2 - tw / 2;
    const maxSX = (W - 1) * tw / 2 + tw / 2;
    const minSY = -th / 2 - wallH - 20 * s;
    const maxSY = (W + H - 2) * th / 2 + th / 2;

    this.geom = {
      tw, th, wallH, s,
      ox: (this.cw - (maxSX - minSX)) / 2 - minSX,
      oy: (this.ch - (maxSY - minSY)) / 2 - minSY,
    };
  }

  project(x, y) {
    const g = this.geom;
    return { cx: g.ox + (x - y) * g.tw / 2, cy: g.oy + (x + y) * g.th / 2 };
  }

  /* Projection inverse, pour savoir sur quelle dalle le joueur a cliqué. */
  cellAt(px, py) {
    const g = this.geom;
    if (!g) return null;
    const a = (px - g.ox) / (g.tw / 2);
    const b = (py - g.oy) / (g.th / 2);
    return { x: Math.round((a + b) / 2), y: Math.round((b - a) / 2) };
  }

  /* ------------------------------------------------------------------ */

  draw(game, view, time) {
    const ctx = this.ctx;
    ctx.save();
    ctx.scale(this.dpr, this.dpr);
    ctx.clearRect(0, 0, this.cw, this.ch);
    this.backdrop(ctx);

    // 1. le sol, puis les marques au sol
    for (let y = 0; y < game.height; y++) {
      for (let x = 0; x < game.width; x++) {
        if (!game.floor.has(x + ',' + y)) continue;
        const { cx, cy } = this.project(x, y);
        this.floorTile(ctx, cx, cy, x, y);
      }
    }
    for (const gk of game.goals) {
      const [x, y] = gk.split(',').map(Number);
      const { cx, cy } = this.project(x, y);
      this.goalMark(ctx, cx, cy, time, game.boxIndex(x, y) >= 0);
    }

    // 2. les ombres portées, toutes à plat sur le sol
    for (let y = 0; y < game.height; y++)
      for (let x = 0; x < game.width; x++)
        if (game.walls.has(x + ',' + y) && this.touchesFloor(game, x, y))
          this.castShadow(ctx, x, y, 1);
    for (const b of view.boxes) this.castShadow(ctx, b.x, b.y, 0.76);
    this.castShadow(ctx, view.player.x, view.player.y, 0.4);

    // 3. les volumes, du fond vers l'avant
    const items = [];
    for (let y = 0; y < game.height; y++)
      for (let x = 0; x < game.width; x++)
        if (game.walls.has(x + ',' + y) && this.touchesFloor(game, x, y))
          items.push({ depth: x + y, x, y, kind: 'wall' });

    for (const gk of game.goals) {
      const [x, y] = gk.split(',').map(Number);
      if (game.boxIndex(x, y) < 0) items.push({ depth: x + y + 0.15, x, y, kind: 'beam' });
    }
    view.boxes.forEach(b => items.push({ depth: b.x + b.y + 0.4, x: b.x, y: b.y, kind: 'box', data: b }));
    items.push({ depth: view.player.x + view.player.y + 0.5, x: view.player.x, y: view.player.y, kind: 'hero' });
    items.sort((a, b) => a.depth - b.depth);

    for (const it of items) {
      const { cx, cy } = this.project(it.x, it.y);
      if (it.kind === 'wall') this.wall(ctx, cx, cy, it.x, it.y);
      else if (it.kind === 'beam') this.goalBeam(ctx, cx, cy, time, it.x, it.y);
      else if (it.kind === 'box') this.crate(ctx, cx, cy, it.data.set, time);
      else this.hero(ctx, cx, cy, view.player.facing, time);
    }

    this.particles(ctx, view);
    this.vignette(ctx);
    ctx.restore();
  }

  touchesFloor(game, x, y) {
    for (let dy = -1; dy <= 1; dy++)
      for (let dx = -1; dx <= 1; dx++)
        if (game.floor.has((x + dx) + ',' + (y + dy))) return true;
    return false;
  }

  backdrop(ctx) {
    const g = ctx.createRadialGradient(this.cw / 2, this.ch * 0.4, 40,
                                       this.cw / 2, this.ch * 0.5, Math.max(this.cw, this.ch) * 0.8);
    g.addColorStop(0, PALETTE.hazeA);
    g.addColorStop(1, PALETTE.hazeB);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, this.cw, this.ch);
  }

  vignette(ctx) {
    const g = ctx.createRadialGradient(this.cw / 2, this.ch / 2, Math.min(this.cw, this.ch) * 0.35,
                                       this.cw / 2, this.ch / 2, Math.max(this.cw, this.ch) * 0.75);
    g.addColorStop(0, 'rgba(0,0,0,0)');
    g.addColorStop(1, 'rgba(0,0,0,.42)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, this.cw, this.ch);
  }

  /* ------------------------------ formes ---------------------------- */

  diamond(ctx, cx, cy, tw, th) {
    ctx.beginPath();
    ctx.moveTo(cx, cy - th / 2);
    ctx.lineTo(cx + tw / 2, cy);
    ctx.lineTo(cx, cy + th / 2);
    ctx.lineTo(cx - tw / 2, cy);
    ctx.closePath();
  }

  floorTile(ctx, cx, cy, x, y) {
    const { tw, th } = this.geom;
    const shade = jitter(x, y) * 0.08;
    ctx.fillStyle = mix((x + y) % 2 ? PALETTE.floorAlt : PALETTE.floor, '#000', shade);
    this.diamond(ctx, cx, cy, tw, th);
    ctx.fill();
    ctx.strokeStyle = PALETTE.grout;
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.strokeStyle = 'rgba(255,255,255,.045)';
    this.diamond(ctx, cx, cy, tw * 0.7, th * 0.7);
    ctx.stroke();
  }

  /* La lumière vient d'en haut à gauche : l'ombre tombe vers le bas à droite. */
  castShadow(ctx, x, y, strength) {
    const { tw, th } = this.geom;
    const { cx, cy } = this.project(x, y);
    ctx.save();
    ctx.globalAlpha = strength;
    ctx.fillStyle = PALETTE.cast;
    this.diamond(ctx, cx + tw * 0.11, cy + th * 0.11, tw * 0.94, th * 0.94);
    ctx.fill();
    ctx.restore();
  }

  /* Emplacement : un liseré au ras du sol, avec les quatre équerres de
     marquage qu'on peint sur un vrai quai. Il bat doucement tant qu'il
     est vide, et s'éteint dès qu'une caisse le couvre. */
  goalMark(ctx, cx, cy, time, filled) {
    const { tw, th } = this.geom;
    const pulse = 0.5 + 0.5 * Math.sin(time / 620);
    const w = tw * 0.72, d = th * 0.72;

    ctx.save();
    ctx.globalAlpha = filled ? 0.18 : 0.22 + pulse * 0.26;
    ctx.fillStyle = PALETTE.goal;
    this.diamond(ctx, cx, cy, w, d);
    ctx.fill();

    ctx.globalAlpha = filled ? 0.35 : 0.95;
    ctx.strokeStyle = PALETTE.goal;
    ctx.lineWidth = Math.max(1.4, tw * 0.03);

    // équerres aux quatre sommets du losange
    const V = [[cx, cy - d / 2], [cx + w / 2, cy], [cx, cy + d / 2], [cx - w / 2, cy]];
    for (let i = 0; i < 4; i++) {
      const a = V[i], b = V[(i + 1) % 4], p = V[(i + 3) % 4];
      ctx.beginPath();
      ctx.moveTo(a[0] + (p[0] - a[0]) * 0.34, a[1] + (p[1] - a[1]) * 0.34);
      ctx.lineTo(a[0], a[1]);
      ctx.lineTo(a[0] + (b[0] - a[0]) * 0.34, a[1] + (b[1] - a[1]) * 0.34);
      ctx.stroke();
    }
    ctx.restore();
  }

  /* Colonne de lumière au-dessus d'un emplacement libre : on la voit même
     quand un mur cache le bas du marquage au sol. */
  goalBeam(ctx, cx, cy, time, x, y) {
    const { tw, th } = this.geom;
    const pulse = 0.72 + 0.28 * Math.sin(time / 620 + (x + y) * 0.7);
    const h = th * 2.1, wBase = tw * 0.44, wTop = tw * 0.2;

    const g = ctx.createLinearGradient(cx, cy, cx, cy - h);
    g.addColorStop(0, 'rgba(79,184,160,.30)');
    g.addColorStop(0.55, 'rgba(79,184,160,.10)');
    g.addColorStop(1, 'rgba(79,184,160,0)');

    ctx.save();
    ctx.globalAlpha = pulse;
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.moveTo(cx - wBase / 2, cy);
    ctx.lineTo(cx - wTop / 2, cy - h);
    ctx.lineTo(cx + wTop / 2, cy - h);
    ctx.lineTo(cx + wBase / 2, cy);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  cube(ctx, cx, cy, tw, th, h, colors, edge) {
    ctx.fillStyle = colors.left;
    ctx.beginPath();
    ctx.moveTo(cx - tw / 2, cy - h);
    ctx.lineTo(cx, cy - h + th / 2);
    ctx.lineTo(cx, cy + th / 2);
    ctx.lineTo(cx - tw / 2, cy);
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = colors.right;
    ctx.beginPath();
    ctx.moveTo(cx + tw / 2, cy - h);
    ctx.lineTo(cx, cy - h + th / 2);
    ctx.lineTo(cx, cy + th / 2);
    ctx.lineTo(cx + tw / 2, cy);
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = colors.top;
    this.diamond(ctx, cx, cy - h, tw, th);
    ctx.fill();

    if (edge) {
      ctx.strokeStyle = edge;
      ctx.lineWidth = Math.max(1, tw * 0.018);
      this.diamond(ctx, cx, cy - h, tw, th);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(cx - tw / 2, cy - h); ctx.lineTo(cx - tw / 2, cy);
      ctx.moveTo(cx + tw / 2, cy - h); ctx.lineTo(cx + tw / 2, cy);
      ctx.moveTo(cx, cy - h + th / 2); ctx.lineTo(cx, cy + th / 2);
      ctx.stroke();
    }
  }

  wall(ctx, cx, cy, x, y) {
    const { tw, th, wallH } = this.geom;
    const v = jitter(x * 3, y * 7) * 0.07;
    this.cube(ctx, cx, cy, tw, th, wallH, {
      top: mix(PALETTE.wallTop, '#000', v),
      left: mix(PALETTE.wallLeft, '#000', v),
      right: mix(PALETTE.wallRight, '#000', v),
    }, 'rgba(93,79,131,.75)');

    // joint de béton à mi-hauteur
    ctx.strokeStyle = 'rgba(255,255,255,.07)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(cx - tw / 2, cy - wallH * 0.5);
    ctx.lineTo(cx, cy - wallH * 0.5 + th / 2);
    ctx.lineTo(cx + tw / 2, cy - wallH * 0.5);
    ctx.stroke();

    // arête éclairée par la lampe du quai
    ctx.strokeStyle = 'rgba(255,236,200,.13)';
    ctx.lineWidth = Math.max(1, tw * 0.02);
    ctx.beginPath();
    ctx.moveTo(cx - tw / 2, cy - wallH);
    ctx.lineTo(cx, cy - wallH - th / 2);
    ctx.stroke();
  }

  crate(ctx, cx, cy, isSet, time) {
    const { tw, th } = this.geom;
    const w = tw * 0.74, d = th * 0.74, h = th * 0.86;

    ctx.save();
    ctx.fillStyle = PALETTE.contact;
    this.diamond(ctx, cx, cy + th * 0.05, w * 1.04, d * 1.04);
    ctx.fill();

    if (isSet) {
      ctx.shadowColor = 'rgba(95,201,174,.6)';
      ctx.shadowBlur = tw * 0.3;
    }
    this.cube(ctx, cx, cy, w, d, h, {
      top: isSet ? PALETTE.setTop : PALETTE.oakTop,
      left: isSet ? PALETTE.setLeft : PALETTE.oakLeft,
      right: isSet ? PALETTE.setRight : PALETTE.oakRight,
    }, isSet ? PALETTE.setEdge : PALETTE.oakEdge);
    ctx.shadowBlur = 0;

    // croisillons de renfort sur les deux faces visibles
    ctx.strokeStyle = isSet ? 'rgba(255,255,255,.3)' : 'rgba(120,72,20,.75)';
    ctx.lineWidth = Math.max(1.2, tw * 0.026);
    ctx.beginPath();
    ctx.moveTo(cx - w / 2, cy - h); ctx.lineTo(cx, cy + d / 2);
    ctx.moveTo(cx - w / 2, cy); ctx.lineTo(cx, cy - h + d / 2);
    ctx.moveTo(cx + w / 2, cy - h); ctx.lineTo(cx, cy + d / 2);
    ctx.moveTo(cx + w / 2, cy); ctx.lineTo(cx, cy - h + d / 2);
    ctx.stroke();

    // planches du couvercle
    ctx.strokeStyle = isSet ? 'rgba(255,255,255,.18)' : 'rgba(120,72,20,.45)';
    ctx.lineWidth = 1;
    // sommets du couvercle : ouest, sud, nord, est
    const Wp = [cx - w / 2, cy - h], Sp = [cx, cy - h + d / 2];
    const Np = [cx, cy - h - d / 2], Ep = [cx + w / 2, cy - h];
    for (const t of [1 / 3, 2 / 3]) {
      ctx.beginPath();
      ctx.moveTo(Wp[0] + (Sp[0] - Wp[0]) * t, Wp[1] + (Sp[1] - Wp[1]) * t);
      ctx.lineTo(Np[0] + (Ep[0] - Np[0]) * t, Np[1] + (Ep[1] - Np[1]) * t);
      ctx.stroke();
    }

    // ferrures laiton
    ctx.fillStyle = PALETTE.brass;
    const r = Math.max(1.4, tw * 0.028);
    for (const [px, py] of [[cx, cy - h - d / 2 + r * 1.4], [cx - w / 2 + r * 1.6, cy - h],
                            [cx + w / 2 - r * 1.6, cy - h]]) {
      ctx.beginPath();
      ctx.arc(px, py, r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }


  hero(ctx, cx, cy, facing, time) {
    const { tw, th } = this.geom;
    const bob = Math.sin(time / 340) * th * 0.04;
    const w = tw * 0.30;
    const legs = th * 0.30, torso = th * 0.62, head = w * 0.62;
    const hip = cy - legs + bob;
    const shoulder = hip - torso;
    const dir = { up: -1, right: -1, down: 1, left: 1 }[facing] ?? 1;
    const away = facing === 'up' || facing === 'right';

    ctx.save();
    ctx.fillStyle = PALETTE.contact;
    ctx.beginPath();
    ctx.ellipse(cx, cy + th * 0.05, w * 0.6, w * 0.3, 0, 0, Math.PI * 2);
    ctx.fill();

    // jambes
    ctx.fillStyle = '#403655';
    ctx.fillRect(cx - w * 0.42, hip, w * 0.34, legs);
    ctx.fillRect(cx + w * 0.08, hip, w * 0.34, legs);

    // buste
    const grad = ctx.createLinearGradient(cx, shoulder, cx, hip);
    grad.addColorStop(0, PALETTE.vest);
    grad.addColorStop(1, PALETTE.vestLow);
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.moveTo(cx - w * 0.52, hip);
    ctx.lineTo(cx - w * 0.46, shoulder + torso * 0.12);
    ctx.quadraticCurveTo(cx, shoulder - torso * 0.06, cx + w * 0.46, shoulder + torso * 0.12);
    ctx.lineTo(cx + w * 0.52, hip);
    ctx.closePath();
    ctx.fill();

    // bande réfléchissante
    ctx.fillStyle = PALETTE.band;
    ctx.fillRect(cx - w * 0.5, hip - torso * 0.42, w, torso * 0.17);

    // tête
    ctx.fillStyle = mix(PALETTE.vest, '#ffffff', 0.35);
    ctx.beginPath();
    ctx.ellipse(cx, shoulder - head * 0.42, head * 0.5, head * 0.55, 0, 0, Math.PI * 2);
    ctx.fill();

    // casque
    ctx.fillStyle = PALETTE.band;
    ctx.beginPath();
    ctx.ellipse(cx, shoulder - head * 0.72, head * 0.58, head * 0.34, 0, 0, Math.PI * 2);
    ctx.fill();

    if (!away) {
      ctx.fillStyle = PALETTE.visor;
      ctx.beginPath();
      ctx.ellipse(cx + dir * head * 0.1, shoulder - head * 0.3, head * 0.26, head * 0.16, 0, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  particles(ctx, view) {
    if (!view.particles.length) return;
    ctx.save();
    for (const p of view.particles) {
      const { cx, cy } = this.project(p.x, p.y);
      ctx.globalAlpha = Math.max(0, p.life);
      ctx.fillStyle = p.color;
      const s = p.size * (0.4 + p.life * 0.6);
      ctx.beginPath();
      ctx.moveTo(cx + p.ox, cy + p.oy - s);
      ctx.lineTo(cx + p.ox + s, cy + p.oy);
      ctx.lineTo(cx + p.ox, cy + p.oy + s);
      ctx.lineTo(cx + p.ox - s, cy + p.oy);
      ctx.closePath();
      ctx.fill();
    }
    ctx.restore();
  }
}
