"""Budgets : compter ce qui passe, et couper quand c'est trop.

Un mot sur ce qui est mesuré, parce que la nuance compte. La sentinelle est
posée entre l'agent et ses outils : elle voit les appels d'outils, pas le
dialogue avec le modèle. Elle ne connaît donc **pas** ta facture de jetons. Ce
qu'elle sait compter :

    appels    combien de fois l'agent a demandé un outil
    octets    combien de données les outils lui ont rapporté
    coût      une estimation, à partir d'un tarif que tu fixes par outil

Le coût est donc une convention, pas une facture. C'est utile quand tes outils
appellent des API payantes et que tu connais leur prix ; ça ne remplace pas le
tableau de bord de ton fournisseur.

Les compteurs ne sont stockés nulle part : ils sont recalculés depuis le
journal, qui est scellé. Un compteur qu'on peut remettre à zéro sans laisser de
trace ne vaut rien, et un chiffre dérivé n'a pas à être scellé ; le fait qui le
produit, lui, l'est déjà.
"""

from __future__ import annotations

import fnmatch
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

PORTEES = ("session", "heure", "jour", "semaine", "glissante", "toujours")


@dataclass
class Budget:
    id: str
    portee: str = "jour"
    fenetre_s: float = 3600.0          # pour la portée glissante
    outil: list[str] | None = None     # None = tous les outils
    max_appels: int | None = None
    max_cout: float | None = None
    max_octets: int | None = None
    mode: str = "observe"
    severite: str = "haute"
    description: str = ""
    alerte_a: float = 0.8              # seuil d'avertissement, en fraction

    @classmethod
    def depuis_yaml(cls, d: dict) -> "Budget":
        outil = d.get("outil")
        if isinstance(outil, str):
            outil = [outil]
        return cls(
            id=d["id"],
            portee=d.get("portee", "jour"),
            fenetre_s=float(d.get("fenetre_s", 3600)),
            outil=outil,
            max_appels=d.get("max_appels"),
            max_cout=d.get("max_cout"),
            max_octets=d.get("max_octets"),
            mode=d.get("mode", "observe"),
            severite=d.get("severite", "haute"),
            description=d.get("description", ""),
            alerte_a=float(d.get("alerte_a", 0.8)),
        )

    def concerne(self, outil: str | None) -> bool:
        if not self.outil:
            return True
        if outil is None:
            return False
        return any(fnmatch.fnmatch(outil, m) for m in self.outil)


@dataclass
class Depassement:
    budget: str
    mode: str
    severite: str
    explication: str
    mesure: str          # appels | cout | octets


@dataclass
class Tarifs:
    """Prix par appel, par outil. Les motifs acceptent les jokers."""
    defaut: float = 0.0
    par_outil: dict[str, float] = field(default_factory=dict)

    @classmethod
    def depuis_yaml(cls, d: dict | None) -> "Tarifs":
        d = dict(d or {})
        defaut = float(d.pop("defaut", 0.0) or 0.0)
        return cls(defaut=defaut,
                   par_outil={k: float(v) for k, v in d.items()})

    def prix(self, outil: str | None) -> float:
        if outil:
            if outil in self.par_outil:
                return self.par_outil[outil]
            for motif, prix in self.par_outil.items():
                if fnmatch.fnmatch(outil, motif):
                    return prix
        return self.defaut


# ────────────────────────────────────────────────────────────── les fenêtres


def _local_minuit(maintenant: datetime) -> datetime:
    local = maintenant.astimezone()
    return local.replace(hour=0, minute=0, second=0, microsecond=0)


def bornes(budget: Budget, maintenant: datetime | None = None
           ) -> tuple[str | None, str | None]:
    """Rend (début de la fenêtre, moment de remise à zéro), en ISO UTC.

    Un budget quotidien se remet à zéro à minuit **chez toi**, pas à minuit
    UTC : un budget qui repart à 20 h locale n'aurait aucun sens.
    """
    maintenant = maintenant or datetime.now(timezone.utc)
    if budget.portee == "toujours":
        return None, None
    if budget.portee == "session":
        return None, None          # borné par le run, pas par le temps
    if budget.portee == "glissante":
        debut = maintenant - timedelta(seconds=budget.fenetre_s)
        return debut.isoformat(timespec="milliseconds"), None
    if budget.portee == "heure":
        debut = maintenant.replace(minute=0, second=0, microsecond=0)
        fin = debut + timedelta(hours=1)
    elif budget.portee == "semaine":
        minuit = _local_minuit(maintenant)
        debut = minuit - timedelta(days=minuit.weekday())
        fin = debut + timedelta(days=7)
    else:  # jour
        debut = _local_minuit(maintenant)
        fin = debut + timedelta(days=1)
    return (debut.astimezone(timezone.utc).isoformat(timespec="milliseconds"),
            fin.astimezone(timezone.utc).isoformat(timespec="milliseconds"))


# ──────────────────────────────────────────────────────────── les compteurs


def _appels(con: sqlite3.Connection, depuis: str | None, run_id: str | None
            ) -> dict[str, int]:
    """Appels réellement exécutés, par outil.

    Un appel refusé ne consomme pas de budget : ce serait doublement punitif,
    et ça viderait le budget d'une session que la sentinelle a justement
    empêchée de dépenser.
    """
    sql = ["""SELECT e.outil, COUNT(*) n FROM evenements e
              WHERE e.type='appel'
                AND NOT EXISTS (SELECT 1 FROM evenements r
                                WHERE r.type='refus' AND r.run_id=e.run_id
                                  AND r.rpc_id=e.rpc_id)"""]
    params: list = []
    if depuis:
        sql.append("AND e.ts >= ?")
        params.append(depuis)
    if run_id:
        sql.append("AND e.run_id = ?")
        params.append(run_id)
    sql.append("GROUP BY e.outil")
    return {r["outil"]: r["n"] for r in con.execute(" ".join(sql), params)}


