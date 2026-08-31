"""Écriture du journal, chaîné par hash.

Chaque événement contient le hash du précédent. Modifier une ligne a posteriori
casse la chaîne à cet endroit et `sentinelle verify` le dit.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import db

GENESE = "0" * 64
SEUIL_BLOB = 400  # au-delà, le contenu part dans la table blobs


def maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _canonique(champs: dict) -> str:
    return json.dumps(champs, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def calcule_hash(hash_prec: str, champs: dict) -> str:
    return hashlib.sha256((hash_prec + _canonique(champs)).encode("utf-8")).hexdigest()


class Journal:
    def __init__(self, chemin: Path | str | None = None, redacteur=None):
        self.con = db.connexion(chemin)
        if redacteur is None:
            from .redaction import Redacteur
            redacteur = Redacteur()      # caviardage actif par défaut
        self.redacteur = redacteur

    # ---------------------------------------------------------------- runs

    def ouvrir_run(self, agent: str, serveur: str, cwd: str = "") -> str:
        run_id = uuid.uuid4().hex[:12]
        self.con.execute(
            "INSERT INTO runs (id, debut, agent, serveur, cwd) VALUES (?,?,?,?,?)",
            (run_id, maintenant(), agent, serveur, cwd),
        )
        return run_id

    def fermer_run(self, run_id: str) -> None:
        self.con.execute("UPDATE runs SET fin=? WHERE id=?", (maintenant(), run_id))

    # ---------------------------------------------------------- evenements

    def _dernier_hash(self) -> str:
        row = self.con.execute(
            "SELECT hash FROM evenements ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        return row["hash"] if row else GENESE

    def _stocke_blob(self, contenu: str) -> str:
        h = hashlib.sha256(contenu.encode("utf-8")).hexdigest()
        self.con.execute(
            "INSERT OR IGNORE INTO blobs (hash, taille, contenu) VALUES (?,?,?)",
            (h, len(contenu), contenu),
        )
        return h

    def ecrire(
        self,
        run_id: str,
        type_evt: str,
        *,
        outil: str | None = None,
        args: dict | None = None,
        contenu: str | None = None,
        resume: str = "",
        duree_ms: int | None = None,
        rpc_id: str | None = None,
        marques: list[str] | None = None,
        ts: str | None = None,
        chemin_source: str | None = None,
    ) -> int:
        """Ajoute un maillon à la chaîne. Renvoie le seq attribué.

        Le caviardage a lieu ICI, avant le calcul du hash : la version en clair
        n'est jamais écrite, et le sceau porte sur ce qui est réellement stocké.
        """
        trouvailles = []
        r = self.redacteur

        args, tr = r.rediger_args(args)
        trouvailles += tr
        resume, tr = r.rediger(resume)
        trouvailles += tr

        if contenu and r.chemin_sensible(chemin_source):
            contenu, tr = r.jeter_contenu(contenu, chemin_source or "")
        else:
            contenu, tr = r.rediger(contenu)
        trouvailles += tr

        args_json = json.dumps(args, ensure_ascii=False) if args is not None else None
        blob_hash = self._stocke_blob(contenu) if contenu else None
        ts = ts or maintenant()
        marques_json = json.dumps(sorted(marques or []))

        champs = {
            "run_id": run_id,
            "ts": ts,
            "type": type_evt,
            "outil": outil,
            "args_json": args_json,
            "resume": resume,
            "blob_hash": blob_hash,
            "duree_ms": duree_ms,
            "rpc_id": rpc_id,
            "marques": marques_json,
        }
        hash_prec = self._dernier_hash()
        h = calcule_hash(hash_prec, champs)

        cur = self.con.execute(
            """INSERT INTO evenements
               (run_id, ts, type, outil, args_json, resume, blob_hash,
                duree_ms, rpc_id, marques, hash_prec, hash)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                run_id, ts, type_evt, outil, args_json, resume, blob_hash,
                duree_ms, rpc_id, marques_json, hash_prec, h,
            ),
        )
        self.con.execute(
            "UPDATE runs SET nb_evts = nb_evts + 1 WHERE id=?", (run_id,)
        )
        seq = int(cur.lastrowid)
        if trouvailles:
            self._cataloguer(run_id, seq, ts, trouvailles)
        return seq

    def _cataloguer(self, run_id: str, seq: int, ts: str, trouvailles) -> None:
        for t in trouvailles:
            self.con.execute(
                """INSERT INTO secrets
                       (empreinte, genre, indice, longueur,
                        premier_ts, dernier_ts, occurrences)
                   VALUES (?,?,?,?,?,?,1)
                   ON CONFLICT(empreinte) DO UPDATE SET
                       dernier_ts  = excluded.dernier_ts,
                       occurrences = occurrences + 1""",
                (t.empreinte, t.genre, t.indice, t.longueur, ts, ts),
            )
            self.con.execute(
                "INSERT OR IGNORE INTO secrets_vus (empreinte, evt_seq, run_id) "
                "VALUES (?,?,?)",
                (t.empreinte, seq, run_id),
            )

    def marquer(self, seq: int, marques: list[str]) -> None:
        """Note : recalculer le hash serait tricher. Les marques posées après coup
        sont stockées dans violations/état, pas dans l'événement scellé."""
        raise NotImplementedError("un événement scellé ne se modifie pas")

    # --------------------------------------------------------- violations

    def violation(
        self,
        run_id: str,
        evt_seq: int,
        regle: str,
        severite: str,
        explication: str,
        origine_seq: int | None = None,
        mode: str = "observe",
    ) -> None:
        self.con.execute(
            """INSERT OR IGNORE INTO violations
               (run_id, evt_seq, origine_seq, regle, severite, explication, mode)
               VALUES (?,?,?,?,?,?,?)""",
            (run_id, evt_seq, origine_seq, regle, severite, explication, mode),
        )

    def fermer(self) -> None:
        self.con.close()


