#!/usr/bin/env python3
"""Filet de sécurité du verdict.

Le blocage est la partie qui peut casser le travail de quelqu'un : un refus de
trop et l'agent est inutilisable, un refus manquant et la sentinelle ne sert à
rien. Ces cas lancent un vrai proxy contre le faux serveur MCP et vérifient ce
que l'agent reçoit réellement.

    python3 tests_controle.py
"""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

RACINE = Path(__file__).parent
REGLES = RACINE / "regles.yaml"
SERVEUR = [sys.executable, str(RACINE / "faux_serveur_mcp.py")]

APPEL_LECTURE = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                 "params": {"name": "read_text_file",
                            "arguments": {"path": "/tmp/sentinelle-essai/.env"}}}
APPEL_SORTIE = {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": "fetch",
                           "arguments": {"url": "https://ailleurs.example/x"}}}
APPEL_ECRITURE = {"jsonrpc": "2.0", "id": 7, "method": "tools/call",
                  "params": {"name": "write_file",
                             "arguments": {"path": "/etc/cron.d/x"}}}


def lancer(messages, dossier, regles=REGLES, observer=False, attendre_fin=True):
    """Fait passer des messages par le proxy, rend les réponses reçues."""
    env = dict(os.environ,
               SENTINELLE_DB=str(dossier / "j.db"),
               SENTINELLE_CLE=str(dossier / "cle"),
               PYTHONPATH=str(RACINE))
    cmd = [sys.executable, "-m", "sentinelle.cli", "--regles", str(regles), "proxy"]
    if observer:
        cmd.append("--observer")
    cmd += ["--"] + SERVEUR
    entree = "".join(json.dumps(m) + "\n" for m in messages)
    p = subprocess.run(cmd, input=entree, capture_output=True, text=True,
                       cwd=RACINE, env=env, timeout=60)
    return [json.loads(l) for l in p.stdout.splitlines() if l.strip()]


def par_id(reponses):
    return {r.get("id"): r for r in reponses}


def est_refus(rep):
    return bool(rep and rep.get("result", {}).get("isError"))


def texte(rep):
    return (rep.get("result", {}).get("content") or [{}])[0].get("text", "")


# ─────────────────────────────────────────────────────────────────── les cas


def cas_blocage(d, echecs):
    """Un secret lu puis une sortie réseau : la sortie ne doit pas partir."""
    rep = par_id(lancer([APPEL_LECTURE, APPEL_SORTIE], d))
    if not est_refus(rep.get(2)):
        echecs.append("BLOCAGE  la sortie réseau n'a pas été bloquée")
    if est_refus(rep.get(1)):
        echecs.append("BLOCAGE  la lecture, elle, aurait dû passer")
    if "fuite-possible" not in texte(rep.get(2, {})):
        echecs.append("BLOCAGE  le refus ne nomme pas la règle")

    # l'appel refusé ne doit jamais avoir atteint l'outil
    con = sqlite3.connect(str(d / "j.db"))
    con.row_factory = sqlite3.Row
    resultats = con.execute(
        "SELECT COUNT(*) c FROM evenements WHERE type='resultat' AND rpc_id='2'"
    ).fetchone()["c"]
    if resultats:
        echecs.append("BLOCAGE  l'appel refusé a quand même été exécuté")
    refus = con.execute(
        "SELECT COUNT(*) c FROM evenements WHERE type='refus'").fetchone()["c"]
    if not refus:
        echecs.append("JOURNAL  le refus n'est pas inscrit dans la chaîne")


def cas_identifiant(d, echecs):
    """L'id de la réponse doit être celui de la requête, type compris."""
    rep = par_id(lancer([APPEL_LECTURE, APPEL_SORTIE], d))
    brut = rep.get(2, {}).get("id")
    if not isinstance(brut, int):
        echecs.append(f"JSON-RPC  id renvoyé en {type(brut).__name__}, "
                      f"un client strict ne le rapprochera jamais")


def cas_observation(d, echecs):
    """--observer note tout et ne bloque rien, quels que soient les modes."""
    rep = par_id(lancer([APPEL_LECTURE, APPEL_SORTIE], d, observer=True))
    if est_refus(rep.get(2)):
        echecs.append("OBSERVER  un appel a été bloqué en observation seule")
    con = sqlite3.connect(str(d / "j.db"))
    n = con.execute("SELECT COUNT(*) c FROM violations").fetchone()[0]
    if not n:
        echecs.append("OBSERVER  plus rien n'est consigné non plus")


