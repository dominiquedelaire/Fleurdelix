#!/usr/bin/env python3
"""Unibox — un jeu de caisses à pousser, dans une fenêtre pywebview.

(C) 2026 Fleurdelix Licence MIT, Dominique Delaire

Lancement :
    python main.py            fenêtre native (nécessite pywebview)
    python main.py --browser  ouvre le jeu dans le navigateur par défaut
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
SAVE = Path.home() / ".unibox" / "progress.json"

REQUIRED = ("index.html", "css/style.css",
            "js/levels.js", "js/engine.js", "js/render.js", "js/app.js")

WINDOW_TITLE = "Unibox"
WINDOW_SIZE = (1180, 780)
MIN_SIZE = (760, 560)


def web_root() -> Path | None:
    """Le dossier qui contient index.html : web/ normalement, mais on tolère
    que le jeu ait été posé directement à côté de main.py."""
    for candidate in (WEB, ROOT):
        if (candidate / "index.html").is_file():
            return candidate
    return None


def check_files() -> Path | None:
    """Renvoie le dossier web, ou explique précisément ce qui manque."""
    root = web_root()
    if root is None:
        print(
            f"Je ne trouve pas index.html.\n"
            f"Cherché dans : {WEB}\n"
            f"        et    : {ROOT}\n\n"
            "Le jeu attend cette arborescence, main.py et web/ côte à côte :\n"
            "    unibox/\n"
            "      main.py\n"
            "      web/index.html\n"
            "      web/css/style.css\n"
            "      web/js/levels.js  engine.js  render.js  app.js\n\n"
            "Si les fichiers ont été téléchargés un par un, ils sont sans doute\n"
            "tous à plat dans le même dossier : recréez web/, web/css et web/js,\n"
            "ou repartez de l'archive unibox.zip.",
            file=sys.stderr,
        )
        return None

    missing = [name for name in REQUIRED if not (root / name).is_file()]
    if missing:
        print(
            f"Dossier trouvé : {root}\n"
            "Mais il manque :\n  " + "\n  ".join(missing) + "\n\n"
            "Le jeu ne peut pas tourner sans ces fichiers.",
            file=sys.stderr,
        )
        return None
    return root


class Api:
    """Pont exposé au JavaScript sous window.pywebview.api."""

    def load_progress(self) -> str:
        try:
            return SAVE.read_text(encoding="utf-8")
        except (OSError, ValueError):
            return ""

    def save_progress(self, raw: str) -> bool:
        try:
            json.loads(raw)  # on refuse d'écrire autre chose que du JSON
            SAVE.parent.mkdir(parents=True, exist_ok=True)
            SAVE.write_text(raw, encoding="utf-8")
            return True
        except (OSError, ValueError):
            return False

    def reset_progress(self) -> bool:
        try:
            SAVE.unlink(missing_ok=True)
            return True
        except OSError:
            return False


def run_window() -> int:
    try:
        import webview
    except ImportError:
        print(
            "pywebview n'est pas disponible, donc pas de fenêtre native.\n\n"
            "Le jeu tourne tout de suite, sans rien installer :\n"
            "    python3 main.py --browser\n\n"
            "Pour la fenêtre native, passez par un environnement virtuel — sur\n"
            "Debian et Ubuntu, pip refuse d'écrire dans le Python système\n"
            "(error: externally-managed-environment) :\n"
            "    python3 -m venv .venv\n"
            "    source .venv/bin/activate\n"
            "    pip install pywebview 'pywebview[qt]'\n"
            "    python main.py\n\n"
            "Détails et cas particuliers dans le README.",
            file=sys.stderr,
        )
        return 1

    root = check_files()
    if root is None:
        return 1

    webview.create_window(
        WINDOW_TITLE,
        str(root / "index.html"),
        js_api=Api(),
        width=WINDOW_SIZE[0],
        height=WINDOW_SIZE[1],
        min_size=MIN_SIZE,
        background_color="#171320",
        text_select=False,
    )
    webview.start()
    return 0


def run_browser(port: int = 0) -> int:
    import webbrowser

    root = check_files()
    if root is None:
        return 1

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(root), **kw)

        def log_message(self, *a):  # serveur silencieux
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{server.server_port}/index.html"
    print(f"Unibox tourne sur {url} — Ctrl+C pour arrêter.")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nÀ bientôt sur les quais.")
    finally:
        server.server_close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Unibox")
    parser.add_argument("--browser", action="store_true",
                        help="ouvrir dans le navigateur au lieu d'une fenêtre native")
    parser.add_argument("--port", type=int, default=0,
                        help="port du serveur local en mode --browser")
    args = parser.parse_args()
    return run_browser(args.port) if args.browser else run_window()


if __name__ == "__main__":
    raise SystemExit(main())