# ------------------------------------------------------------ vérification


def verifier(con: sqlite3.Connection) -> tuple[bool, int | None, str]:
    """Recalcule toute la chaîne. Renvoie (intacte, seq_du_bris, message)."""
    attendu = GENESE
    n = 0
    for row in con.execute("SELECT * FROM evenements ORDER BY seq"):
        n += 1
        if row["hash_prec"] != attendu:
            return False, row["seq"], (
                f"maillon rompu à l'événement {row['seq']} : "
                "un événement antérieur a été modifié ou supprimé"
            )
        champs = {
            "run_id": row["run_id"],
            "ts": row["ts"],
            "type": row["type"],
            "outil": row["outil"],
            "args_json": row["args_json"],
            "resume": row["resume"],
            "blob_hash": row["blob_hash"],
            "duree_ms": row["duree_ms"],
            "rpc_id": row["rpc_id"],
            "marques": row["marques"],
        }
        recalcule = calcule_hash(row["hash_prec"], champs)
        if recalcule != row["hash"]:
            return False, row["seq"], (
                f"contenu falsifié à l'événement {row['seq']} : "
                "le hash enregistré ne correspond pas aux données"
            )
        attendu = row["hash"]
    return True, None, f"chaîne intacte, {n} événements vérifiés"


def verifier_blobs(con: sqlite3.Connection) -> tuple[bool, int, int, list[str]]:
    """Le sceau d'un événement porte le hash de son contenu, pas le contenu.

    Conséquence utile : effacer un contenu ne casse pas la chaîne, mais le
    modifier se voit. C'est ce qui permet d'honorer une demande d'effacement
    sans perdre la preuve d'intégrité du journal.
    """
    intacts = effaces = 0
    alteres: list[str] = []
    for row in con.execute("SELECT hash, contenu, efface FROM blobs"):
        if row["efface"]:
            effaces += 1
            continue
        recalcule = hashlib.sha256((row["contenu"] or "").encode("utf-8")).hexdigest()
        if recalcule != row["hash"]:
            alteres.append(row["hash"])
        else:
            intacts += 1
    return (not alteres), intacts, effaces, alteres


def oublier(
    con: sqlite3.Connection,
    *,
    blob_hash: str | None = None,
    empreinte_secret: str | None = None,
    motif: str = "effacement demandé",
) -> int:
    """Détruit un contenu stocké en gardant sa trace et son hash.

    L'événement, son sceau et sa place dans la chaîne restent intacts : on
    prouve toujours que quelque chose est passé là, sans plus pouvoir le lire.
    """
    if empreinte_secret:
        cibles = [r["blob_hash"] for r in con.execute(
            """SELECT DISTINCT e.blob_hash FROM evenements e
               JOIN secrets_vus s ON s.evt_seq = e.seq
               WHERE s.empreinte = ? AND e.blob_hash IS NOT NULL""",
            (empreinte_secret,))]
    elif blob_hash:
        cibles = [blob_hash]
    else:
        cibles = [r["hash"] for r in con.execute(
            "SELECT hash FROM blobs WHERE efface = 0")]

    n = 0
    for h in cibles:
        cur = con.execute(
            "UPDATE blobs SET contenu = NULL, efface = 1, motif = ? "
            "WHERE hash = ? AND efface = 0",
            (motif, h),
        )
        n += cur.rowcount
    return n
