"""Moteur de règles déterministe.

Quatre familles :
  marqueurs       : posent une étiquette de provenance (ex. "secret")
  regles/quand    : un seul événement suffit à déclencher
  regles/sequence : une étiquette posée plus tôt + un événement sortant
  regles/seuil    : N fois le même genre d'appel dans une fenêtre de temps

Aucun LLM ici : un verdict doit être reproductible et explicable.
"""

from __future__ import annotations

import fnmatch
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

SEVERITES = ("info", "moyenne", "haute", "critique")
MODES = ("observe", "demande", "bloque")


# ------------------------------------------------------------------ chargement


def charger(chemin: Path | str) -> "Jeu":
    texte = Path(chemin).read_text(encoding="utf-8")
    return charger_texte(texte)


def charger_texte(texte: str) -> "Jeu":
    try:
        import yaml
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise SystemExit(
            "PyYAML manque. Installe-le : pip install pyyaml"
        ) from exc
    data = yaml.safe_load(texte) or {}
    return Jeu(
        marqueurs=data.get("marqueurs", []) or [],
        regles=data.get("regles", []) or [],
        redaction=data.get("redaction", {}) or {},
        budgets=data.get("budgets", []) or [],
        tarifs=data.get("tarifs", {}) or {},
        controle=data.get("controle", {}) or {},
    )


@dataclass
class Jeu:
    marqueurs: list[dict] = field(default_factory=list)
    regles: list[dict] = field(default_factory=list)
    redaction: dict = field(default_factory=dict)
    budgets: list = field(default_factory=list)
    tarifs: dict = field(default_factory=dict)

    def budgets_tarifs(self):
        from .budgets import charger as charger_budgets
        return charger_budgets({"budgets": self.budgets, "tarifs": self.tarifs})
    controle: dict = field(default_factory=dict)

    def redacteur(self):
        from .redaction import Redacteur, Reglage
        return Redacteur(Reglage.depuis_yaml(self.redaction))

    def valider(self) -> list[str]:
        erreurs = []
        vus = set()
        for r in self.regles:
            rid = r.get("id")
            if not rid:
                erreurs.append("une règle n'a pas d'id")
                continue
            if rid in vus:
                erreurs.append(f"id en double : {rid}")
            vus.add(rid)
            if r.get("severite", "moyenne") not in SEVERITES:
                erreurs.append(f"{rid} : sévérité inconnue « {r['severite']} »")
            if r.get("mode", "observe") not in MODES:
                erreurs.append(f"{rid} : mode inconnu « {r['mode']} », "
                               f"attendu {' ou '.join(MODES)}")
            if not any(k in r for k in ("quand", "sequence", "seuil")):
                erreurs.append(f"{rid} : ni quand, ni sequence, ni seuil")
        from .budgets import valider as valider_budgets
        b, _t = self.budgets_tarifs()
        erreurs += valider_budgets(b)
        for m in self.marqueurs:
            if "marque" not in m or "quand" not in m:
                erreurs.append("un marqueur doit avoir « marque » et « quand »")
        return erreurs


# -------------------------------------------------------------- comparaisons


def _valeur_arg(args: dict, nom: str) -> str | None:
    if not isinstance(args, dict):
        return None
    if nom in args:
        v = args[nom]
        return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    bas = {k.lower(): v for k, v in args.items()}
    v = bas.get(nom.lower())
    if v is None:
        return None
    return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)


def _outil_correspond(outil: str | None, motif) -> bool:
    if motif is None:
        return True
    if outil is None:
        return False
    motifs = motif if isinstance(motif, list) else [motif]
    return any(fnmatch.fnmatch(outil, m) for m in motifs)


def _condition_correspond(cond: dict, outil: str | None, args: dict) -> bool:
    """cond = {outil: ..., arg: nom, dans/non_dans/correspond/contient: ...}"""
    if not _outil_correspond(outil, cond.get("outil")):
        return False

    nom_arg = cond.get("arg")
    if nom_arg is None:
        # aucun test sur les arguments : l'outil suffisait
        return not any(k in cond for k in ("dans", "non_dans", "correspond", "contient"))

    valeur = _valeur_arg(args, nom_arg)
    if valeur is None:
        return False

    if "correspond" in cond:
        if not re.search(cond["correspond"], valeur):
            return False
    if "contient" in cond:
        if cond["contient"] not in valeur:
            return False
    if "dans" in cond:
        if not any(fnmatch.fnmatch(valeur, g) for g in cond["dans"]):
            return False
    if "non_dans" in cond:
        if any(fnmatch.fnmatch(valeur, g) for g in cond["non_dans"]):
            return False
    return True


# ------------------------------------------------------------------ moteur


