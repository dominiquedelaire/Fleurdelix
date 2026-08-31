from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import db as dbmod
from . import journal as jmod
from . import regles as rmod

GRIS = "\033[90m"
JAUNE = "\033[33m"
ROUGE = "\033[31m"
VERT = "\033[32m"
RAZ = "\033[0m"

COULEUR_SEV = {"info": GRIS, "moyenne": JAUNE, "haute": JAUNE, "critique": ROUGE}


def _chemin_regles(args) -> Path | None:
    if args.regles:
        return Path(args.regles)
    local = Path.cwd() / "regles.yaml"
    return local if local.exists() else None


# ------------------------------------------------------------------ commandes


def cmd_proxy(args) -> int:
    from .proxy import Proxy

    if not args.commande:
        print("usage : sentinelle proxy -- <commande du serveur MCP>", file=sys.stderr)
        return 2
    return Proxy(args.commande, regles=_chemin_regles(args), db=args.db,
                 observer_seulement=args.observer).lancer()


def cmd_demandes(args) -> int:
    from . import controle

    con = dbmod.connexion(args.db)
    lignes = controle.en_attente(con)
    if not lignes:
        print("Aucune demande en attente.")
        return 0
    print(f"\n{len(lignes)} demande(s) en attente :\n")
    for d in lignes:
        c = COULEUR_SEV.get(d["severite"], JAUNE)
        print(f"  [{d['id']}] {c}{d['regle']}{RAZ} : {d['explication']}")
        print(f"       {d['resume']}")
        print(f"       {GRIS}{d['cree_ts'][11:19]} · session {d['run_id']}{RAZ}")
    print(f"\n{GRIS}sentinelle accorder <id>  ·  sentinelle refuser <id>{RAZ}")
    return 0


def cmd_accorder(args) -> int:
    return _decider(args, "accorde", "Accordé")


def cmd_refuser(args) -> int:
    return _decider(args, "refuse", "Refusé")


def _decider(args, etat: str, mot: str) -> int:
    from . import controle

    con = dbmod.connexion(args.db)
    if controle.decider(con, args.id, etat, motif=args.motif or ""):
        print(f"{mot}. L'agent reçoit la décision dans la seconde.")
        return 0
    print("Cette demande n'est plus en attente (déjà tranchée ou expirée).",
          file=sys.stderr)
    return 1


def cmd_stop(args) -> int:
    from . import controle

    con = dbmod.connexion(args.db)
    controle.basculer_arret(con, True, args.motif or "arrêt manuel")
    print(f"{ROUGE}Frein tiré.{RAZ} Tout appel d'outil est refusé, "
          f"quelles que soient les règles.")
    print(f"{GRIS}Relâcher : sentinelle go{RAZ}")
    return 0


def cmd_go(args) -> int:
    from . import controle

    con = dbmod.connexion(args.db)
    controle.basculer_arret(con, False, "")
    print(f"{VERT}Frein relâché.{RAZ} Les règles reprennent la main.")
    return 0


def cmd_runs(args) -> int:
    con = dbmod.connexion(args.db)
    lignes = con.execute(
        """SELECT r.*, (SELECT COUNT(*) FROM violations v WHERE v.run_id=r.id) AS viol
           FROM runs r ORDER BY r.debut DESC LIMIT ?""",
        (args.limite,),
    ).fetchall()
    if not lignes:
        print("Aucune session enregistrée. Essaie « sentinelle demo » pour voir "
              "à quoi ça ressemble.")
        return 0
    for r in lignes:
        marque = f"{ROUGE}{r['viol']} alerte(s){RAZ}" if r["viol"] else f"{GRIS}-{RAZ}"
        print(f"{r['id']}  {r['debut'][:19]}  {r['nb_evts']:>4} évts  "
              f"{marque:<22} {GRIS}{r['serveur'][:50]}{RAZ}")
    return 0


