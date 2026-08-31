"""Schéma et accès SQLite.

Un seul fichier journal.db, ouvert en WAL : le proxy écrit pendant que
l'interface lit, sans blocage.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS runs (
    id          TEXT PRIMARY KEY,
    debut       TEXT NOT NULL,
    fin         TEXT,
    agent       TEXT,
    serveur     TEXT,
    cwd         TEXT,
    nb_evts     INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS evenements (
    seq         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT NOT NULL REFERENCES runs(id),
    ts          TEXT NOT NULL,
    type        TEXT NOT NULL,          -- appel | resultat | erreur | meta
    outil       TEXT,
    args_json   TEXT,
    resume      TEXT,                   -- une ligne lisible par un humain
    blob_hash   TEXT,                   -- contenu volumineux, dédupliqué
    duree_ms    INTEGER,
    rpc_id      TEXT,                   -- corrélation appel <-> resultat
    marques     TEXT,                   -- provenance, JSON list
    hash_prec   TEXT NOT NULL,
    hash        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_evt_run ON evenements(run_id, seq);

CREATE TABLE IF NOT EXISTS blobs (
    hash        TEXT PRIMARY KEY,
    taille      INTEGER,
    contenu     TEXT,
    efface      INTEGER DEFAULT 0,      -- purgé après coup ; la chaîne tient
    motif       TEXT
);

-- Catalogue des secrets aperçus. Aucune valeur en clair : seulement leur
-- empreinte HMAC, leur genre, et où ils sont passés.
CREATE TABLE IF NOT EXISTS secrets (
    empreinte   TEXT PRIMARY KEY,
    genre       TEXT NOT NULL,
    indice      TEXT,
    longueur    INTEGER,
    premier_ts  TEXT,
    dernier_ts  TEXT,
    occurrences INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS secrets_vus (
    empreinte   TEXT NOT NULL,
    evt_seq     INTEGER NOT NULL,
    run_id      TEXT NOT NULL,
    PRIMARY KEY (empreinte, evt_seq)
);

CREATE TABLE IF NOT EXISTS violations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT NOT NULL,
    evt_seq     INTEGER NOT NULL,
    origine_seq INTEGER,                -- pour les règles de séquence
    regle       TEXT NOT NULL,
    severite    TEXT NOT NULL,
    explication TEXT,
    mode        TEXT NOT NULL DEFAULT 'observe',   -- observe | bloque
    UNIQUE(evt_seq, regle, origine_seq)
);

CREATE INDEX IF NOT EXISTS idx_viol_run ON violations(run_id);

-- Demandes d'autorisation en attente d'un humain.
CREATE TABLE IF NOT EXISTS demandes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT NOT NULL,
    evt_seq     INTEGER,
    outil       TEXT,
    args_json   TEXT,
    resume      TEXT,
    regle       TEXT,
    severite    TEXT,
    explication TEXT,
    cree_ts     TEXT NOT NULL,
    etat        TEXT NOT NULL DEFAULT 'attente',  -- attente|accorde|refuse|expire
    decide_ts   TEXT,
    decideur    TEXT,
    motif       TEXT
);

CREATE INDEX IF NOT EXISTS idx_dem_etat ON demandes(etat, id);

-- Le frein d'urgence. Une seule ligne, id = 1.
CREATE TABLE IF NOT EXISTS arret (
    id      INTEGER PRIMARY KEY CHECK (id = 1),
    actif   INTEGER NOT NULL DEFAULT 0,
    ts      TEXT,
    motif   TEXT
);
INSERT OR IGNORE INTO arret (id, actif) VALUES (1, 0);
"""


def chemin_defaut() -> Path:
    """~/.sentinelle/journal.db, surchargeable par SENTINELLE_DB."""
    if env := os.environ.get("SENTINELLE_DB"):
        return Path(env).expanduser()
    return Path.home() / ".sentinelle" / "journal.db"


def connexion(chemin: Path | str | None = None) -> sqlite3.Connection:
    chemin = Path(chemin) if chemin else chemin_defaut()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False : le proxy écrit depuis ses deux threads de relais.
    # Les accès y sont protégés par un verrou côté proxy.
    con = sqlite3.connect(
        str(chemin), timeout=10.0, isolation_level=None, check_same_thread=False
    )
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    _migrer(con)
    return con


def _migrer(con: sqlite3.Connection) -> None:
    """Rattrape les journaux créés avant l'ajout d'une colonne."""
    colonnes = {r["name"] for r in con.execute("PRAGMA table_info(blobs)")}
    for nom, decl in (("efface", "INTEGER DEFAULT 0"), ("motif", "TEXT")):
        if nom not in colonnes:
            con.execute(f"ALTER TABLE blobs ADD COLUMN {nom} {decl}")
