"""
FlightBoard — backend (données de vol, réglages, localisation).

(C) 2026 Dominique Delaire, Fleurdelix OS, Open source licence MIT

Sources de données (gratuites, sans clé) :
  - Positions des avions : airplanes.live  (repli : adsb.lol)
  - Route / compagnie / type d'appareil : adsbdb.com
  - Localisation approximative par IP : ip-api.com
"""
from __future__ import annotations

import json
import math
import os
import platform
import sys
import threading
import time
from pathlib import Path

import requests

APP_NAME = "FlightBoard"
USER_AGENT = "FlightBoard/1.0 (personal hobby project)"

# ---------------------------------------------------------------------------
# Réglages
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS = {
    "lat": 45.5017,          # Montréal par défaut
    "lon": -73.5673,
    "location_name": "Montréal",
    "radius_km": 40,
    "refresh_seconds": 15,   # intervalle de rafraîchissement des données
    "cycle_seconds": 6,      # durée d'affichage de chaque vol
    "units": "metric",       # metric | imperial
    "led_pitch": 8,          # taille d'une LED à l'écran (px)
    "led_shape": "round",    # round | square
    "display_mode": "board", # board (texte) | radar
    "radar_color": "#3cff5a",
    "render_style": "led",   # led | smooth (lisse)
    "bg_color": "#050505",   # fond du panneau
    "off_color": "#141414",  # LED éteintes
    "glow": 0.2,             # intensité du halo (0 à 1)
    "mono": False,           # une seule couleur pour tout le texte
    "mono_color": "#ffb000", # couleur unique (ambre classique)
    "fields": {              # ce que l'on affiche (ordre = ordre des lignes)
        "airline": True,
        "callsign": True,
        "route": True,
        "aircraft": True,
        "altitude": True,
        "speed": True,
        "distance": True,
        "origin_name": False,
        "destination_name": False,
        "registration": False,
        "heading": False,
        "vertical_rate": False,
        "counter": True,
    },
    "colors": {
        "airline": "#ff8a3d",
        "callsign": "#ffffff",
        "route": "#4aa8ff",
        "aircraft": "#ffffff",
        "altitude": "#5df07c",
        "speed": "#5df07c",
        "distance": "#5df07c",
        "origin_name": "#c9c9c9",
        "destination_name": "#c9c9c9",
        "registration": "#c9c9c9",
        "heading": "#5df07c",
        "vertical_rate": "#5df07c",
        "counter": "#7a7a7a",
    },
}


def config_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    elif system == "Darwin":
        base = Path.home() / "Library/Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    d = base / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


SETTINGS_FILE = config_dir() / "settings.json"