def cmd_show(args) -> int:
    con = dbmod.connexion(args.db)
    run = con.execute("SELECT * FROM runs WHERE id=?", (args.run_id,)).fetchone()
    if not run:
        print(f"Session {args.run_id} introuvable.", file=sys.stderr)
        return 1

    viols: dict[int, list] = {}
    for v in con.execute("SELECT * FROM violations WHERE run_id=?", (args.run_id,)):
        viols.setdefault(v["evt_seq"], []).append(v)

    print(f"\nSession {run['id']}  ·  {run['agent']}  ·  {run['serveur']}")
    print(f"{GRIS}{'─' * 72}{RAZ}")
    for e in con.execute(
        "SELECT * FROM evenements WHERE run_id=? ORDER BY seq", (args.run_id,)
    ):
        if e["type"] == "meta" and not args.tout:
            continue
        heure = e["ts"][11:19]
        sceau = e["hash"][:6]
        symbole = {"appel": "→", "resultat": "←", "erreur": "✗",
                   "meta": "·", "refus": "⊘"}.get(e["type"], "·")
        print(f"{GRIS}{sceau}{RAZ} {heure} {symbole} {e['resume']}")
        for v in viols.get(e["seq"], []):
            c = COULEUR_SEV.get(v["severite"], JAUNE)
            origine = f" (origine : évt {v['origine_seq']})" if v["origine_seq"] else ""
            print(f"       {c}⚑ {v['regle']} : {v['explication']}{origine}{RAZ}")
    print()
    return 0


def cmd_verify(args) -> int:
    con = dbmod.connexion(args.db)
    ok, seq, message = jmod.verifier(con)
    print(f"{VERT if ok else ROUGE}{message}{RAZ}")

    ok_b, intacts, effaces, alteres = jmod.verifier_blobs(con)
    detail = f"contenus : {intacts} intacts"
    if effaces:
        detail += f", {effaces} effacés (chaîne préservée)"
    if alteres:
        detail += f", {len(alteres)} ALTÉRÉS"
    print(f"{VERT if ok_b else ROUGE}{detail}{RAZ}")
    return 0 if (ok and ok_b) else 1


def _jauge(fraction: float, largeur: int = 24) -> str:
    plein = min(largeur, int(round(fraction * largeur)))
    couleur = ROUGE if fraction >= 1 else (JAUNE if fraction >= 0.8 else VERT)
    return f"{couleur}{'█' * plein}{GRIS}{'░' * (largeur - plein)}{RAZ}"


def _octets_lisibles(n: int) -> str:
    for unite, seuil in (("Go", 1e9), ("Mo", 1e6), ("ko", 1e3)):
        if n >= seuil:
            return f"{n / seuil:.1f} {unite}"
    return f"{n} o"


def cmd_budget(args) -> int:
    from . import budgets as bud

    chemin = _chemin_regles(args)
    if not chemin:
        print("Aucun fichier de règles. Indique-le avec --regles regles.yaml",
              file=sys.stderr)
        return 2
    jeu = rmod.charger(chemin)
    liste, tarifs = jeu.budgets_tarifs()
    if not liste:
        print("Aucun budget défini dans " + str(chemin))
        return 0

    con = dbmod.connexion(args.db)
    run_id = args.session
    if not run_id:
        row = con.execute(
            "SELECT id FROM runs ORDER BY debut DESC LIMIT 1").fetchone()
        run_id = row["id"] if row else None

    print()
    for e in bud.tous(con, liste, tarifs, run_id):
        etiquette = f"{e['id']}"
        if e["outil"]:
            etiquette += f" {GRIS}[{', '.join(e['outil'])}]{RAZ}"
        print(f"  {etiquette}")

        mesures = []
        if e["max_appels"]:
            mesures.append(f"{e['appels']} / {e['max_appels']} appels")
        if e["max_cout"]:
            mesures.append(f"{e['cout']:.2f} / {e['max_cout']:.2f} $")
        if e["max_octets"]:
            mesures.append(f"{_octets_lisibles(e['octets'])} / "
                           f"{_octets_lisibles(e['max_octets'])}")
        etat_txt = ROUGE + "dépassé" + RAZ if e["depasse"] else (
            JAUNE + "proche" + RAZ if e["proche"] else GRIS + e["mode"] + RAZ)
        print(f"    {_jauge(e['fraction'])} {' · '.join(mesures)}  {etat_txt}")

        portee = e["portee"]
        if e["remise_a_zero"]:
            from datetime import datetime
            quand = datetime.fromisoformat(e["remise_a_zero"]).astimezone()
            portee += f", remise à zéro {quand.strftime('%d/%m à %Hh%M')}"
        elif portee == "session":
            portee += f" {run_id or '-'}"
        print(f"    {GRIS}{portee}{RAZ}\n")

    if tarifs.par_outil or tarifs.defaut:
        print(f"  {GRIS}Coûts estimés à partir des tarifs de {chemin.name}, "
              f"pas d'une facture réelle.{RAZ}\n")
    return 0