def cas_frein(d, echecs):
    """Frein tiré : tout appel d'outil est refusé, la poignée de main passe."""
    env = dict(os.environ, SENTINELLE_DB=str(d / "j.db"),
               SENTINELLE_CLE=str(d / "cle"), PYTHONPATH=str(RACINE))
    subprocess.run([sys.executable, "-m", "sentinelle.cli", "stop",
                    "--motif", "essai"], cwd=RACINE, env=env,
                   capture_output=True, timeout=30)
    depart = {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}}
    rep = par_id(lancer([depart, APPEL_LECTURE], d))
    if est_refus(rep.get(0)):
        echecs.append("FREIN  la poignée de main a été refusée, "
                      "le client ne pourra même pas démarrer")
    if not est_refus(rep.get(1)):
        echecs.append("FREIN  un appel est passé malgré le frein")
    subprocess.run([sys.executable, "-m", "sentinelle.cli", "go"],
                   cwd=RACINE, env=env, capture_output=True, timeout=30)
    rep = par_id(lancer([APPEL_LECTURE], d))
    if est_refus(rep.get(1)):
        echecs.append("FREIN  le relâchement n'a pas repris effet")


def cas_autorisation(d, echecs):
    """L'agent attend ; un humain accorde ; l'appel s'exécute vraiment."""
    resultat = {}

    def agent():
        resultat["rep"] = par_id(lancer([APPEL_ECRITURE], d))

    t = threading.Thread(target=agent)
    t.start()

    env = dict(os.environ, SENTINELLE_DB=str(d / "j.db"),
               SENTINELLE_CLE=str(d / "cle"), PYTHONPATH=str(RACINE))
    demande_id = None
    for _ in range(60):
        time.sleep(0.4)
        try:
            con = sqlite3.connect(str(d / "j.db"))
            con.row_factory = sqlite3.Row
            r = con.execute(
                "SELECT id FROM demandes WHERE etat='attente'").fetchone()
            if r:
                demande_id = r["id"]
                break
        except sqlite3.OperationalError:
            pass
    if demande_id is None:
        echecs.append("AUTORISATION  aucune demande n'est apparue")
        t.join(timeout=30)
        return

    subprocess.run([sys.executable, "-m", "sentinelle.cli", "accorder",
                    str(demande_id)], cwd=RACINE, env=env,
                   capture_output=True, timeout=30)
    t.join(timeout=60)
    rep = resultat.get("rep", {})
    if est_refus(rep.get(7)):
        echecs.append("AUTORISATION  l'appel accordé a quand même été refusé")
    if not rep.get(7):
        echecs.append("AUTORISATION  l'agent n'a jamais reçu de réponse")


def cas_silence(d, echecs):
    """Personne ne répond : le silence vaut refus, pas autorisation."""
    courtes = d / "regles_courtes.yaml"
    courtes.write_text(
        REGLES.read_text(encoding="utf-8").replace(
            "delai_demande_s: 120", "delai_demande_s: 2"),
        encoding="utf-8")
    debut = time.time()
    rep = par_id(lancer([APPEL_ECRITURE], d, regles=courtes))
    duree = time.time() - debut
    if not est_refus(rep.get(7)):
        echecs.append("SILENCE  l'absence de réponse a laissé passer l'appel")
    if duree > 30:
        echecs.append(f"SILENCE  l'attente a duré {duree:.0f} s, délai ignoré")


def _regles_budget(d, **remplacements):
    """Un fichier de règles où seul le budget testé peut bloquer."""
    txt = REGLES.read_text(encoding="utf-8")
    for ancien, nouveau in remplacements.items():
        txt = txt.replace(ancien, nouveau)
    chemin = d / "budget.yaml"
    chemin.write_text(txt, encoding="utf-8")
    return chemin


