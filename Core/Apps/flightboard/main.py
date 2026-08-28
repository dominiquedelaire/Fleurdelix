"""
FlightBoard — tableau LED des avions qui passent au-dessus de vous.

(C) 2026 Dominique Delaire, Fleurdelix OS - Open source licence MIT

Lancement :
    python main.py              -> fenêtre native (pywebview)
    python main.py --browser    -> serveur local + navigateur (sans pywebview)
    python main.py --fullscreen -> plein écran (mode « cadre » / kiosque)
    python main.py --host 0.0.0.0 -> serveur accessible depuis un iPad / téléphone du réseau local
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from backend import Api

# Avec PyInstaller, les fichiers embarqués sont extraits dans sys._MEIPASS
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
UI_DIR = ROOT / "ui"
INDEX = UI_DIR / "index.html"


# ---------------------------------------------------------------------------
# Mode navigateur : petit serveur HTTP local qui expose la même Api en JSON
# ---------------------------------------------------------------------------

def run_browser_mode(api: Api, port: int, open_browser: bool = True, host: str = "127.0.0.1"):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # silence
            pass

        def _json(self, obj, status=200):
            body = json.dumps(obj).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                body = INDEX.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path.endswith(".js") and (UI_DIR / self.path.lstrip("/")).is_file():
                body = (UI_DIR / self.path.lstrip("/")).read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/javascript; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path.startswith("/api/"):
                name = self.path[5:].split("?")[0]
                fn = getattr(api, name, None)
                if not fn or name.startswith("_"):
                    return self._json({"error": "unknown"}, 404)
                self._json(fn())
            else:
                self.send_error(404)

        def do_POST(self):
            if not self.path.startswith("/api/"):
                return self.send_error(404)
            name = self.path[5:]
            fn = getattr(api, name, None)
            if not fn or name.startswith("_"):
                return self._json({"error": "unknown"}, 404)
            n = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(n) or b"null")
            self._json(fn(payload) if payload is not None else fn())

    srv = ThreadingHTTPServer((host, port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"FlightBoard : {url}")
    if host == "0.0.0.0":
        import socket
        try:
            s_ = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s_.connect(("8.8.8.8", 80))
            print(f"Depuis un autre appareil du réseau (iPad, etc.) : http://{s_.getsockname()[0]}:{port}/")
            s_.close()
        except OSError:
            pass
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


# ---------------------------------------------------------------------------
# Mode fenêtre native (pywebview)
# ---------------------------------------------------------------------------

def run_webview_mode(api: Api, fullscreen: bool):
    import webview  # pywebview
    window = webview.create_window(
        "FlightBoard",
        str(INDEX),
        js_api=api,
        width=1100, height=420,
        min_size=(520, 220),
        background_color="#050505",
        fullscreen=fullscreen,
    )
    webview.start(debug="--debug" in sys.argv)


def main():
    p = argparse.ArgumentParser(description="FlightBoard — afficheur LED des vols au-dessus de vous")
    p.add_argument("--browser", action="store_true", help="utiliser le navigateur au lieu d'une fenêtre native")
    p.add_argument("--fullscreen", action="store_true", help="démarrer en plein écran")
    p.add_argument("--port", type=int, default=8765, help="port du mode navigateur")
    p.add_argument("--host", default="127.0.0.1", help="adresse d'écoute du mode navigateur (0.0.0.0 = accessible sur le réseau local)")
    p.add_argument("--debug", action="store_true", help="outils de développement pywebview")
    args = p.parse_args()

    api = Api()
    if args.browser or args.host != "127.0.0.1":
        return run_browser_mode(api, args.port, host=args.host)
    try:
        import webview  # noqa: F401
    except ImportError:
        print("pywebview n'est pas installé (pip install pywebview) — bascule en mode navigateur.")
        return run_browser_mode(api, args.port)
    run_webview_mode(api, args.fullscreen)


if __name__ == "__main__":
    main()