def _octets(con: sqlite3.Connection, depuis: str | None, run_id: str | None
            ) -> dict[str, int]:
    """Volume rapporté par les outils, par outil."""
    sql = ["""SELECT e.outil, COALESCE(SUM(b.taille), 0) o
              FROM evenements e JOIN blobs b ON b.hash = e.blob_hash
              WHERE e.type='resultat'"""]
    params: list = []
    if depuis:
        sql.append("AND e.ts >= ?")
        params.append(depuis)
    if run_id:
        sql.append("AND e.run_id = ?")
        params.append(run_id)
    sql.append("GROUP BY e.outil")
    return {r["outil"]: int(r["o"]) for r in con.execute(" ".join(sql), params)}


def etat(con: sqlite3.Connection, budget: Budget, tarifs: Tarifs,
         run_id: str | None = None, maintenant: datetime | None = None) -> dict:
    """Où en est ce budget, maintenant."""
    debut, remise = bornes(budget, maintenant)
    portee_run = run_id if budget.portee == "session" else None

    appels = _appels(con, debut, portee_run)
    octets = _octets(con, debut, portee_run)

    n = sum(v for outil, v in appels.items() if budget.concerne(outil))
    cout = sum(v * tarifs.prix(outil)
               for outil, v in appels.items() if budget.concerne(outil))
    o = sum(v for outil, v in octets.items() if budget.concerne(outil))

    fractions = []
    if budget.max_appels:
        fractions.append(n / budget.max_appels)
    if budget.max_cout:
        fractions.append(cout / budget.max_cout)
    if budget.max_octets:
        fractions.append(o / budget.max_octets)
    fraction = max(fractions) if fractions else 0.0

    return {
        "id": budget.id,
        "portee": budget.portee,
        "outil": budget.outil,
        "mode": budget.mode,
        "description": budget.description,
        "appels": n, "max_appels": budget.max_appels,
        "cout": round(cout, 4), "max_cout": budget.max_cout,
        "octets": o, "max_octets": budget.max_octets,
        "fraction": round(fraction, 4),
        "depasse": fraction >= 1.0,
        "proche": budget.alerte_a <= fraction < 1.0,
        "debut": debut,
        "remise_a_zero": remise,
    }


def tous(con: sqlite3.Connection, budgets: list[Budget], tarifs: Tarifs,
         run_id: str | None = None) -> list[dict]:
    return [etat(con, b, tarifs, run_id) for b in budgets]


# ─────────────────────────────────────────────────────────────── le verdict


def verdict(con: sqlite3.Connection, budgets: list[Budget], tarifs: Tarifs,
            run_id: str, outil: str | None) -> list[Depassement]:
    """L'appel qu'on s'apprête à laisser passer tient-il dans les budgets ?

    L'appel en cours est déjà inscrit au journal quand on arrive ici : il est
    donc déjà dans le compte, et il ne faut surtout pas l'ajouter une seconde
    fois. S'il est finalement refusé, il sortira du compte tout seul, la
    requête excluant les appels refusés.
    """
    trouves: list[Depassement] = []
    for b in budgets:
        if not b.concerne(outil):
            continue
        e = etat(con, b, tarifs, run_id)

        if b.max_appels is not None and e["appels"] > b.max_appels:
            trouves.append(Depassement(
                b.id, b.mode, b.severite,
                b.description or f"plafond de {b.max_appels} appels par "
                                 f"{b.portee} atteint",
                "appels"))
        elif b.max_cout is not None and e["cout"] > b.max_cout:
            trouves.append(Depassement(
                b.id, b.mode, b.severite,
                b.description or f"{e['cout']:.2f} $ estimés, plafond "
                                 f"{b.max_cout:.2f} $ par {b.portee}",
                "cout"))
        elif b.max_octets is not None and e["octets"] > b.max_octets:
            trouves.append(Depassement(
                b.id, b.mode, b.severite,
                b.description or f"{e['octets'] / 1e6:.1f} Mo rapportés, "
                                 f"plafond {b.max_octets / 1e6:.1f} Mo "
                                 f"par {b.portee}",
                "octets"))
    return trouves


def charger(data: dict) -> tuple[list[Budget], Tarifs]:
    budgets = [Budget.depuis_yaml(b) for b in (data.get("budgets") or [])]
    return budgets, Tarifs.depuis_yaml(data.get("tarifs"))


def valider(budgets: list[Budget]) -> list[str]:
    erreurs = []
    vus = set()
    for b in budgets:
        if b.id in vus:
            erreurs.append(f"budget en double : {b.id}")
        vus.add(b.id)
        if b.portee not in PORTEES:
            erreurs.append(f"{b.id} : portée inconnue « {b.portee} », "
                           f"attendu {' · '.join(PORTEES)}")
        if b.max_appels is None and b.max_cout is None and b.max_octets is None:
            erreurs.append(f"{b.id} : aucun plafond (max_appels, max_cout "
                           f"ou max_octets)")
        if b.mode not in ("observe", "demande", "bloque"):
            erreurs.append(f"{b.id} : mode inconnu « {b.mode} »")
    return erreurs
