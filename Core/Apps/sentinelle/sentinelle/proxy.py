"""Proxy MCP en stdio : se place entre l'agent et son serveur d'outils.

    agent  --stdio-->  sentinelle proxy  --stdio-->  serveur MCP réel

Règle d'or : stdout ne contient QUE du JSON-RPC. Tout message de diagnostic
part sur stderr ou dans ~/.sentinelle/proxy.log, sinon le canal est corrompu
et l'agent décroche.

Le proxy relaie, enregistre, et selon les règles : laisse passer, retient le
temps qu'un humain tranche, ou refuse. Un appel refusé n'atteint jamais le
serveur réel.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import controle
from .journal import Journal
from . import budgets as bud
from .regles import EtatRun, Jeu, Moteur, charger


def _diag(msg: str) -> None:
    chemin = Path.home() / ".sentinelle" / "proxy.log"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")


class _ViolationBudget:
    """Un dépassement se juge comme une violation de règle : même modes,
    même chemin de décision, même écriture au journal."""

    def __init__(self, d):
        self.regle = d.budget
        self.severite = d.severite
        self.explication = d.explication
        self.mode = d.mode
        self.origine_seq = None


def _resume_appel(outil: str, args: dict) -> str:
    for cle in ("path", "chemin", "file_path", "url", "query", "command", "pattern"):
        if isinstance(args, dict) and cle in args:
            v = args[cle]
            if isinstance(v, str):
                return f"{outil} {v[:120]}"
    return outil


def _texte_resultat(res: dict) -> str:
    contenu = res.get("content")
    if isinstance(contenu, list):
        morceaux = [c.get("text", "") for c in contenu if isinstance(c, dict)]
        return "\n".join(m for m in morceaux if m)
    return json.dumps(res, ensure_ascii=False)[:4000]


def _chemin_dans(args: dict | None) -> str | None:
    if not isinstance(args, dict):
        return None
    for cle in ("path", "chemin", "file_path"):
        if isinstance(args.get(cle), str):
            return args[cle]
    return None


class Proxy:
    def __init__(self, commande: list[str], regles: Path | None = None,
                 db: Path | None = None, observer_seulement: bool = False):
        self.commande = commande
        self.journal = Journal(db)
        self.run_id = self.journal.ouvrir_run(
            agent=os.environ.get("SENTINELLE_AGENT", "inconnu"),
            serveur=" ".join(commande),
            cwd=os.getcwd(),
        )
        jeu = charger(regles) if regles else Jeu()
        self.journal.redacteur = jeu.redacteur()
        self.moteur = Moteur(jeu)
        self.budgets, self.tarifs = jeu.budgets_tarifs()
        self.budgets_prevenus: set[str] = set()
        self.etat = EtatRun()

        conf = getattr(jeu, "controle", {}) or {}
        self.delai_demande = float(conf.get("delai_demande_s", 120))
        self.bloquer_si_erreur = conf.get("si_erreur", "bloquer") == "bloquer"
        self.observer_seulement = observer_seulement

        self.attente: dict[str, tuple[float, str, dict]] = {}
        self.verrou = threading.Lock()          # journal (SQLite)
        self.verrou_sortie = threading.Lock()   # stdout, écrit par 2 threads
        self.verrou_entree = threading.Lock()   # stdin du serveur réel
        self.enfant: subprocess.Popen | None = None
        self.en_suspens: list[threading.Thread] = []

    # ------------------------------------------------------------- écriture

    def _vers_stdout(self, ligne: str) -> None:
        with self.verrou_sortie:
            sys.stdout.write(ligne if ligne.endswith("\n") else ligne + "\n")
            sys.stdout.flush()

    def _vers_stdin_serveur(self, ligne: str) -> None:
        with self.verrou_entree:
            try:
                self.enfant.stdin.write(ligne)
                self.enfant.stdin.flush()
            except (BrokenPipeError, ValueError, AttributeError):
                pass

    def _repondre_refus(self, rpc_id, regle: str, explication: str,
                        genre: str) -> None:
        self._vers_stdout(json.dumps({
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": controle.message_refus(regle, explication, genre),
        }, ensure_ascii=False))

    # --------------------------------------------------------- enregistrement

    def _journaliser_appel(self, outil: str, args: dict, rpc_id: str):
        """Écrit l'appel et rend (seq, violations)."""
        with self.verrou:
            seq = self.journal.ecrire(
                self.run_id, "appel", outil=outil, args=args,
                resume=_resume_appel(outil, args), rpc_id=rpc_id,
            )
            self.attente[rpc_id] = (time.time(), outil, args)
            ts = self.journal.con.execute(
                "SELECT ts FROM evenements WHERE seq=?", (seq,)
            ).fetchone()["ts"]
            violations = self.moteur.evaluer(self.etat, seq, outil, args, ts)
            for v in violations:
                self.journal.violation(
                    self.run_id, seq, v.regle, v.severite, v.explication,
                    origine_seq=v.origine_seq,
                    mode="observe" if self.observer_seulement else v.mode,
                )
        return seq, violations

    def _prevenir_approche(self, outil: str | None) -> None:
        """Signale une fois qu'un plafond approche. Une fois : un compteur qui
        crie à chaque appel finit par ne plus être lu."""
        for b in self.budgets:
            if b.id in self.budgets_prevenus or not b.concerne(outil):
                continue
            e = bud.etat(self.journal.con, b, self.tarifs, self.run_id)
            if e["proche"]:
                self.budgets_prevenus.add(b.id)
                _diag(f"[budget] {b.id} à {e['fraction']:.0%} du plafond")
                self.journal.ecrire(
                    self.run_id, "meta", outil="budget",
                    resume=f"{b.id} : {e['fraction']:.0%} du plafond atteint",
                )

    def _journaliser_verdict(self, genre: str, outil: str, regle: str,
                             explication: str, rpc_id: str) -> None:
        with self.verrou:
            self.journal.ecrire(
                self.run_id, "refus", outil=outil, rpc_id=rpc_id,
                resume=f"{genre} · {regle} · {explication}"[:200],
            )
            self.attente.pop(rpc_id, None)

    # ------------------------------------------------------------- décision

    def _decider(self, msg: dict) -> tuple[str, dict]:
        """Rend (« passe » | « bloque » | « demande », contexte)."""
        params = msg.get("params") or {}
        outil = params.get("name", "?")
        args = params.get("arguments") or {}
        # JSON-RPC exige que l'identifiant de la réponse soit rigoureusement
        # celui de la requête, type compris : renvoyer "1" à qui a demandé 1
        # laisse un client strict attendre pour toujours. On garde donc la
        # valeur d'origine pour répondre, et sa forme texte pour nos index.
        rpc_brut = msg.get("id")
        rpc_id = str(rpc_brut)

        with self.verrou:
            coupe, motif = controle.arret_actif(self.journal.con)
        if coupe:
            return "bloque", {"outil": outil, "rpc_id": rpc_id, "rpc_brut": rpc_brut, "genre": "arret",
                              "regle": "frein d'urgence",
                              "explication": motif or "coupure manuelle"}

        try:
            seq, violations = self._journaliser_appel(outil, args, rpc_id)
        except Exception as exc:
            # Le dispositif de contrôle est aveugle : on ne laisse pas passer.
            _diag(f"évaluation impossible : {exc}")
            if self.bloquer_si_erreur:
                return "bloque", {"outil": outil, "rpc_id": rpc_id,
                                  "rpc_brut": rpc_brut,
                                  "genre": "bloque", "regle": "erreur interne",
                                  "explication": "la sentinelle n'a pas pu "
                                                 "évaluer cet appel"}
            return "passe", {}

        for v in violations:
            _diag(f"[{v.severite}] {v.regle} : {v.explication}")

        # Les budgets se jugent sur le journal, pas sur la règle : ils
        # dépendent de ce qui s'est déjà passé, pas de l'appel en cours seul.
        try:
            with self.verrou:
                depassements = bud.verdict(self.journal.con, self.budgets,
                                           self.tarifs, self.run_id, outil)
                for d in depassements:
                    self.journal.violation(
                        self.run_id, seq, d.budget, d.severite, d.explication,
                        mode="observe" if self.observer_seulement else d.mode,
                    )
                self._prevenir_approche(outil)
        except Exception as exc:
            _diag(f"budgets non évaluables : {exc}")
            depassements = []

        for d in depassements:
            _diag(f"[budget] {d.budget} : {d.explication}")
            violations.append(_ViolationBudget(d))

        if self.observer_seulement:
            return "passe", {}

        dur = [v for v in violations if v.mode == "bloque"]
        if dur:
            v = dur[0]
            return "bloque", {"outil": outil, "rpc_id": rpc_id, "rpc_brut": rpc_brut, "genre": "bloque",
                              "regle": v.regle, "explication": v.explication}

        a_demander = [v for v in violations if v.mode == "demande"]
        if a_demander:
            v = a_demander[0]
            with self.verrou:
                demande_id = controle.creer_demande(
                    self.journal.con, self.run_id, seq, outil, args,
                    _resume_appel(outil, args), v.regle, v.severite,
                    v.explication,
                )
            _diag(f"demande {demande_id} en attente : {v.regle}")
            return "demande", {"outil": outil, "rpc_id": rpc_id,
                               "rpc_brut": rpc_brut, "demande_id": demande_id, "regle": v.regle,
                               "explication": v.explication}

        return "passe", {}

    def _trancher(self, ligne: str, ctx: dict) -> None:
        """Attend la décision humaine sans bloquer le reste du relais."""
        etat = controle.attendre(self.journal.con, ctx["demande_id"],
                                 delai_s=self.delai_demande)
        if etat == "accorde":
            with self.verrou:
                self.journal.ecrire(
                    self.run_id, "meta", outil=ctx["outil"], rpc_id=ctx["rpc_id"],
                    resume=f"autorisé par un humain · {ctx['regle']}",
                )
            self._vers_stdin_serveur(ligne)
            return
        genre = "refuse" if etat == "refuse" else "expire"
        self._journaliser_verdict(genre, ctx["outil"], ctx["regle"],
                                  ctx["explication"], ctx["rpc_id"])
        self._repondre_refus(ctx["rpc_brut"], ctx["regle"], ctx["explication"], genre)

    # --------------------------------------------------------- enregistrement

    def _note_resultat(self, msg: dict) -> None:
        rpc_id = str(msg.get("id"))
        with self.verrou:
            depart, outil, args = self.attente.pop(rpc_id, (None, None, None))
        if depart is None:
            return

        duree = int((time.time() - depart) * 1000)
        if "error" in msg:
            texte, type_evt = json.dumps(msg["error"], ensure_ascii=False), "erreur"
        else:
            texte, type_evt = _texte_resultat(msg.get("result") or {}), "resultat"
        with self.verrou:
            self.journal.ecrire(
                self.run_id, type_evt, outil=outil, contenu=texte,
                resume=f"{len(texte)} car. en {duree} ms",
                duree_ms=duree, rpc_id=rpc_id, chemin_source=_chemin_dans(args),
            )

    def _note_meta(self, msg: dict) -> None:
        methode = msg.get("method", "")
        with self.verrou:
            self.journal.ecrire(self.run_id, "meta", outil=methode,
                                resume=methode, rpc_id=str(msg.get("id")))

    # ------------------------------------------------------------- boucles

    def _vers_serveur(self) -> None:
        for ligne in sys.stdin:
            try:
                msg = json.loads(ligne)
            except json.JSONDecodeError:
                self._vers_stdin_serveur(ligne)
                continue

            methode = msg.get("method")
            if methode != "tools/call":
                if methode in ("initialize", "tools/list", "resources/read"):
                    try:
                        self._note_meta(msg)
                    except Exception as exc:
                        _diag(f"enregistrement du message entrant impossible : {exc}")
                self._vers_stdin_serveur(ligne)
                continue

            decision, ctx = self._decider(msg)

            if decision == "bloque":
                self._journaliser_verdict(ctx["genre"], ctx["outil"], ctx["regle"],
                                          ctx["explication"], ctx["rpc_id"])
                self._repondre_refus(ctx["rpc_brut"], ctx["regle"],
                                     ctx["explication"], ctx["genre"])
                continue   # l'appel n'atteint jamais le serveur réel

            if decision == "demande":
                t = threading.Thread(target=self._trancher, args=(ligne, ctx),
                                     daemon=True)
                self.en_suspens.append(t)
                t.start()
                continue

            self._vers_stdin_serveur(ligne)

        # L'agent a fermé son entrée. Ne pas replier le relais tant qu'une
        # décision humaine est en attente : sinon le serveur réel s'arrête et
        # l'autorisation accordée trois secondes plus tard n'a plus rien à
        # exécuter.
        for t in self.en_suspens:
            t.join(timeout=self.delai_demande + 5)
        with self.verrou_entree:
            try:
                self.enfant.stdin.close()
            except Exception:
                pass

    def _vers_client(self) -> None:
        for ligne in self.enfant.stdout:
            try:
                msg = json.loads(ligne)
                if "id" in msg and ("result" in msg or "error" in msg):
                    self._note_resultat(msg)
            except Exception as exc:
                _diag(f"enregistrement du message sortant impossible : {exc}")
            self._vers_stdout(ligne)

    def lancer(self) -> int:
        mode = "observation seule" if self.observer_seulement else "contrôle actif"
        _diag(f"run {self.run_id}, {mode}, {' '.join(self.commande)}")
        self.enfant = subprocess.Popen(
            self.commande, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=None, text=True, bufsize=1,
        )
        t1 = threading.Thread(target=self._vers_serveur, daemon=True)
        t2 = threading.Thread(target=self._vers_client, daemon=True)
        t1.start()
        t2.start()
        code = self.enfant.wait()
        t2.join(timeout=2)
        self.journal.fermer_run(self.run_id)
        self.journal.fermer()
        _diag(f"run {self.run_id} terminé, code {code}")
        return code
