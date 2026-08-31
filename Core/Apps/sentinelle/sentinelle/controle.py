"""Le verdict : ce qui interrompt réellement un agent.

Trois niveaux, du plus doux au plus dur :

    observe   on note, l'appel passe
    demande   l'appel est retenu jusqu'à ce qu'un humain tranche
    bloque    l'appel n'atteint jamais l'outil

Plus un frein d'urgence global qui coupe tout, indépendant des règles.

Deux principes qui gouvernent ce fichier :

1. **Le refus doit être lisible par le modèle, pas seulement par toi.** Un
   agent qui reçoit une erreur de protocole se contente souvent de réessayer en
   boucle. Un agent qui reçoit un résultat d'outil disant « refusé par la
   sentinelle, règle X, demande à ton humain » change de plan. Le refus part
   donc en `isError` dans un résultat normal, pas en erreur JSON-RPC.

2. **En cas de doute, on refuse.** Si le moteur de règles lève une exception,
   si l'humain ne répond pas à temps, si le journal est inaccessible : l'appel
   ne passe pas. C'est le seul défaut défendable pour un dispositif de
   contrôle, et c'est réglable pour ceux qui préfèrent l'inverse.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone


def maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


# ───────────────────────────────────────────────────────── frein d'urgence


def arret_actif(con: sqlite3.Connection) -> tuple[bool, str]:
    row = con.execute("SELECT actif, motif FROM arret WHERE id=1").fetchone()
    if not row:
        return False, ""
    return bool(row["actif"]), row["motif"] or ""


def basculer_arret(con: sqlite3.Connection, actif: bool, motif: str = "") -> None:
    con.execute(
        "UPDATE arret SET actif=?, ts=?, motif=? WHERE id=1",
        (1 if actif else 0, maintenant(), motif),
    )


# ────────────────────────────────────────────────────── file d'autorisations


def creer_demande(
    con: sqlite3.Connection,
    run_id: str,
    evt_seq: int | None,
    outil: str,
    args: dict,
    resume: str,
    regle: str,
    severite: str,
    explication: str,
) -> int:
    cur = con.execute(
        """INSERT INTO demandes
           (run_id, evt_seq, outil, args_json, resume, regle, severite,
            explication, cree_ts)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (run_id, evt_seq, outil, json.dumps(args, ensure_ascii=False), resume,
         regle, severite, explication, maintenant()),
    )
    return int(cur.lastrowid)


def decider(
    con: sqlite3.Connection,
    demande_id: int,
    etat: str,
    decideur: str = "humain",
    motif: str = "",
) -> bool:
    cur = con.execute(
        """UPDATE demandes SET etat=?, decide_ts=?, decideur=?, motif=?
           WHERE id=? AND etat='attente'""",
        (etat, maintenant(), decideur, motif, demande_id),
    )
    return cur.rowcount > 0


def etat_demande(con: sqlite3.Connection, demande_id: int) -> str:
    row = con.execute("SELECT etat FROM demandes WHERE id=?", (demande_id,)).fetchone()
    return row["etat"] if row else "expire"


def attendre(
    con: sqlite3.Connection,
    demande_id: int,
    delai_s: float = 120.0,
    intervalle: float = 0.4,
) -> str:
    """Attend la décision d'un humain. Silence prolongé = refus.

    Un dispositif de contrôle dont l'inaction laisse passer ne contrôle rien.
    """
    limite = time.time() + delai_s
    while time.time() < limite:
        etat = etat_demande(con, demande_id)
        if etat != "attente":
            return etat
        time.sleep(intervalle)
    con.execute(
        "UPDATE demandes SET etat='expire', decide_ts=?, decideur='délai', "
        "motif=? WHERE id=? AND etat='attente'",
        (maintenant(), f"aucune réponse en {delai_s:.0f} s", demande_id),
    )
    return "expire"


def en_attente(con: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in con.execute(
        "SELECT * FROM demandes WHERE etat='attente' ORDER BY id")]


# ───────────────────────────────────────────────────────────── la réponse


def message_refus(regle: str, explication: str, mode: str) -> dict:
    """Ce que l'agent reçoit à la place du résultat.

    Rédigé pour être lu par un modèle : il dit ce qui a été refusé, pourquoi,
    et quelle est la suite raisonnable ; sinon l'agent réessaie en boucle.
    """
    if mode == "arret":
        texte = (
            "Appel refusé : le frein d'urgence de la sentinelle est tiré. "
            "Aucun outil n'est disponible tant qu'un humain ne l'a pas relâché. "
            "Arrête-toi et signale-le à ton humain plutôt que de réessayer."
        )
    elif mode == "expire":
        texte = (
            f"Appel refusé faute d'autorisation : la règle « {regle} » exige "
            f"l'accord d'un humain, et personne n'a répondu dans le délai. "
            f"Ne réessaie pas ; demande explicitement l'autorisation."
        )
    elif mode == "refuse":
        texte = (
            f"Appel refusé par un humain. Règle « {regle} » : {explication}. "
            f"N'essaie pas de contourner ce refus par un autre outil. "
            f"Explique ce que tu voulais faire et attends des instructions."
        )
    else:
        texte = (
            f"Appel bloqué par la sentinelle. Règle « {regle} » : {explication}. "
            f"Cette limite est fixée par l'humain qui te supervise. "
            f"Ne cherche pas d'autre chemin vers le même effet ; "
            f"signale le blocage et propose une alternative."
        )
    return {"content": [{"type": "text", "text": texte}], "isError": True}