def _deep_merge(base: dict, extra: dict) -> dict:
    out = dict(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_settings() -> dict:
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return _deep_merge(DEFAULT_SETTINGS, data)
    except Exception:
        return json.loads(json.dumps(DEFAULT_SETTINGS))


def save_settings(data: dict) -> dict:
    merged = _deep_merge(load_settings(), data)
    SETTINGS_FILE.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    return merged


# ---------------------------------------------------------------------------
# Géographie
# ---------------------------------------------------------------------------

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def bearing_deg(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def compass(deg: float) -> str:
    pts = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
    return pts[int((deg + 22.5) // 45) % 8]


def locate_by_ip() -> dict:
    """Localisation approximative (ville) d'après l'adresse IP publique."""
    r = requests.get("http://ip-api.com/json/?fields=status,city,regionName,country,lat,lon",
                     timeout=8, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    d = r.json()
    if d.get("status") != "success":
        raise RuntimeError("Localisation par IP impossible")
    return {
        "lat": d["lat"], "lon": d["lon"],
        "location_name": ", ".join(x for x in [d.get("city"), d.get("country")] if x),
    }


# ---------------------------------------------------------------------------
# Données de vol
# ---------------------------------------------------------------------------

POSITION_SOURCES = [
    "https://api.airplanes.live/v2/point/{lat}/{lon}/{nm}",
    "https://api.adsb.lol/v2/point/{lat}/{lon}/{nm}",
]
ROUTE_URL = "https://api.adsbdb.com/v0/callsign/{callsign}"
AIRCRAFT_URL = "https://api.adsbdb.com/v0/aircraft/{hex}"


class FlightData:
    """Récupère les avions autour d'un point et enrichit chaque vol (route, compagnie, type)."""

    def __init__(self):
        self._route_cache: dict[str, dict | None] = {}
        self._aircraft_cache: dict[str, dict | None] = {}
        self._lock = threading.Lock()
        self._session = requests.Session()
        self._session.headers["User-Agent"] = USER_AGENT

    # -- sources -----------------------------------------------------------
    def _fetch_positions(self, lat: float, lon: float, radius_km: float) -> list[dict]:
        nm = max(1, min(250, round(radius_km / 1.852)))
        last_err = None
        for tpl in POSITION_SOURCES:
            try:
                r = self._session.get(tpl.format(lat=lat, lon=lon, nm=nm), timeout=8)
                r.raise_for_status()
                return r.json().get("ac", []) or []
            except Exception as e:  # on essaie la source suivante
                last_err = e
        raise RuntimeError(f"Aucune source de positions disponible ({last_err})")

    def _route(self, callsign: str) -> dict | None:
        if not callsign:
            return None
        with self._lock:
            if callsign in self._route_cache:
                return self._route_cache[callsign]
        info = None
        try:
            r = self._session.get(ROUTE_URL.format(callsign=callsign), timeout=6)
            if r.ok:
                fr = (r.json().get("response") or {}).get("flightroute") or {}
                if fr:
                    info = {
                        "airline": (fr.get("airline") or {}).get("name"),
                        "airline_iata": (fr.get("airline") or {}).get("iata"),
                        "origin_iata": (fr.get("origin") or {}).get("iata_code"),
                        "origin_icao": (fr.get("origin") or {}).get("icao_code"),
                        "origin_name": (fr.get("origin") or {}).get("name"),
                        "origin_city": (fr.get("origin") or {}).get("municipality"),
                        "dest_iata": (fr.get("destination") or {}).get("iata_code"),
                        "dest_icao": (fr.get("destination") or {}).get("icao_code"),
                        "dest_name": (fr.get("destination") or {}).get("name"),
                        "dest_city": (fr.get("destination") or {}).get("municipality"),
                    }
        except Exception:
            info = None
        with self._lock:
            self._route_cache[callsign] = info
        return info

    def _aircraft(self, hexcode: str) -> dict | None:
        if not hexcode:
            return None
        with self._lock:
            if hexcode in self._aircraft_cache:
                return self._aircraft_cache[hexcode]
        info = None
        try:
            r = self._session.get(AIRCRAFT_URL.format(hex=hexcode), timeout=6)
            if r.ok:
                ac = (r.json().get("response") or {}).get("aircraft") or {}
                if ac:
                    info = {
                        "type": ac.get("type"),
                        "manufacturer": ac.get("manufacturer"),
                        "icao_type": ac.get("icao_type"),
                        "registration": ac.get("registration"),
                        "owner": ac.get("registered_owner"),
                    }
        except Exception:
            info = None
        with self._lock:
            self._aircraft_cache[hexcode] = info
        return info

    # -- API publique -------------------------------------------------------
    def nearby(self, lat: float, lon: float, radius_km: float, max_flights: int = 12) -> list[dict]:
        raw = self._fetch_positions(lat, lon, radius_km)
        flights = []
        for ac in raw:
            if ac.get("lat") is None or ac.get("lon") is None:
                continue
            dist = haversine_km(lat, lon, ac["lat"], ac["lon"])
            if dist > radius_km:
                continue
            alt = ac.get("alt_baro")
            if alt == "ground":
                alt = 0
            flights.append({
                "hex": ac.get("hex"),
                "callsign": (ac.get("flight") or "").strip() or None,
                "registration": ac.get("r"),
                "type_code": ac.get("t"),
                "type_desc": ac.get("desc"),
                "lat": ac["lat"], "lon": ac["lon"],
                "altitude_ft": alt if isinstance(alt, (int, float)) else None,
                "speed_kt": ac.get("gs"),
                "track": ac.get("track"),
                "vertical_rate_fpm": ac.get("baro_rate", ac.get("geom_rate")),
                "distance_km": round(dist, 1),
                "bearing": round(bearing_deg(lat, lon, ac["lat"], ac["lon"])),
            })
        flights.sort(key=lambda f: f["distance_km"])
        flights = flights[:max_flights]

        # Enrichissement (route + type), en parallèle pour ne pas bloquer
        threads = []
        def enrich(f):
            route = self._route(f["callsign"]) if f["callsign"] else None
            acinfo = self._aircraft(f["hex"])
            f["route"] = route
            f["aircraft"] = acinfo
        for f in flights:
            t = threading.Thread(target=enrich, args=(f,), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join(timeout=10)

        for f in flights:
            f["bearing_compass"] = compass(f["bearing"])
            if f.get("aircraft") and f["aircraft"].get("registration") and not f["registration"]:
                f["registration"] = f["aircraft"]["registration"]
        return flights


# ---------------------------------------------------------------------------
# API exposée à l'interface (utilisée par pywebview ET par le mode navigateur)
# ---------------------------------------------------------------------------

class Api:
    def __init__(self):
        self.data = FlightData()

    def get_settings(self) -> dict:
        return load_settings()

    def save_settings(self, data: dict) -> dict:
        return save_settings(data)

    def reset_settings(self) -> dict:
        if SETTINGS_FILE.exists():
            SETTINGS_FILE.unlink()
        return load_settings()

    def locate(self) -> dict:
        try:
            loc = locate_by_ip()
            save_settings(loc)
            return {"ok": True, **loc}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_flights(self) -> dict:
        s = load_settings()
        try:
            flights = self.data.nearby(float(s["lat"]), float(s["lon"]), float(s["radius_km"]))
            return {"ok": True, "flights": flights, "time": time.time()}
        except Exception as e:
            return {"ok": False, "error": str(e), "flights": []}

    def system_info(self) -> dict:
        return {"platform": platform.system(), "python": sys.version.split()[0],
                "settings_file": str(SETTINGS_FILE)}
