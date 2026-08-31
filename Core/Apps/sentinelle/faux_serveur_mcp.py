#!/usr/bin/env python3
"""Faux serveur MCP minimal, uniquement pour tester le proxy hors ligne.

Il parle le même dialecte que les vrais : du JSON-RPC ligne par ligne sur
stdin/stdout. Il sait lire un fichier, en écrire un, et râler si l'outil
est inconnu.
"""

import json
import sys
from pathlib import Path


def repondre(rpc_id, resultat=None, erreur=None):
    msg = {"jsonrpc": "2.0", "id": rpc_id}
    if erreur:
        msg["error"] = erreur
    else:
        msg["result"] = resultat
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def texte(contenu):
    return {"content": [{"type": "text", "text": contenu}]}


for ligne in sys.stdin:
    ligne = ligne.strip()
    if not ligne:
        continue
    try:
        msg = json.loads(ligne)
    except json.JSONDecodeError:
        continue

    methode = msg.get("method")
    rpc_id = msg.get("id")

    if methode == "initialize":
        repondre(rpc_id, {"protocolVersion": "2024-11-05",
                          "serverInfo": {"name": "faux", "version": "0"}})
    elif methode == "tools/list":
        repondre(rpc_id, {"tools": [
            {"name": "read_text_file"}, {"name": "write_file"},
            {"name": "delete_file"}, {"name": "fetch"},
        ]})
    elif methode == "tools/call":
        params = msg.get("params", {})
        outil = params.get("name")
        args = params.get("arguments", {})
        if outil == "read_text_file":
            p = Path(args.get("path", ""))
            repondre(rpc_id, texte(p.read_text() if p.exists() else "(fichier absent)"))
        elif outil == "write_file":
            repondre(rpc_id, texte(f"écrit dans {args.get('path')}"))
        elif outil == "delete_file":
            repondre(rpc_id, texte("supprimé"))
        elif outil == "fetch":
            repondre(rpc_id, texte("200 OK"))
        else:
            repondre(rpc_id, erreur={"code": -32601, "message": f"outil inconnu : {outil}"})
    elif methode == "notifications/initialized":
        pass
    else:
        repondre(rpc_id, erreur={"code": -32601, "message": "méthode inconnue"})
