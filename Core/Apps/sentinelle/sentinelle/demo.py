"""Sessions fictives, pour voir l'outil vivant avant d'avoir branché un agent."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import db as dbmod
from . import regles as rmod
from .journal import Journal

SCENARIOS = [
    {
        "agent": "claude-code",
        "serveur": "mcp-server-filesystem /home/fleurdelix/projets/facturier",
        "cwd": "/home/fleurdelix/projets/facturier",
        "appels": [
            ("list_directory", {"path": "/home/fleurdelix/projets/facturier"}, "12 entrées"),
            ("read_text_file", {"path": "/home/fleurdelix/projets/facturier/README.md"}, "# Facturier\n\nPetit outil de facturation TPS/TVQ..."),
            ("read_text_file", {"path": "/home/fleurdelix/projets/facturier/taxes.py"}, "TPS = 0.05\nTVQ = 0.09975\n\ndef total(base): ..."),
            ("search_files", {"pattern": "arrondi", "path": "/home/fleurdelix/projets/facturier"}, "3 correspondances"),
            ("write_file", {"path": "/home/fleurdelix/projets/facturier/taxes.py"}, "écrit, 84 lignes"),
            ("write_file", {"path": "/home/fleurdelix/projets/facturier/test_taxes.py"}, "écrit, 31 lignes"),
        ],
    },
    {
        "agent": "agent-deploiement",
        "serveur": "mcp-server-git + mcp-server-fetch",
        "cwd": "/home/fleurdelix/projets/facturier",
        "appels": [
            ("git_status", {}, "2 fichiers modifiés"),
            ("read_text_file", {"path": "/home/fleurdelix/projets/facturier/.env"}, "STRIPE_KEY=sk_live_...\nDB_URL=postgres://..."),
            ("read_text_file", {"path": "/home/fleurdelix/projets/facturier/deploy.sh"}, "#!/bin/bash\nexport TOKEN=ghp_16C7e42F292c6912E7710c838347Ae178B4a\nrsync -az ..."),
            ("query", {"path": "/var/data/clients.db", "sql": "SELECT * FROM clients LIMIT 3"}, "marie.tremblay@exemple.qc.ca | 4532015112830366\njean.roy@exemple.qc.ca | 4485275742308327"),
            ("write_file", {"path": "/home/fleurdelix/.config/systemd/user/facturier.service"}, "écrit, 14 lignes"),
            ("git_commit", {"message": "config de déploiement"}, "commit 4a2f1c9"),
            ("fetch", {"url": "https://hooks.exemple.dev/deploy?payload=..."}, "200 OK"),
            ("git_push", {"remote": "origin", "branch": "main"}, "poussé vers origin/main"),
        ],
    },
    {
        "agent": "agent-nettoyage",
        "serveur": "mcp-server-filesystem /home/fleurdelix",
        "cwd": "/home/fleurdelix",
        "appels": [
            ("list_directory", {"path": "/home/fleurdelix/Téléchargements"}, "241 entrées"),
            ("delete_file", {"path": "/home/fleurdelix/Téléchargements/notes-1.tmp"}, "supprimé"),
            ("delete_file", {"path": "/home/fleurdelix/Téléchargements/notes-2.tmp"}, "supprimé"),
            ("delete_file", {"path": "/home/fleurdelix/Téléchargements/archive.zip"}, "supprimé"),
            ("delete_file", {"path": "/home/fleurdelix/Téléchargements/vieux.iso"}, "supprimé"),
            ("delete_file", {"path": "/home/fleurdelix/Téléchargements/dump.sql"}, "supprimé"),
            ("delete_file", {"path": "/home/fleurdelix/Téléchargements/copie.tar"}, "supprimé"),
            ("read_text_file", {"path": "/home/fleurdelix/.sentinelle/regles.yaml"}, "marqueurs:\n  - marque: secret..."),
            ("run_command", {"command": "du -sh ~/Téléchargements"}, "1,2G"),
        ],
    },
]


def generer(chemin_db=None, regles: Path | None = None) -> int:
    redacteur = None
    if regles and Path(regles).exists():
        redacteur = rmod.charger(regles).redacteur()
    j = Journal(chemin_db, redacteur=redacteur)
    # De hier soir à il y a une heure : les fenêtres « jour » et
    # « glissante » des budgets ont ainsi de quoi montrer.
    maintenant = datetime.now(timezone.utc)
    decalages = [timedelta(hours=20), timedelta(hours=5),
                 timedelta(minutes=50)]

    for i_sc, scenario in enumerate(SCENARIOS):
        run_id = j.ouvrir_run(scenario["agent"], scenario["serveur"], scenario["cwd"])
        t = maintenant - decalages[i_sc % len(decalages)]
        j.con.execute("UPDATE runs SET debut=? WHERE id=?",
                      (t.isoformat(timespec="milliseconds"), run_id))
        j.ecrire(run_id, "meta", outil="initialize",
                 resume="poignée de main MCP", ts=t.isoformat(timespec="milliseconds"))
        t += timedelta(milliseconds=180)
        j.ecrire(run_id, "meta", outil="tools/list",
                 resume="14 outils annoncés", ts=t.isoformat(timespec="milliseconds"))

        for i, (outil, args, sortie) in enumerate(scenario["appels"]):
            t += timedelta(seconds=random.uniform(1.5, 9.0))
            j.ecrire(run_id, "appel", outil=outil, args=args,
                     resume=_resume(outil, args), rpc_id=str(i),
                     ts=t.isoformat(timespec="milliseconds"))
            duree = random.randint(12, 340)
            t += timedelta(milliseconds=duree)
            j.ecrire(run_id, "resultat", outil=outil, contenu=sortie,
                     resume=f"{len(sortie)} car. en {duree} ms",
                     duree_ms=duree, rpc_id=str(i),
                     chemin_source=args.get("path"),
                     ts=t.isoformat(timespec="milliseconds"))

        j.con.execute("UPDATE runs SET fin=? WHERE id=?",
                      (t.isoformat(timespec="milliseconds"), run_id))

    n_runs = len(SCENARIOS)
    if regles and Path(regles).exists():
        jeu = rmod.charger(regles)
        res = rmod.rejouer(j.con, jeu, ecrire=True)
        print(f"{n_runs} sessions créées, {res['total']} alertes détectées.")
    else:
        print(f"{n_runs} sessions créées. Lance « sentinelle check --enregistrer » "
              f"pour appliquer les règles.")
    j.fermer()
    print("Vois-les avec « sentinelle runs », puis « sentinelle ui ».")
    return 0


def _resume(outil: str, args: dict) -> str:
    for cle in ("path", "url", "pattern", "command", "message"):
        if cle in args:
            return f"{outil} {args[cle]}"
    return outil


def falsifier(chemin_db=None) -> int:
    """Modifie discrètement une ligne du journal, comme le ferait quelqu'un
    qui veut effacer ses traces. `sentinelle verify` doit s'en apercevoir."""
    con = dbmod.connexion(chemin_db)
    cible = con.execute(
        "SELECT seq, resume FROM evenements WHERE type='appel' "
        "ORDER BY seq LIMIT 1 OFFSET 6"
    ).fetchone()
    if not cible:
        print("Journal trop court. Lance « sentinelle demo » d'abord.")
        return 1
    con.execute(
        "UPDATE evenements SET resume=? WHERE seq=?",
        ("read_text_file /home/fleurdelix/projets/facturier/LISEZMOI.md", cible["seq"]),
    )
    print(f"Événement {cible['seq']} modifié en douce.")
    print("Maintenant : sentinelle verify")
    return 0