def cmd_secrets(args) -> int:
    con = dbmod.connexion(args.db)
    lignes = con.execute(
        """SELECT s.*, (SELECT COUNT(DISTINCT run_id) FROM secrets_vus v
                        WHERE v.empreinte = s.empreinte) sessions
           FROM secrets s ORDER BY s.occurrences DESC, s.genre"""
    ).fetchall()
    if not lignes:
        print("Aucun secret repéré dans le journal.")
        return 0

    print(f"\n{len(lignes)} valeur(s) sensible(s) ont traversé les agents. "
          f"Aucune n'est stockée en clair.\n")
    for r in lignes:
        print(f"  {r['genre']:<18} {JAUNE}{r['empreinte'][:6]}{RAZ}  "
              f"{r['longueur']:>3} car.  vue {r['occurrences']}× "
              f"dans {r['sessions']} session(s)  "
              f"{GRIS}{r['premier_ts'][:16].replace('T', ' ')}{RAZ}")

    if args.empreinte:
        print(f"\nOù {args.empreinte} est passé :")
        for r in con.execute(
            """SELECT e.seq, e.ts, e.resume, e.run_id FROM secrets_vus v
               JOIN evenements e ON e.seq = v.evt_seq
               WHERE v.empreinte LIKE ? || '%' ORDER BY e.seq""",
            (args.empreinte,),
        ):
            print(f"  évt {r['seq']:>4}  {r['ts'][11:19]}  {r['resume'][:70]}")
    else:
        print(f"\n{GRIS}Pour suivre une valeur : sentinelle secrets <empreinte>{RAZ}")
    return 0


def cmd_oublier(args) -> int:
    con = dbmod.connexion(args.db)
    n = jmod.oublier(
        con,
        blob_hash=args.contenu,
        empreinte_secret=args.secret,
        motif=args.motif,
    )
    print(f"{n} contenu(s) détruit(s). Les événements et leurs sceaux restent.")
    ok, *_ = jmod.verifier(con)
    print(f"{VERT if ok else ROUGE}Chaîne toujours "
          f"{'intacte' if ok else 'rompue'}.{RAZ}")
    return 0


def cmd_rediger(args) -> int:
    """Essayer le caviardage sur un texte, sans rien enregistrer."""
    chemin = _chemin_regles(args)
    red = rmod.charger(chemin).redacteur() if chemin else None
    if red is None:
        from .redaction import Redacteur
        red = Redacteur()
    texte = (Path(args.fichier).read_text(encoding="utf-8")
             if args.fichier else sys.stdin.read())
    sortie, trouvailles = red.rediger(texte)
    print(sortie)
    if trouvailles:
        print(f"\n{GRIS}{len(trouvailles)} valeur(s) caviardée(s) : "
              f"{', '.join(sorted({t.genre for t in trouvailles}))}{RAZ}",
              file=sys.stderr)
    return 0


def cmd_check(args) -> int:
    chemin = _chemin_regles(args)
    if not chemin:
        print("Aucun fichier de règles. Indique-le avec --regles regles.yaml",
              file=sys.stderr)
        return 2
    jeu = rmod.charger(chemin)
    erreurs = jeu.valider()
    if erreurs:
        for e in erreurs:
            print(f"{ROUGE}règle invalide : {e}{RAZ}", file=sys.stderr)
        return 2

    con = dbmod.connexion(args.db)
    res = rmod.rejouer(con, jeu, ecrire=args.enregistrer)
    if not res["total"]:
        print("Aucune règle ne se déclenche sur l'historique.")
        return 0

    print(f"\n{res['total']} déclenchement(s) sur l'historique :\n")
    for regle, n in sorted(res["par_regle"].items(), key=lambda kv: -kv[1]):
        print(f"  {n:>4}×  {regle}")
        for ex in res["exemples"][regle]:
            print(f"        {GRIS}évt {ex['seq']} · {ex['explication']}{RAZ}")
    if args.enregistrer:
        print(f"\n{VERT}Alertes enregistrées dans le journal.{RAZ}")
    else:
        print(f"\n{GRIS}Rien n'a été bloqué ni enregistré. "
              f"Ajoute --enregistrer pour les garder.{RAZ}")
    return 0


def cmd_demo(args) -> int:
    from . import demo

    if args.falsifier:
        return demo.falsifier(args.db)
    return demo.generer(args.db, regles=_chemin_regles(args))


def cmd_ui(args) -> int:
    from . import webview_app

    return webview_app.lancer(args.db, navigateur=args.navigateur, port=args.port)


