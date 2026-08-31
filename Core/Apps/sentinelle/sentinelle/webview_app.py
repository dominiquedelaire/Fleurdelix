"""La fenêtre.

`webview_app` ne contient aucune logique métier : la classe Api est un pont qui
délègue à db / journal / regles. Le même pont sert au repli navigateur, donc
l'interface est identique dans les deux modes.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from . import controle as ctrl
from . import db as dbmod
from . import journal as jmod
from . import regles as rmod

UI = Path(__file__).parent / "ui"


def _regles_par_defaut() -> Path:
    for c in (Path.cwd() / "regles.yaml", Path.home() / ".sentinelle" / "regles.yaml"):
        if c.exists():
            return c
    return Path.cwd() / "regles.yaml"


class Api:
    def __init__(self, chemin_db=None):
        self.chemin_db = chemin_db
        self.chemin_regles = _regles_par_defaut()

    def _con(self) -> sqlite3.Connection:
        return dbmod.connexion(self.chemin_db)

    # ------------------------------------------------------------------ état

    def etat(self) -> dict:
        con = self._con()
        ok, seq, message = jmod.verifier(con)
        n_runs = con.execute("SELECT COUNT(*) c FROM runs").fetchone()["c"]
        n_evts = con.execute("SELECT COUNT(*) c FROM evenements").fetchone()["c"]
        n_viol = con.execute("SELECT COUNT(*) c FROM violations").fetchone()["c"]
        n_sec = con.execute("SELECT COUNT(*) c FROM secrets").fetchone()["c"]
        n_eff = con.execute(
            "SELECT COUNT(*) c FROM blobs WHERE efface=1").fetchone()["c"]
        ok_b, _intacts, _effaces, alteres = jmod.verifier_blobs(con)
        coupe, motif_arret = ctrl.arret_actif(con)
        n_dem = con.execute(
            "SELECT COUNT(*) c FROM demandes WHERE etat='attente'").fetchone()["c"]
        return {
            "db": str(dbmod.chemin_defaut() if not self.chemin_db else self.chemin_db),
            "chaine_ok": ok,
            "chaine_seq": seq,
            "chaine_message": message,
            "nb_runs": n_runs,
            "nb_evts": n_evts,
            "nb_violations": n_viol,
            "nb_secrets": n_sec,
            "nb_effaces": n_eff,
            "contenus_ok": ok_b,
            "contenus_alteres": len(alteres),
            "arret_actif": coupe,
            "arret_motif": motif_arret,
            "nb_demandes": n_dem,
            "regles": str(self.chemin_regles),
        }

    # ------------------------------------------------------------- contrôle

    def demandes(self) -> list[dict]:
        return ctrl.en_attente(self._con())

    def trancher(self, demande_id: int, etat: str, motif: str = "") -> dict:
        """Accorder ou refuser. L'agent, qui attend, reçoit dans la seconde."""
        if etat not in ("accorde", "refuse"):
            return {"erreur": "décision inconnue"}
        ok = ctrl.decider(self._con(), int(demande_id), etat, motif=motif)
        return {"ok": ok} if ok else {
            "erreur": "cette demande n'est plus en attente"}

    def basculer_arret(self, actif: bool, motif: str = "") -> dict:
        ctrl.basculer_arret(self._con(), bool(actif),
                            motif or ("frein tiré depuis la fenêtre" if actif else ""))
        return {"actif": bool(actif)}

    def budgets(self, run_id: str | None = None) -> list[dict]:
        """Les compteurs, recalculés depuis le journal à chaque appel."""
        from . import budgets as bud
        jeu = rmod.charger(self.chemin_regles) if Path(self.chemin_regles).exists() \
            else rmod.Jeu()
        liste, tarifs = jeu.budgets_tarifs()
        con = self._con()
        if not run_id:
            row = con.execute(
                "SELECT id FROM runs ORDER BY debut DESC LIMIT 1").fetchone()
            run_id = row["id"] if row else None
        return bud.tous(con, liste, tarifs, run_id)

    def secrets(self) -> list[dict]:
        """Le catalogue. Aucune valeur en clair n'y figure : ces empreintes
        sont des HMAC, elles ne se retournent pas sans la clé locale."""
        con = self._con()
        return [dict(r) for r in con.execute(
            """SELECT s.*,
                      (SELECT COUNT(DISTINCT run_id) FROM secrets_vus v
                       WHERE v.empreinte = s.empreinte) sessions
               FROM secrets s
               ORDER BY s.occurrences DESC, s.genre""")]

    def circulation(self, empreinte: str) -> list[dict]:
        """Par où cette valeur est passée, sans jamais la lire."""
        con = self._con()
        return [dict(r) for r in con.execute(
            """SELECT e.seq, e.ts, e.resume, e.outil, e.run_id, r.agent
               FROM secrets_vus v
               JOIN evenements e ON e.seq = v.evt_seq
               JOIN runs r ON r.id = e.run_id
               WHERE v.empreinte = ? ORDER BY e.seq""", (empreinte,))]

    def runs(self) -> list[dict]:
        con = self._con()
        lignes = con.execute(
            """SELECT r.*,
                      (SELECT COUNT(*) FROM violations v WHERE v.run_id=r.id) viol,
                      (SELECT MAX(CASE severite
                            WHEN 'critique' THEN 4 WHEN 'haute' THEN 3
                            WHEN 'moyenne' THEN 2 ELSE 1 END)
                       FROM violations v WHERE v.run_id=r.id) pire
               FROM runs r ORDER BY r.debut DESC"""
        ).fetchall()
        return [dict(r) for r in lignes]

    def run(self, run_id: str) -> dict:
        con = self._con()
        run = con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not run:
            return {"erreur": f"session {run_id} introuvable"}
        evts = [dict(e) for e in con.execute(
            "SELECT * FROM evenements WHERE run_id=? ORDER BY seq", (run_id,))]
        viols: dict[str, list] = {}
        for v in con.execute("SELECT * FROM violations WHERE run_id=?", (run_id,)):
            viols.setdefault(str(v["evt_seq"]), []).append(dict(v))
        for e in evts:
            e["args"] = json.loads(e["args_json"] or "{}")
            e["marques"] = json.loads(e["marques"] or "[]")
        return {"run": dict(run), "evenements": evts, "violations": viols}

    def contenu(self, blob_hash: str) -> dict:
        con = self._con()
        row = con.execute(
            "SELECT contenu, taille, efface, motif FROM blobs WHERE hash=?",
            (blob_hash,),
        ).fetchone()
        if not row:
            return {"contenu": "", "taille": 0}
        if row["efface"]:
            return {"contenu": "", "taille": row["taille"], "efface": True,
                    "motif": row["motif"] or "effacé"}
        return {"contenu": (row["contenu"] or "")[:20000], "taille": row["taille"]}

    def genealogie(self, seq: int) -> dict:
        """Remonte la chaîne : d'où vient cette action ?"""
        con = self._con()
        evt = con.execute("SELECT * FROM evenements WHERE seq=?", (seq,)).fetchone()
        if not evt:
            return {"erreur": "événement introuvable"}
        viols = [dict(v) for v in con.execute(
            "SELECT * FROM violations WHERE evt_seq=?", (seq,))]

        chaine = []
        for v in viols:
            if v["origine_seq"]:
                o = con.execute(
                    "SELECT * FROM evenements WHERE seq=?", (v["origine_seq"],)
                ).fetchone()
                if o:
                    chaine.append({"role": "origine", "regle": v["regle"], **dict(o)})

        avant = [dict(e) for e in con.execute(
            """SELECT * FROM evenements
               WHERE run_id=? AND seq<? AND type='appel'
               ORDER BY seq DESC LIMIT 4""",
            (evt["run_id"], seq))]
        for a in reversed(avant):
            if not any(c["seq"] == a["seq"] for c in chaine):
                chaine.append({"role": "avant", **a})
        chaine.sort(key=lambda x: x["seq"])
        return {"evenement": dict(evt), "violations": viols, "chaine": chaine}

    # ---------------------------------------------------------------- règles

    def lire_regles(self) -> dict:
        p = Path(self.chemin_regles)
        return {"chemin": str(p),
                "texte": p.read_text(encoding="utf-8") if p.exists() else ""}

    def tester_regles(self, texte: str) -> dict:
        try:
            jeu = rmod.charger_texte(texte)
        except Exception as exc:
            return {"erreur": f"YAML illisible : {exc}"}
        erreurs = jeu.valider()
        if erreurs:
            return {"erreur": " · ".join(erreurs)}
        return rmod.rejouer(self._con(), jeu, ecrire=False)

    def enregistrer_regles(self, texte: str) -> dict:
        try:
            jeu = rmod.charger_texte(texte)
        except Exception as exc:
            return {"erreur": f"YAML illisible : {exc}"}
        erreurs = jeu.valider()
        if erreurs:
            return {"erreur": " · ".join(erreurs)}
        Path(self.chemin_regles).write_text(texte, encoding="utf-8")
        res = rmod.rejouer(self._con(), jeu, ecrire=True)
        return {"ok": True, "total": res["total"], "chemin": str(self.chemin_regles)}


