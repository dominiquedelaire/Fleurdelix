/* Pont unique : pywebview s'il est là, sinon fetch vers le serveur local.
   Même code d'interface dans les deux modes. */

const pont = {
  pret: false,
  async appel(nom, ...args) {
    if (window.pywebview && window.pywebview.api) {
      return await window.pywebview.api[nom](...args);
    }
    const r = await fetch('/api/' + nom, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(args)
    });
    if (!r.ok) throw new Error('appel ' + nom + ' refusé');
    return await r.json();
  }
};

const $ = (s) => document.querySelector(s);
const el = (t, c, txt) => {
  const n = document.createElement(t);
  if (c) n.className = c;
  if (txt !== undefined) n.textContent = txt;
  return n;
};

let etatGlobal = null;
let runCourant = null;
let seqSelection = null;

const GLYPHES = { appel: '→', resultat: '←', erreur: '✗', meta: '·', refus: '⊘' };
const NOM_SEV = { 1: 'info', 2: 'moyenne', 3: 'haute', 4: 'critique' };

/* ───────────────────────────────────────────────── démarrage */

async function demarrer() {
  try {
    etatGlobal = await pont.appel('etat');
  } catch (e) {
    $('#entete').innerHTML = '<p class="vide">Le pont Python ne répond pas.</p>';
    return;
  }
  majSceau();
  majStatut();
  await chargerSessions();
}

function majSceau() {
  const n = $('#sceau-chaine');
  n.classList.toggle('ok', etatGlobal.chaine_ok);
  n.classList.toggle('bris', !etatGlobal.chaine_ok);
  n.querySelector('.txt').textContent = etatGlobal.chaine_ok
    ? `chaîne intacte · ${etatGlobal.nb_evts} maillons`
    : `chaîne rompue à l'évt ${etatGlobal.chaine_seq}`;
  n.title = etatGlobal.chaine_message;
}

function majStatut() {
  $('#st-db').textContent = etatGlobal.db;
  $('#st-evts').textContent = `${etatGlobal.nb_runs} sessions · ${etatGlobal.nb_evts} évts`;
  $('#st-alertes').textContent =
    (etatGlobal.nb_violations ? `${etatGlobal.nb_violations} alertes` : 'aucune alerte')
    + ` · ${etatGlobal.nb_secrets} secrets caviardés`
    + (etatGlobal.nb_effaces ? ` · ${etatGlobal.nb_effaces} contenus détruits` : '');
  $('#st-mode').textContent = (window.pywebview ? 'fenêtre' : 'navigateur');

  const b = $('#ouvrir-demandes');
  b.hidden = !etatGlobal.nb_demandes;
  $('#compte-demandes').textContent = etatGlobal.nb_demandes;

  const f = $('#frein');
  f.classList.toggle('tire', etatGlobal.arret_actif);
  f.textContent = etatGlobal.arret_actif ? 'Frein tiré : relâcher' : "Arrêt d'urgence";
}

/* ───────────────────────────────────────────────── sessions */

async function chargerSessions() {
  const runs = await pont.appel('runs');
  const nav = $('#sessions');
  nav.innerHTML = '';
  if (!runs.length) {
    nav.append(el('p', 'vide', 'Aucune session. Lance « sentinelle demo » pour voir à quoi ça ressemble.'));
    return;
  }
  runs.forEach((r) => {
    const b = el('button', 'session');
    b.type = 'button';
    if (r.viol) {
      const sev = NOM_SEV[r.pire] || 'haute';
      const badge = el('span', 'badge ' + sev, String(r.viol));
      b.append(badge);
    }
    b.append(el('span', 'agent', r.agent || 'agent inconnu'));
    b.append(el('span', 'meta', `${(r.debut || '').slice(0, 16).replace('T', ' ')} · ${r.nb_evts} évts`));
    b.addEventListener('click', () => ouvrirRun(r.id, b));
    nav.append(b);
  });
  nav.querySelector('button').click();
}

/* ───────────────────────────────────────────────── chronologie */

