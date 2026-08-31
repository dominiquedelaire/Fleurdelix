"""Caviardage avant écriture.

Une boîte noire qui enregistre tout devient le meilleur endroit où chercher des
secrets. Ce module s'interpose avant le scellement : ce qui entre dans le
journal est déjà caviardé, donc le hash porte sur la version caviardée et il
n'existe nulle part de version en clair.

Ce qui reste à la place : un marqueur qui dit le genre et porte une empreinte.

    STRIPE_KEY=sk_live_51H8x...     →     STRIPE_KEY=⟦stripe·a3f19c⟧

L'empreinte est un HMAC-SHA256 avec une clé locale (~/.sentinelle/cle_empreinte),
jamais le secret lui-même. Deux conséquences utiles :

  · le même secret donne le même marqueur partout, donc on suit sa circulation
    d'un bout à l'autre d'une session sans jamais le lire ;
  · on peut prouver après coup qu'une valeur donnée est bien celle qui est
    passée, en recalculant son empreinte. Sans la clé, l'empreinte ne se
    retourne pas, même pour un secret court.

La clé ne doit pas voyager avec un journal exporté.
"""

from __future__ import annotations

import hashlib
import hmac
import math
import os
import re
import secrets as _secrets
from dataclasses import dataclass
from pathlib import Path

# ────────────────────────────────────────────────────────────── motifs nommés
# (genre, expression, indice_du_groupe, prefixe_public)
# Le préfixe est une information publique du format, jamais un morceau du
# secret : « sk_live_ » ne dit rien de la clé qui suit.