# ---------------------------------------------------------------- lancement


AIDE_GTK = """
Aucun moteur de rendu pour pywebview.

Sous Ubuntu / Debian :
    sudo apt install python3-gi gir1.2-webkit2-4.1 libcairo2-dev
Sous Windows : installer WebView2 (souvent déjà présent).
Sous macOS : rien à installer.

En attendant, « sentinelle ui --navigateur » affiche exactement la même
interface dans ton navigateur.
"""


def lancer(chemin_db=None, navigateur: bool = False, port: int = 8731) -> int:
    api = Api(chemin_db)
    if navigateur:
        return _servir(api, port)
    try:
        import webview
    except ModuleNotFoundError:
        print("pywebview n'est pas installé : pip install pywebview")
        print("Ou lance « sentinelle ui --navigateur ».")
        return 1

    webview.create_window(
        "Sentinelle",
        str(UI / "index.html"),
        js_api=api,
        width=1280,
        height=820,
        min_size=(900, 600),
        background_color="#0E1216",
    )
    try:
        webview.start()
    except Exception as exc:
        print(f"{exc}\n{AIDE_GTK}")
        return 1
    return 0


def _servir(api: Api, port: int) -> int:
    """Repli : même interface, servie en local, appels via fetch."""
    import http.server
    import socketserver

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(UI), **kw)

        def log_message(self, *a):
            pass

        def do_POST(self):
            if not self.path.startswith("/api/"):
                self.send_error(404)
                return
            nom = self.path[5:]
            methode = getattr(api, nom, None)
            if not methode or nom.startswith("_"):
                self.send_error(404)
                return
            taille = int(self.headers.get("Content-Length", 0))
            args = json.loads(self.rfile.read(taille) or "[]")
            try:
                res = methode(*args)
            except Exception as exc:
                res = {"erreur": str(exc)}
            corps = json.dumps(res, ensure_ascii=False, default=str).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), Handler) as srv:
        print(f"Sentinelle sur http://127.0.0.1:{port}  (Ctrl-C pour arrêter)")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\nArrêté.")
    return 0