async function ouvrirRun(runId, bouton) {
  document.querySelectorAll('.session').forEach((s) => s.removeAttribute('aria-current'));
  if (bouton) bouton.setAttribute('aria-current', 'true');
  montrer('#chronologie');

  runCourant = await pont.appel('run', runId);
  if (runCourant.erreur) return;
  const { run, evenements, violations } = runCourant;

  const e = $('#entete');
  e.innerHTML = '';
  e.append(el('h2', null, run.agent || 'agent inconnu'));
  const d = el('p', 'details');
  d.innerHTML =
    `<span><b>serveur</b> ${echapper(run.serveur || '-')}</span>` +
    `<span><b>dossier</b> ${echapper(run.cwd || '-')}</span>` +
    `<span><b>début</b> ${(run.debut || '').slice(0, 19).replace('T', ' ')}</span>` +
    `<span><b>session</b> ${run.id}</span>`;
  e.append(d);

  const c = $('#chronologie');
  c.innerHTML = '';
  const seqBris = etatGlobal.chaine_ok ? null : etatGlobal.chaine_seq;

  evenements.forEach((ev) => {
    const b = el('button', 'evt type-' + ev.type);
    b.type = 'button';
    b.dataset.seq = ev.seq;
    if (seqBris !== null && ev.seq === seqBris) b.classList.add('rompu');

    const fil = el('div', 'fil');
    fil.append(el('span', 'sceau', ev.hash.slice(0, 6)));
    b.append(fil);

    const corps = el('div', 'corps');
    corps.append(el('span', 'heure', (ev.ts || '').slice(11, 19)));
    corps.append(el('span', 'glyphe', GLYPHES[ev.type] || '·'));
    corps.append(avecMarqueurs(el('span', 'resume'), ev.resume || ev.outil || ''));
    b.append(corps);

    b.addEventListener('click', () => selectionner(ev.seq, b));
    c.append(b);

    (violations[String(ev.seq)] || []).forEach((v) => {
      const a = el('div', 'alerte-ligne ' + (v.severite === 'critique' ? 'critique' : ''));
      a.append(el('span', 'regle', '⚑ ' + v.regle));
      a.append(el('span', 'quoi', ' : ' + v.explication));
      c.append(a);
    });
  });

  $('#tiroir').innerHTML = '<p class="vide">Clique un événement pour voir d\'où il vient.</p>';
}

/* ───────────────────────────────────────────────── tiroir */

async function selectionner(seq, bouton) {
  document.querySelectorAll('.evt').forEach((n) => n.removeAttribute('aria-current'));
  bouton.setAttribute('aria-current', 'true');
  seqSelection = seq;

  const g = await pont.appel('genealogie', seq);
  const ev = g.evenement;
  const t = $('#tiroir');
  t.innerHTML = '';
  t.append(el('h3', null, 'Événement ' + seq));

  champ(t, 'outil', ev.outil || '-');
  champ(t, 'heure', (ev.ts || '').replace('T', ' ').slice(0, 23));
  if (ev.duree_ms !== null && ev.duree_ms !== undefined) champ(t, 'durée', ev.duree_ms + ' ms');
  champ(t, 'sceau', ev.hash.slice(0, 24) + '…');
  champ(t, 'précédent', ev.hash_prec.slice(0, 24) + '…');

  const args = JSON.parse(ev.args_json || '{}');
  if (Object.keys(args).length) {
    t.append(el('h4', null, 'Arguments'));
    t.append(el('pre', 'bloc', JSON.stringify(args, null, 2)));
  }

  if (ev.blob_hash) {
    const c = await pont.appel('contenu', ev.blob_hash);
    if (c.efface) {
      t.append(el('h4', null, `Contenu (${c.taille} car.)`));
      t.append(el('p', 'efface', `Détruit : ${c.motif}. Le sceau reste, la chaîne tient.`));
    } else if (c.contenu) {
      t.append(el('h4', null, `Contenu (${c.taille} car.)`));
      t.append(avecMarqueurs(el('pre', 'bloc'), c.contenu.slice(0, 4000)));
    }
  }

  if (g.violations.length) {
    t.append(el('h4', null, 'Alertes'));
    g.violations.forEach((v) => {
      const a = el('div', 'alerte-ligne ' + (v.severite === 'critique' ? 'critique' : ''));
      a.append(el('span', 'regle', v.regle));
      a.append(el('span', 'quoi', ' : ' + v.explication));
      t.append(a);
    });
  }

  if (g.chaine.length) {
    t.append(el('h4', null, 'D\'où ça vient'));
    const box = el('div', 'genealogie');
    g.chaine.forEach((m) => {
      const n = el('div', 'maillon ' + (m.role === 'origine' ? 'origine' : ''));
      n.append(el('span', 'role', m.role === 'origine'
        ? 'origine · ' + m.regle : 'évt ' + m.seq));
      n.append(el('span', 'quoi', m.resume || m.outil || ''));
      box.append(n);
    });
    const ici = el('div', 'maillon ici');
    ici.append(el('span', 'role', 'ici'));
    ici.append(el('span', 'quoi', ev.resume || ev.outil || ''));
    box.append(ici);
    t.append(box);
  }
}