@dataclass
class Violation:
    regle: str
    severite: str
    explication: str
    origine_seq: int | None = None
    mode: str = "observe"      # observe | demande | bloque


class EtatRun:
    """Mémoire de ce qui s'est passé jusqu'ici dans un run."""

    def __init__(self) -> None:
        self.marques: dict[str, int] = {}      # marque -> seq où elle a été posée
        self.historique: list[tuple[str, str, float]] = []  # (outil, ts, epoch)

    def poser(self, marque: str, seq: int) -> None:
        self.marques.setdefault(marque, seq)


class Moteur:
    def __init__(self, jeu: Jeu):
        self.jeu = jeu

    def evaluer(
        self, etat: EtatRun, seq: int, outil: str | None, args: dict, ts: str
    ) -> list[Violation]:
        args = args or {}
        trouvees: list[Violation] = []

        # 1. marqueurs de provenance
        for m in self.jeu.marqueurs:
            if _condition_correspond(m["quand"], outil, args):
                etat.poser(m["marque"], seq)

        # 2. historique pour les seuils
        try:
            epoch = datetime.fromisoformat(ts).timestamp()
        except ValueError:
            epoch = 0.0
        if outil:
            etat.historique.append((outil, ts, epoch))

        for r in self.jeu.regles:
            sev = r.get("severite", "moyenne")

            mode = r.get("mode", "observe")

            if "quand" in r and _condition_correspond(r["quand"], outil, args):
                trouvees.append(
                    Violation(r["id"], sev, self._texte(r, outil, args), mode=mode))

            elif "sequence" in r:
                etapes = r["sequence"]
                if len(etapes) >= 2:
                    depart, arrivee = etapes[0], etapes[-1]
                    marque = depart.get("marque")
                    pose = etat.marques.get(marque) if marque else None
                    if pose is not None and _condition_correspond(arrivee, outil, args):
                        trouvees.append(
                            Violation(
                                r["id"],
                                sev,
                                r.get("description")
                                or f"« {marque} » lu à l'événement {pose}, "
                                   f"puis {outil} ici",
                                origine_seq=pose,
                                mode=mode,
                            )
                        )

            elif "seuil" in r:
                s = r["seuil"]
                fenetre = float(s.get("fenetre_s", 60))
                compte = 0
                for o, _t, e in reversed(etat.historique):
                    if epoch - e > fenetre:
                        break
                    if _outil_correspond(o, s.get("outil")):
                        compte += 1
                if compte == int(s.get("compte", 5)):  # une seule alerte par salve
                    trouvees.append(
                        Violation(
                            r["id"],
                            sev,
                            r.get("description")
                            or f"{compte} appels {s.get('outil')} en {fenetre:.0f} s",
                            mode=mode,
                        )
                    )

        return trouvees

    @staticmethod
    def _texte(r: dict, outil: str | None, args: dict) -> str:
        if r.get("description"):
            return r["description"]
        nom_arg = (r.get("quand") or {}).get("arg")
        val = _valeur_arg(args, nom_arg) if nom_arg else None
        return f"{outil} sur {val}" if val else f"{outil}"


# ------------------------------------------------------------------- rejeu


def rejouer(con, jeu: Jeu, ecrire: bool = False) -> dict:
    """Applique un jeu de règles à tout l'historique déjà enregistré.

    C'est la fonction qui répond à « cette règle aurait déclenché combien de
    fois ? » sans rien bloquer.
    """
    moteur = Moteur(jeu)
    par_regle: dict[str, int] = {}
    exemples: dict[str, list[dict]] = {}
    etats: dict[str, EtatRun] = {}
    total = 0

    for row in con.execute(
        "SELECT * FROM evenements WHERE type='appel' ORDER BY seq"
    ):
        etat = etats.setdefault(row["run_id"], EtatRun())
        args = json.loads(row["args_json"] or "{}")
        for v in moteur.evaluer(etat, row["seq"], row["outil"], args, row["ts"]):
            total += 1
            par_regle[v.regle] = par_regle.get(v.regle, 0) + 1
            exemples.setdefault(v.regle, [])
            if len(exemples[v.regle]) < 3:
                exemples[v.regle].append(
                    {"seq": row["seq"], "run_id": row["run_id"],
                     "outil": row["outil"], "explication": v.explication}
                )
            if ecrire:
                con.execute(
                    """INSERT OR IGNORE INTO violations
                       (run_id, evt_seq, origine_seq, regle, severite,
                        explication, mode)
                       VALUES (?,?,?,?,?,?,'observe')""",
                    (row["run_id"], row["seq"], v.origine_seq, v.regle,
                     v.severite, v.explication),
                )

    return {"total": total, "par_regle": par_regle, "exemples": exemples}