def cas_budget_compte_juste(d, echecs):
    """Un plafond de N appels laisse passer exactement N appels."""
    regles = _regles_budget(
        d,
        **{"max_appels: 300": "max_appels: 3",
           "mode: demande\n    description: cette session":
               "mode: bloque\n    description: cette session"})
    appels = [{"jsonrpc": "2.0", "id": i, "method": "tools/call",
               "params": {"name": "read_text_file",
                          "arguments": {"path": f"/tmp/f{i}"}}}
              for i in range(1, 7)]
    rep = lancer(appels, d, regles=regles)
    passes = sum(1 for r in rep if not est_refus(r))
    if passes != 3:
        echecs.append(f"BUDGET  plafond 3 → {passes} appels exécutés, "
                      f"attendu exactement 3")
    if "appels-par-session" not in texte(par_id(rep).get(4, {})):
        echecs.append("BUDGET  le refus ne nomme pas le budget en cause")


def cas_budget_refus_gratuit(d, echecs):
    """Un appel refusé ne doit pas consommer de budget.

    Sinon la sentinelle punit deux fois : elle bloque l'appel, puis fait payer
    au suivant un budget dépensé par un appel qui n'a jamais eu lieu.
    """
    regles = _regles_budget(
        d,
        **{"max_appels: 300": "max_appels: 4",
           "mode: demande\n    description: cette session":
               "mode: bloque\n    description: cette session"})
    # deux appels normaux, un que la règle « fuite-possible » bloque,
    # puis deux autres : les cinq licites doivent tenir dans le plafond de 4
    appels = [
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "read_text_file",
                    "arguments": {"path": "/tmp/sentinelle-essai/.env"}}},
        APPEL_SORTIE,                       # bloqué par la règle, pas le budget
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "read_text_file", "arguments": {"path": "/tmp/a"}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "read_text_file", "arguments": {"path": "/tmp/b"}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
         "params": {"name": "read_text_file", "arguments": {"path": "/tmp/c"}}},
    ]
    rep = par_id(lancer(appels, d, regles=regles))
    if not est_refus(rep.get(2)):
        echecs.append("BUDGET  la sortie réseau aurait dû être bloquée")
    for i in (1, 3, 4, 5):
        if est_refus(rep.get(i)):
            echecs.append(f"BUDGET  l'appel {i} a été refusé : le budget a "
                          f"compté un appel qui n'a jamais été exécuté")
            break


def cas_budget_compteur(d, echecs):
    """Le compteur affiché correspond à ce qui s'est réellement passé."""
    import sqlite3 as _sq
    appels = [{"jsonrpc": "2.0", "id": i, "method": "tools/call",
               "params": {"name": "read_text_file",
                          "arguments": {"path": f"/tmp/f{i}"}}}
              for i in range(1, 5)]
    lancer(appels, d)
    sys.path.insert(0, str(RACINE))
    from sentinelle import budgets as bud
    from sentinelle import regles as rmod
    con = _sq.connect(str(d / "j.db"))
    con.row_factory = _sq.Row
    liste, tarifs = rmod.charger(REGLES).budgets_tarifs()
    run = con.execute("SELECT id FROM runs ORDER BY debut DESC LIMIT 1").fetchone()
    session = [e for e in bud.tous(con, liste, tarifs, run["id"])
               if e["portee"] == "session"]
    if not session:
        echecs.append("COMPTEUR  aucun budget de portée session à mesurer")
        return
    if session[0]["appels"] != 4:
        echecs.append(f"COMPTEUR  {session[0]['appels']} appels comptés, "
                      f"4 réellement passés")


def principal() -> int:
    cas = [cas_blocage, cas_identifiant, cas_observation, cas_frein,
           cas_autorisation, cas_silence,
           cas_budget_compte_juste, cas_budget_refus_gratuit,
           cas_budget_compteur]
    echecs: list[str] = []
    for fonction in cas:
        dossier = Path(tempfile.mkdtemp(prefix="sentinelle-essai-"))
        try:
            fonction(dossier, echecs)
            print(f"  {fonction.__name__}")
        except Exception as exc:
            echecs.append(f"{fonction.__name__} a levé une exception : {exc}")
        finally:
            shutil.rmtree(dossier, ignore_errors=True)

    if echecs:
        print("\n" + "\n".join(echecs))
        print(f"\n{len(echecs)} échec(s).")
        return 1
    print(f"\n{len(cas)} scénarios passés.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