function champ(parent, cle, val) {
  const c = el('div', 'champ');
  c.append(el('span', 'cle', cle));
  c.append(el('span', 'val', String(val)));
  parent.append(c);
}

/* Les marqueurs ⟦genre·empreinte⟧ deviennent des pastilles. Le texte est
   échappé d'abord : on n'injecte jamais du HTML venu du journal. */
const MARQUEUR = /⟦([a-zé\-]+)·([0-9a-f]{6})⟧/g;

function avecMarqueurs(noeud, texte) {
  noeud.innerHTML = echapper(texte || '').replace(
    MARQUEUR,
    (m, genre, emp) => `<span class="caviarde" title="${genre} · empreinte ${emp}">${m}</span>`
  );
  return noeud;
}

function echapper(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

/* ───────────────────────────────────────────────── règles */

function montrer(panneau) {
  ['#chronologie', '#panneau-demandes', '#panneau-budgets', '#panneau-secrets', '#panneau-regles']
    .forEach((sel) => { $(sel).hidden = (sel !== panneau); });
}

/* ───────────────────────────────────────────────── demandes */

async function ouvrirDemandes() {
  montrer('#panneau-demandes');
  const e = $('#entete');
  e.innerHTML = '';
  e.append(el('h2', null, 'En attente de toi'));
  await peuplerDemandes();
}

async function peuplerDemandes() {
  const liste = await pont.appel('demandes');
  const z = $('#liste-demandes');
  z.innerHTML = '';
  if (!liste.length) {
    z.append(el('p', 'vide', 'Plus rien en attente. Les agents tournent.'));
    return;
  }
  liste.forEach((d) => {
    const c = el('div', 'demande');
    c.append(el('span', 'regle', '⚑ ' + d.regle));
    c.append(avecMarqueurs(el('span', 'quoi'), d.resume || d.outil));
    c.append(el('span', 'pourquoi', d.explication));
    let args = {};
    try { args = JSON.parse(d.args_json || '{}'); } catch (_) {}
    if (Object.keys(args).length) {
      c.append(avecMarqueurs(el('pre', 'bloc'), JSON.stringify(args, null, 2)));
    }
    const actions = el('div', 'actions');
    const oui = el('button', 'bouton accorder', 'Accorder');
    const non = el('button', 'bouton refuser', 'Refuser');
    oui.addEventListener('click', () => trancher(d.id, 'accorde'));
    non.addEventListener('click', () => trancher(d.id, 'refuse'));
    actions.append(oui, non);
    c.append(actions);
    z.append(c);
  });
}

async function trancher(id, etat) {
  await pont.appel('trancher', id, etat, '');
  etatGlobal = await pont.appel('etat');
  majStatut();
  await peuplerDemandes();
}

$('#ouvrir-demandes').addEventListener('click', ouvrirDemandes);

$('#frein').addEventListener('click', async () => {
  const veutTirer = !etatGlobal.arret_actif;
  await pont.appel('basculer_arret', veutTirer, '');
  etatGlobal = await pont.appel('etat');
  majStatut();
});

/* Un agent retenu attend une réponse : on va la chercher, on n'attend pas
   que l'utilisateur pense à rafraîchir. */
setInterval(async () => {
  if (!etatGlobal) return;
  try {
    const avant = etatGlobal.nb_demandes;
    etatGlobal = await pont.appel('etat');
    majStatut();
    if (etatGlobal.nb_demandes !== avant && !$('#panneau-demandes').hidden) {
      await peuplerDemandes();
    }
  } catch (_) { /* la fenêtre survit à un aller-retour raté */ }
}, 2000);

function octetsLisibles(n) {
  if (n >= 1e9) return (n / 1e9).toFixed(1) + ' Go';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + ' Mo';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + ' ko';
  return n + ' o';
}

$('#ouvrir-budgets').addEventListener('click', async () => {
  montrer('#panneau-budgets');
  const e = $('#entete');
  e.innerHTML = '';
  e.append(el('h2', null, 'Budgets'));

  const liste = await pont.appel('budgets');
  const z = $('#liste-budgets');
  z.innerHTML = '';
  if (!liste.length) {
    z.append(el('p', 'vide', 'Aucun budget défini dans le fichier de règles.'));
    return;
  }
  liste.forEach((b) => {
    const n = el('div', 'budget' + (b.depasse ? ' depasse' : b.proche ? ' proche' : ''));
    const titre = el('div', 'titre');
    titre.append(el('span', 'nom', b.id));
    if (b.outil) titre.append(el('span', 'cible', b.outil.join(', ')));
    titre.append(el('span', 'verdict', b.depasse ? 'dépassé' : b.proche ? 'proche' : b.mode));
    n.append(titre);

    const jauge = el('div', 'jauge');
    const barre = el('span');
    barre.style.width = Math.min(100, b.fraction * 100) + '%';
    jauge.append(barre);
    n.append(jauge);

    const mesures = [];
    if (b.max_appels) mesures.push(`${b.appels} / ${b.max_appels} appels`);
    if (b.max_cout) mesures.push(`${b.cout.toFixed(2)} / ${b.max_cout.toFixed(2)} $`);
    if (b.max_octets) mesures.push(`${octetsLisibles(b.octets)} / ${octetsLisibles(b.max_octets)}`);
    n.append(el('div', 'mesures', mesures.join('  ·  ')));

    let quand = b.portee;
    if (b.remise_a_zero) {
      const d = new Date(b.remise_a_zero);
      quand += ', remise à zéro ' + d.toLocaleString(undefined,
        { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
    }
    n.append(el('div', 'quand', quand));
    if (b.description) n.append(el('div', 'quand', b.description));
    z.append(n);
  });
});

$('#ouvrir-secrets').addEventListener('click', async () => {
  montrer('#panneau-secrets');
  const e = $('#entete');
  e.innerHTML = '';
  e.append(el('h2', null, 'Secrets'));

  const liste = await pont.appel('secrets');
  const z = $('#liste-secrets');
  z.innerHTML = '';
  if (!liste.length) {
    z.append(el('p', 'vide', 'Rien de sensible n\'a encore traversé le journal.'));
    return;
  }
  liste.forEach((s) => {
    const b = el('button', 'secret');
    b.type = 'button';
    b.append(el('span', 'genre', s.genre));
    b.append(el('span', 'emp', s.empreinte.slice(0, 6)));
    b.append(el('span', 'infos',
      `${s.longueur} car. · vu ${s.occurrences}× dans ${s.sessions} session(s)`));
    const detail = el('div', 'circulation');
    detail.hidden = true;
    b.addEventListener('click', async () => {
      if (!detail.dataset.charge) {
        const etapes = await pont.appel('circulation', s.empreinte);
        etapes.forEach((x) => {
          detail.append(avecMarqueurs(el('div', 'etape'),
            `évt ${x.seq} · ${x.agent} · ${x.resume || x.outil}`));
        });
        detail.dataset.charge = '1';
      }
      detail.hidden = !detail.hidden;
    });
    z.append(b);
    z.append(detail);
  });
});

$('#ouvrir-regles').addEventListener('click', async () => {
  montrer('#panneau-regles');
  const e = $('#entete');
  e.innerHTML = '';
  e.append(el('h2', null, 'Règles'));
  const r = await pont.appel('lire_regles');
  $('#yaml').value = r.texte;
  const d = el('p', 'details');
  d.innerHTML = `<span><b>fichier</b> ${echapper(r.chemin)}</span>`;
  e.append(d);
});

$('#rejouer').addEventListener('click', async () => {
  const res = await pont.appel('tester_regles', $('#yaml').value);
  afficherResultat(res, false);
});

$('#enregistrer').addEventListener('click', async () => {
  const res = await pont.appel('enregistrer_regles', $('#yaml').value);
  afficherResultat(res, true);
  etatGlobal = await pont.appel('etat');
  majStatut();
  await chargerSessions();
});

function afficherResultat(res, enregistre) {
  const z = $('#resultat-regles');
  z.innerHTML = '';
  if (res.erreur) {
    z.append(el('p', 'erreur', res.erreur));
    return;
  }
  if (enregistre) {
    z.append(el('p', null, `Règles enregistrées. ${res.total} alertes portées au journal.`));
    return;
  }
  if (!res.total) {
    z.append(el('p', 'vide', 'Aucune de ces règles ne se déclenche sur l\'historique.'));
    return;
  }
  z.append(el('p', null, `${res.total} déclenchements sur l'historique. Rien n'a été enregistré.`));
  Object.entries(res.par_regle)
    .sort((a, b) => b[1] - a[1])
    .forEach(([regle, n]) => {
      const l = el('div', 'ligne');
      l.append(el('span', 'n', n + '×'));
      l.append(el('span', null, regle));
      z.append(l);
      (res.exemples[regle] || []).forEach((ex) => {
        z.append(el('div', 'ex', `évt ${ex.seq} · ${ex.explication}`));
      });
    });
}

/* pywebview injecte son api après le chargement de la page */
if (window.pywebview && window.pywebview.api) demarrer();
else {
  window.addEventListener('pywebviewready', demarrer);
  setTimeout(() => { if (!etatGlobal) demarrer(); }, 350);
}