MOTIFS: list[tuple[str, re.Pattern, int, str]] = [
    ("cle-privee", re.compile(
        r"-----BEGIN[A-Z ]*PRIVATE KEY-----.*?-----END[A-Z ]*PRIVATE KEY-----",
        re.S), 0, "PEM"),
    ("anthropic", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}"), 0, "sk-ant-"),
    ("openai", re.compile(r"\bsk-(?!ant-)[A-Za-z0-9_\-]{20,}"), 0, "sk-"),
    ("stripe", re.compile(r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{10,}"), 0, "sk_live_"),
    ("aws", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), 0, "AKIA"),
    ("github", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), 0, "ghp_"),
    ("google", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"), 0, "AIza"),
    ("slack", re.compile(r"\bxox[baprse]-[A-Za-z0-9\-]{10,}"), 0, "xox"),
    ("jeton-jwt", re.compile(
        r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{4,}"), 0, "eyJ"),
    ("mot-de-passe-url", re.compile(
        r"\b[a-z][a-z0-9+.\-]*://[^:/\s]+:([^@/\s]{3,})@"), 1, ""),
    ("en-tete-auth", re.compile(
        r"(?i)\b(?:authorization|x-api-key)\s*[:=]\s*[\"']?(?:bearer\s+)?"
        r"([A-Za-z0-9._\-+/=]{12,})"), 1, ""),
    # Le nom de la variable trahit la valeur, même si la valeur est faible :
    # DB_PASSWORD=hunter2 n'a aucune entropie mais reste un mot de passe.
    ("affectation", re.compile(
        r"(?im)^\s*[A-Z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD|PASSWD|PWD|CREDENTIAL"
        r"|APIKEY|ACCESS)[A-Z0-9_]*\s*[:=]\s*[\"']?([^\s\"'#]{3,})"), 1, ""),
    ("affectation-json", re.compile(
        r"(?i)\"(?:[a-z_]*(?:key|secret|token|password|pwd|credential)[a-z_]*)\""
        r"\s*:\s*\"([^\"]{3,})\""), 1, ""),
]

# Données personnelles : autre régime, autre bouton. On ne mélange pas
# « l'agent a manipulé une clé d'API » et « l'agent a vu un courriel client ».
MOTIFS_PERSONNELS: list[tuple[str, re.Pattern, int, str]] = [
    ("courriel", re.compile(r"\b[\w.+\-]+@[\w\-]+\.[\w.\-]{2,}\b"), 0, ""),
    ("carte", re.compile(r"\b(?:\d[ \-]?){13,19}\b"), 0, ""),
    ("nas", re.compile(r"\b\d{3}[ \-]?\d{3}[ \-]?\d{3}\b"), 0, ""),
    ("telephone", re.compile(
        r"\b(?:\+1[ \-.]?)?\(?\d{3}\)?[ \-.]\d{3}[ \-.]\d{4}\b"), 0, ""),
]

# Jetons opaques que personne n'a nommés : on se rabat sur l'entropie.
CANDIDAT_JETON = re.compile(r"[A-Za-z0-9+/_\-]{24,}={0,2}")
SEUIL_ENTROPIE = 3.6      # bits par caractère
HEXA_PUR = re.compile(r"^[0-9a-fA-F]+$")


def entropie(s: str) -> float:
    if not s:
        return 0.0
    freq: dict[str, int] = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    n = len(s)
    return -sum((k / n) * math.log2(k / n) for k in freq.values())


def _ressemble_a_un_jeton(jeton: str) -> bool:
    """Écarte ce qui a l'entropie d'un secret sans en être un.

    Un chemin comme /home/fleurdelix/projets/facturier/taxes passe largement le
    seuil d'entropie. Or caviarder les chemins rendrait le journal illisible,
    et un chemin n'est pas un secret. Trois garde-fous :
      · pas de barre oblique (c'est un chemin, pas un jeton) ;
      · pas d'hexadécimal pur (c'est un hash, un sha git, un UUID) ;
      · au moins deux classes de caractères parmi majuscules, minuscules,
        chiffres, ce qu'un mot ou un chemin n'a presque jamais.
    """
    if "/" in jeton:
        return False
    if HEXA_PUR.match(jeton):
        return False
    classes = sum((
        any(c.isupper() for c in jeton),
        any(c.islower() for c in jeton),
        any(c.isdigit() for c in jeton),
    ))
    return classes >= 2 and any(c.isdigit() for c in jeton)


def _luhn(chiffres: str) -> bool:
    total, alt = 0, False
    for c in reversed(chiffres):
        d = ord(c) - 48
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


# ─────────────────────────────────────────────────────────────────── la clé


def chemin_cle() -> Path:
    if env := os.environ.get("SENTINELLE_CLE"):
        return Path(env).expanduser()
    return Path.home() / ".sentinelle" / "cle_empreinte"


def cle() -> bytes:
    """Lit la clé locale, la crée au premier usage en 0600."""
    p = chemin_cle()
    if p.exists():
        return bytes.fromhex(p.read_text().strip())
    p.parent.mkdir(parents=True, exist_ok=True)
    valeur = _secrets.token_bytes(32)
    p.write_text(valeur.hex())
    try:
        p.chmod(0o600)
    except OSError:
        pass
    return valeur


def empreinte(valeur: str, k: bytes | None = None) -> str:
    return hmac.new(k or cle(), valeur.encode("utf-8"), hashlib.sha256).hexdigest()


# ──────────────────────────────────────────────────────────────── le rédacteur


@dataclass
class Trouvaille:
    genre: str
    empreinte: str
    indice: str        # préfixe public du format, jamais un bout du secret
    longueur: int


@dataclass
class Reglage:
    actif: bool = True
    donnees_personnelles: bool = True
    entropie: bool = True
    seuil_entropie: float = SEUIL_ENTROPIE
    motifs_perso: list[tuple[str, str]] = None      # (genre, expression)
    chemins_sensibles: list[str] = None             # contenu jeté en entier

    @classmethod
    def depuis_yaml(cls, data: dict | None) -> "Reglage":
        d = data or {}
        niveau = d.get("niveau", "normal")
        if niveau == "aucun":
            return cls(actif=False)
        return cls(
            actif=True,
            donnees_personnelles=d.get("donnees_personnelles", True),
            entropie=d.get("entropie", niveau != "leger"),
            seuil_entropie=float(d.get("seuil_entropie", SEUIL_ENTROPIE)),
            motifs_perso=[(m["genre"], m["expression"]) for m in d.get("motifs", [])],
            chemins_sensibles=d.get("chemins_sensibles", []) or [],
        )


class Redacteur:
    def __init__(self, reglage: Reglage | None = None, k: bytes | None = None):
        self.reglage = reglage or Reglage()
        self.cle = k or cle()
        self._perso = [
            (g, re.compile(e), 0, "")
            for g, e in (self.reglage.motifs_perso or [])
        ]

    # -------------------------------------------------------------- marqueur

    def _marqueur(self, genre: str, emp: str) -> str:
        return f"⟦{genre}·{emp[:6]}⟧"

    # ------------------------------------------------------------- rédaction

    def rediger(self, texte: str | None) -> tuple[str | None, list[Trouvaille]]:
        if texte is None or not self.reglage.actif or not texte:
            return texte, []

        motifs = list(MOTIFS) + self._perso
        if self.reglage.donnees_personnelles:
            motifs += MOTIFS_PERSONNELS

        spans: list[tuple[int, int, str, int]] = []
        priorites = {g: (1 if (g, e, gr, i) in MOTIFS_PERSONNELS else 0)
                     for g, e, gr, i in motifs}
        for genre, expr, groupe, indice in motifs:
            prio = priorites[genre]
            for m in expr.finditer(texte):
                deb, fin = m.span(groupe)
                if deb < 0:
                    continue
                valeur = texte[deb:fin]
                if genre in ("carte", "nas"):
                    chiffres = re.sub(r"\D", "", valeur)
                    # sans Luhn, tout numéro de commande devient une carte
                    if not (13 <= len(chiffres) <= 19 or len(chiffres) == 9):
                        continue
                    if not _luhn(chiffres):
                        continue
                spans.append((deb, fin, genre, prio))

        if self.reglage.entropie:
            for m in CANDIDAT_JETON.finditer(texte):
                deb, fin = m.span()
                jeton = m.group()
                if not _ressemble_a_un_jeton(jeton):
                    continue
                if entropie(jeton) < self.reglage.seuil_entropie:
                    continue
                spans.append((deb, fin, "jeton-opaque", 2))

        if not spans:
            return texte, []

        # On garde le plus long en cas de chevauchement : un JWT complet plutôt
        # que le fragment de haute entropie qu'il contient.
        # début, puis priorité, puis longueur : un JWT entier plutôt que le
        # fragment de haute entropie qu'il contient.
        spans.sort(key=lambda s: (s[0], s[3], -(s[1] - s[0])))
        retenus: list[tuple[int, int, str]] = []
        curseur = -1
        for deb, fin, genre, _prio in spans:
            if deb < curseur:
                continue
            retenus.append((deb, fin, genre))
            curseur = fin

        indices = {g: i for g, _e, _gr, i in motifs}
        morceaux: list[str] = []
        trouvailles: list[Trouvaille] = []
        precedent = 0
        for deb, fin, genre in retenus:
            valeur = texte[deb:fin]
            emp = empreinte(valeur, self.cle)
            morceaux.append(texte[precedent:deb])
            morceaux.append(self._marqueur(genre, emp))
            trouvailles.append(
                Trouvaille(genre, emp, indices.get(genre, ""), len(valeur))
            )
            precedent = fin
        morceaux.append(texte[precedent:])
        return "".join(morceaux), trouvailles

    def rediger_args(self, args: dict | None) -> tuple[dict | None, list[Trouvaille]]:
        if not args or not self.reglage.actif:
            return args, []
        out, toutes = {}, []
        for k, v in args.items():
            if isinstance(v, str):
                out[k], tr = self.rediger(v)
                toutes.extend(tr)
            else:
                out[k] = v
        return out, toutes

    def chemin_sensible(self, chemin: str | None) -> bool:
        import fnmatch
        if not chemin or not self.reglage.chemins_sensibles:
            return False
        return any(fnmatch.fnmatch(chemin, g)
                   for g in self.reglage.chemins_sensibles)

    def jeter_contenu(self, contenu: str, chemin: str) -> tuple[str, list[Trouvaille]]:
        """Fichier déclaré sensible : on ne garde rien du contenu, juste sa
        taille et son empreinte, ce qui suffit à prouver plus tard qu'un
        fichier donné est bien celui qui a été lu."""
        emp = empreinte(contenu, self.cle)
        marque = (f"⟦fichier-sensible·{emp[:6]}⟧ {len(contenu)} caractères "
                  f"non conservés ({chemin})")
        return marque, [Trouvaille("fichier-sensible", emp, "", len(contenu))]
