"""
Petites fonctions utilitaires partagees : parsing de dates souples,
extraction de hashtags dans un texte, parsing de metriques.
Isolees ici pour rester testables et reutilisables par la future IA.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

_TAG_RE = re.compile(r"#(\w+)")


def parse_date(value: str | None) -> str | None:
    """
    Accepte des formes pratiques et renvoie une date ISO (YYYY-MM-DD).

    Exemples acceptes :
      "today", "tomorrow", "yesterday",
      "+3" / "+3d" (dans 3 jours), "-2" (il y a 2 jours),
      "2026-06-10", "10/06/2026".
    """
    if not value:
        return None
    value = value.strip().lower()
    today = datetime.now().date()

    keywords = {
        "today": 0, "aujourdhui": 0, "auj": 0,
        "tomorrow": 1, "demain": 1,
        "yesterday": -1, "hier": -1,
    }
    if value in keywords:
        return (today + timedelta(days=keywords[value])).isoformat()

    m = re.fullmatch(r"([+-]\d+)d?", value)
    if m:
        return (today + timedelta(days=int(m.group(1)))).isoformat()

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m", "%Y/%m/%d"):
        try:
            d = datetime.strptime(value, fmt).date()
            if fmt == "%d/%m":  # annee implicite = annee courante
                d = d.replace(year=today.year)
            return d.isoformat()
        except ValueError:
            continue

    # En dernier recours, on renvoie tel quel : on prefere ne rien perdre.
    return value


def extract_hashtags(text: str | None) -> list[str]:
    """Recupere les #tags presents dans un texte libre."""
    if not text:
        return []
    return [m.lower() for m in _TAG_RE.findall(text)]


def parse_tags(raw: str | None) -> list[str]:
    """Transforme 'sport,sante #moral' en ['sport', 'sante', 'moral']."""
    if not raw:
        return []
    parts = re.split(r"[,\s]+", raw.strip())
    return [p.lstrip("#").lower() for p in parts if p.strip()]


def parse_metrics(pairs: list[str] | None) -> dict[str, float | tuple]:
    """
    Transforme une liste 'poids=78.5' 'humeur=7' 'sommeil=6.5:h'
    en dict {'poids': 78.5, 'humeur': 7.0, 'sommeil': (6.5, 'h')}.
    """
    result: dict[str, float | tuple] = {}
    if not pairs:
        return result
    for pair in pairs:
        if "=" not in pair:
            continue
        name, raw_val = pair.split("=", 1)
        unit = None
        if ":" in raw_val:
            raw_val, unit = raw_val.split(":", 1)
        try:
            value = float(raw_val.replace(",", "."))
        except ValueError:
            continue
        result[name.strip().lower()] = (value, unit) if unit else value
    return result