def cmd_export(args) -> int:
    con = dbmod.connexion(args.db)
    sortie = {
        "runs": [dict(r) for r in con.execute("SELECT * FROM runs")],
        "evenements": [dict(r) for r in con.execute("SELECT * FROM evenements")],
        "violations": [dict(r) for r in con.execute("SELECT * FROM violations")],
    }
    Path(args.fichier).write_text(
        json.dumps(sortie, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Exporté vers {args.fichier}")
    return 0


# ---------------------------------------------------------------- assemblage


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="sentinelle",
        description="Boîte noire pour agents IA : enregistre, scelle, explique.",
    )
    p.add_argument("--db", help="chemin du journal (défaut ~/.sentinelle/journal.db)")
    p.add_argument("--regles", help="fichier de règles YAML")
    sous = p.add_subparsers(dest="cmd", required=True)

    sp = sous.add_parser("proxy", help="relaie un serveur MCP et enregistre tout")
    sp.add_argument("--observer", action="store_true",
                    help="tout enregistrer sans jamais bloquer, quels que "
                         "soient les modes des règles")
    sp.add_argument("commande", nargs=argparse.REMAINDER)
    sp.set_defaults(func=cmd_proxy)

    sp = sous.add_parser("demandes", help="ce qui attend ton feu vert")
    sp.set_defaults(func=cmd_demandes)

    sp = sous.add_parser("accorder", help="autoriser une demande")
    sp.add_argument("id", type=int)
    sp.add_argument("--motif")
    sp.set_defaults(func=cmd_accorder)

    sp = sous.add_parser("refuser", help="refuser une demande")
    sp.add_argument("id", type=int)
    sp.add_argument("--motif")
    sp.set_defaults(func=cmd_refuser)

    sp = sous.add_parser("stop", help="frein d'urgence : tout refuser")
    sp.add_argument("--motif")
    sp.set_defaults(func=cmd_stop)

    sp = sous.add_parser("go", help="relâcher le frein d'urgence")
    sp.set_defaults(func=cmd_go)

    sp = sous.add_parser("runs", help="liste les sessions")
    sp.add_argument("-n", "--limite", type=int, default=20)
    sp.set_defaults(func=cmd_runs)

    sp = sous.add_parser("show", help="déroule une session")
    sp.add_argument("run_id")
    sp.add_argument("--tout", action="store_true", help="inclure les événements meta")
    sp.set_defaults(func=cmd_show)

    sp = sous.add_parser("verify", help="vérifie la chaîne de hash")
    sp.set_defaults(func=cmd_verify)

    sp = sous.add_parser("budget", help="où en sont les compteurs")
    sp.add_argument("--session", help="session à mesurer (défaut : la dernière)")
    sp.set_defaults(func=cmd_budget)

    sp = sous.add_parser("secrets", help="ce qui est passé sans être stocké")
    sp.add_argument("empreinte", nargs="?", help="suivre une valeur précise")
    sp.set_defaults(func=cmd_secrets)

    sp = sous.add_parser("oublier", help="détruit un contenu, garde le sceau")
    sp.add_argument("--contenu", help="hash du contenu à détruire")
    sp.add_argument("--secret", help="tout contenu où cette empreinte apparaît")
    sp.add_argument("--motif", default="effacement demandé")
    sp.set_defaults(func=cmd_oublier)

    sp = sous.add_parser("rediger", help="essaie le caviardage sur un texte")
    sp.add_argument("fichier", nargs="?", help="défaut : entrée standard")
    sp.set_defaults(func=cmd_rediger)

    sp = sous.add_parser("check", help="rejoue les règles sur l'historique")
    sp.add_argument("--enregistrer", action="store_true")
    sp.set_defaults(func=cmd_check)

    sp = sous.add_parser("demo", help="remplit le journal avec des sessions fictives")
    sp.add_argument("--falsifier", action="store_true",
                    help="modifie une ligne pour montrer que verify le détecte")
    sp.set_defaults(func=cmd_demo)

    sp = sous.add_parser("ui", help="ouvre la fenêtre")
    sp.add_argument("--navigateur", action="store_true",
                    help="servir l'interface en local au lieu d'ouvrir une fenêtre")
    sp.add_argument("--port", type=int, default=8731)
    sp.set_defaults(func=cmd_ui)

    sp = sous.add_parser("export", help="exporte le journal en JSON")
    sp.add_argument("fichier")
    sp.set_defaults(func=cmd_export)

    args = p.parse_args(argv)
    if args.cmd == "proxy" and args.commande and args.commande[0] == "--":
        args.commande = args.commande[1:]
    return args.func(args)


def _point_entree() -> int:
    """Sortir proprement quand la sortie est coupée (« sentinelle show | head »)
    ou quand l'utilisateur fait Ctrl-C, plutôt que de cracher une trace."""
    try:
        return main()
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except Exception:
            pass
        return 0
    except KeyboardInterrupt:
        print("\nInterrompu.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(_point_entree())
