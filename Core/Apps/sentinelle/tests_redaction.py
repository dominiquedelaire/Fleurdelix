#!/usr/bin/env python3
"""Filet de sécurité du rédacteur.

Le caviardage est l'endroit où une erreur coûte cher dans les deux sens : trop
peu et le journal devient un coffre à secrets, trop et il devient illisible.
Ces cas gardent les deux bords.

    python3 tests_redaction.py
"""

import sys

from sentinelle.redaction import Redacteur, Reglage

DOIT_CAVIARDER = [
    ("stripe", "STRIPE_KEY=sk_live_51H8xQ2eZvKYlo2CkQm3nP"),
    ("aws", "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"),
    ("github", 'config = {"api_key": "ghp_16C7e42F292c6912E7710c838347Ae178B4a"}'),
    ("anthropic", "ANTHROPIC_API_KEY=sk-ant-api03-Xy9zAbCdEf1234567890GhIjKl"),
    ("jeton-jwt", "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcd1234"),
    ("mot-de-passe-url", 'DB_URL="postgres://app:Tr0ub4dour@db.interne:5432/prod"'),
    ("affectation", "DB_PASSWORD=hunter2"),          # faible, mais mot de passe
    ("affectation", "SECRET_KEY: correcthorse"),
    ("cle-privee", "-----BEGIN RSA PRIVATE KEY-----\nMIIEow...\n-----END RSA PRIVATE KEY-----"),
    ("jeton-opaque", "jeton maison: Zm9vYmFyc2VjcmV0dmFsdWUxMjM0NTY3ODkw"),
    ("courriel", "écris à marie.tremblay@exemple.qc.ca"),
    ("carte", "payé avec 4532015112830366"),
    ("nas", "NAS 046 454 286 pour le T4"),
]

DOIT_LAISSER_PASSER = [
    "commit 4a2f1c9e8b3d5f7a1c2e4b6d8f0a2c4e6b8d0f2a",
    "read_text_file /home/fleurdelix/projets/facturier/taxes.py",
    "write_file /home/fleurdelix/.config/systemd/user/facturier.service",
    "list_directory /home/fleurdelix/Documents/shellbots/webview_app",
    "GET https://api.exemple.dev/v2/factures?page=3&limite=50",
    "numéro de facture 2026-000481, montant 1 240,50 $",
    "TPS 5 %, TVQ 9,975 %, total 1 426,23",
    "aucun secret ici, juste du texte normal",
]


def principal() -> int:
    r = Redacteur(Reglage())
    echecs = []

    for genre_attendu, texte in DOIT_CAVIARDER:
        red, tr = r.rediger(texte)
        genres = [t.genre for t in tr]
        if genre_attendu not in genres:
            echecs.append(f"MANQUÉ  [{genre_attendu}] {texte}\n         → {red} {genres}")

    for texte in DOIT_LAISSER_PASSER:
        red, tr = r.rediger(texte)
        if tr:
            echecs.append(f"EXCÈS   {texte}\n         → {red} {[t.genre for t in tr]}")

    # le même secret doit donner le même marqueur, deux textes plus loin
    a, _ = r.rediger("clé sk_live_51H8xQ2eZvKYlo2CkQm3nP ici")
    b, _ = r.rediger("et sk_live_51H8xQ2eZvKYlo2CkQm3nP là")
    if a.split()[1] != b.split()[1]:
        echecs.append("CORRÉLATION  le même secret donne deux marqueurs différents")

    # aucun fragment du secret ne doit survivre dans le marqueur
    red, _ = r.rediger("sk_live_51H8xQ2eZvKYlo2CkQm3nP")
    if "51H8x" in red or "Q2eZv" in red:
        echecs.append("FUITE  un morceau du secret est resté dans le marqueur")

    total = len(DOIT_CAVIARDER) + len(DOIT_LAISSER_PASSER) + 2
    if echecs:
        print("\n".join(echecs))
        print(f"\n{len(echecs)} échec(s) sur {total} cas.")
        return 1
    print(f"{total} cas passés.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
