"""
Couche de stockage de Task365.

Tout passe par SQLite, en local, dans ~/.task365/task365.db.
(Reprise automatique d'une ancienne base ~/.shellbots/shellbots.db si presente.)
Le schema est volontairement generique : tout est une "entry"
(tache, entree de journal, contact, note...) avec un type, du texte,
des dates, des tags et des metriques chiffrees libres.

Cette generalite est ce qui permettra plus tard :
  - d'ajouter de nouveaux types d'information sans changer le schema,
  - de brancher une IA qui interroge la base avec des requetes simples.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

DB_DIR = Path.home() / ".task365"
DB_PATH = DB_DIR / "task365.db"

# Reprise transparente d'une base creee par l'ancienne version ("shellbots").
# Si la nouvelle base n'existe pas encore mais que l'ancienne est presente,
# on la reutilise pour ne perdre aucune donnee.
_OLD_DB = Path.home() / ".shellbots" / "shellbots.db"
if not DB_PATH.exists() and _OLD_DB.exists():
    try:
        DB_DIR.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(_OLD_DB, DB_PATH)
    except OSError:
        # en cas d'echec, on retombe simplement sur une base neuve
        pass

# Les types d'entrees connus. La liste sert a la validation douce et a
# l'affichage ; ajouter un type ne casse rien.
ENTRY_TYPES = ("task", "journal", "contact", "note", "recurrence", "budget",
               "sport", "food")


SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    initial_balance REAL NOT NULL DEFAULT 0,
    -- date a laquelle le solde initial est valable ; les operations
    -- anterieures a cette date ne sont pas comptees dans le solde.
    opened_on       TEXT,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT NOT NULL,
    title       TEXT,
    body        TEXT,
    created_at  TEXT NOT NULL,
    -- date "metier" de l'entree : echeance d'une tache, date du jour
    -- journalise, etc. Peut etre NULL.
    date        TEXT,
    -- pour les taches : 0 = a faire, 1 = fait
    done        INTEGER NOT NULL DEFAULT 0,
    -- lien optionnel vers une autre entree (ex: note rattachee a un contact,
    -- ou les deux jambes d'un virement reliees entre elles)
    parent_id   INTEGER REFERENCES entries(id) ON DELETE CASCADE,
    -- pour les operations budget : compte concerne et montant signe
    -- (negatif = depense, positif = revenu). NULL pour les autres types.
    account_id  INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    amount      REAL,
    -- pour les taches : 1 = prioritaire, 0 = normale
    priority    INTEGER NOT NULL DEFAULT 0,
    -- pour les operations budget : 1 = rapproche avec le compte bancaire
    reconciled  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tags (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS entry_tags (
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    tag_id   INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (entry_id, tag_id)
);

-- Metriques chiffrees libres rattachees a une entree :
-- ("poids", 78.5), ("humeur", 7), ("sommeil_h", 6.5), ("tension", 12)...
-- Le nom est libre : pas besoin de modifier le schema pour suivre
-- une nouvelle constante.
CREATE TABLE IF NOT EXISTS metrics (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    name     TEXT NOT NULL,
    value    REAL NOT NULL,
    unit     TEXT
);

-- Regles de recurrence : a partir d'un modele, on genere des taches
-- (ou autres entrees) a intervalle regulier.
--   freq   : daily | weekly | monthly
--   interval : tous les N (freq). interval=2 + weekly = toutes les 2 semaines
--   title / tags_json : ce qui sera recopie dans chaque entree generee
--   last_run : derniere date pour laquelle on a deja genere
--   until    : date de fin optionnelle
CREATE TABLE IF NOT EXISTS recurrences (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    gen_type   TEXT NOT NULL DEFAULT 'task',
    title      TEXT NOT NULL,
    tags_json  TEXT,
    freq       TEXT NOT NULL,
    interval   INTEGER NOT NULL DEFAULT 1,
    start      TEXT NOT NULL,
    until      TEXT,
    last_run   TEXT,
    active     INTEGER NOT NULL DEFAULT 1,
    -- pour les recurrences de type budget : compte et montant a recopier
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    amount     REAL
);

CREATE INDEX IF NOT EXISTS idx_entries_type ON entries(type);
CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(date);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name);

-- ===== Module Depenses =====

-- Un "code de taxe" regroupe une ou plusieurs taxes (ex: code Quebec = TPS+TVQ,
-- code France = TVA). is_default marque celui applique par defaut.
CREATE TABLE IF NOT EXISTS tax_codes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    is_default INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

-- Les taxes composant un code, avec leur nom et leur taux (en %).
CREATE TABLE IF NOT EXISTS tax_lines (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tax_code_id INTEGER NOT NULL REFERENCES tax_codes(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,     -- ex: "TPS", "TVQ", "TVA"
    rate        REAL NOT NULL,     -- ex: 5.0, 9.975, 18.6
    position    INTEGER NOT NULL DEFAULT 0
);

-- Categories de depenses (simples : un nom).
CREATE TABLE IF NOT EXISTS expense_categories (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

-- Les depenses. Les montants HT/TTC et les taxes sont en CAD ($ de base).
-- tax_detail_json stocke le detail calcule des taxes au moment de la saisie
-- (nom -> montant), pour figer le calcul meme si le code evolue ensuite.
CREATE TABLE IF NOT EXISTS expenses (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,
    label        TEXT,
    category_id  INTEGER REFERENCES expense_categories(id) ON DELETE SET NULL,
    tax_code_id  INTEGER REFERENCES tax_codes(id) ON DELETE SET NULL,
    no_tax       INTEGER NOT NULL DEFAULT 0,   -- 1 = pas de taxes
    amount_ht    REAL NOT NULL DEFAULT 0,      -- hors taxes (CAD)
    amount_ttc   REAL NOT NULL DEFAULT 0,      -- toutes taxes (CAD)
    tax_total    REAL NOT NULL DEFAULT 0,      -- somme des taxes (CAD)
    tax_detail_json TEXT,                      -- {nom: montant} fige
    tip          REAL NOT NULL DEFAULT 0,      -- pourboire (CAD), a part du TTC
    currency     TEXT NOT NULL DEFAULT 'CAD',
    amount_currency REAL,                      -- montant dans la devise (note)
    is_personal  INTEGER NOT NULL DEFAULT 1,   -- 1 = compte perso, 0 = entreprise
    op_type      TEXT NOT NULL DEFAULT 'expense', -- 'expense' ou 'income'
    third_party  TEXT,                         -- fournisseur (dépense) ou client (revenu)
    created_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
"""


def get_connection() -> sqlite3.Connection:
    """Ouvre la base (en la creant au besoin) et active les cles etrangeres."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Cree les tables si elles n'existent pas encore."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        _migrate_columns(conn)
    # cree le code de taxe par defaut (Quebec) au premier lancement
    seed_default_tax_codes()


def _migrate_columns(conn) -> None:
    """
    Ajoute les colonnes manquantes aux tables existantes (les bases creees
    avant l'ajout d'une colonne ne l'ont pas, car CREATE TABLE IF NOT EXISTS
    ne modifie pas une table deja presente). Sans danger : ne touche a rien
    si la colonne existe deja.
    """
    migrations = {
        "expenses": [("is_personal", "INTEGER NOT NULL DEFAULT 1"),
                     ("op_type", "TEXT NOT NULL DEFAULT 'expense'"),
                     ("third_party", "TEXT")],
        "entries": [("priority", "INTEGER NOT NULL DEFAULT 0"),
                    ("reconciled", "INTEGER NOT NULL DEFAULT 0")],
    }
    for table, cols in migrations.items():
        existing = {r["name"] for r in
                    conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for col_name, col_def in cols:
            if col_name not in existing:
                conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")


# --------------------------------------------------------------------------
# Tags
# --------------------------------------------------------------------------

def _get_or_create_tag(conn: sqlite3.Connection, name: str) -> int:
    name = name.strip().lstrip("#").lower()
    cur = conn.execute("SELECT id FROM tags WHERE name = ?", (name,))
    row = cur.fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO tags(name) VALUES (?)", (name,))
    return cur.lastrowid


def _attach_tags(conn: sqlite3.Connection, entry_id: int, tags: Iterable[str]) -> None:
    for tag in tags:
        if not tag.strip():
            continue
        tag_id = _get_or_create_tag(conn, tag)
        conn.execute(
            "INSERT OR IGNORE INTO entry_tags(entry_id, tag_id) VALUES (?, ?)",
            (entry_id, tag_id),
        )


def get_tags_for_entry(conn: sqlite3.Connection, entry_id: int) -> list[str]:
    cur = conn.execute(
        """
        SELECT t.name FROM tags t
        JOIN entry_tags et ON et.tag_id = t.id
        WHERE et.entry_id = ?
        ORDER BY t.name
        """,
        (entry_id,),
    )
    return [r["name"] for r in cur.fetchall()]


# --------------------------------------------------------------------------
# Metriques
# --------------------------------------------------------------------------

def _attach_metrics(
    conn: sqlite3.Connection, entry_id: int, metrics: dict[str, Any]
) -> None:
    """metrics: {"poids": 78.5, "humeur": 7} ou {"poids": (78.5, "kg")}."""
    for name, raw in metrics.items():
        if isinstance(raw, (tuple, list)):
            value, unit = raw[0], (raw[1] if len(raw) > 1 else None)
        else:
            value, unit = raw, None
        conn.execute(
            "INSERT INTO metrics(entry_id, name, value, unit) VALUES (?, ?, ?, ?)",
            (entry_id, name.strip().lower(), float(value), unit),
        )


def get_metrics_for_entry(conn: sqlite3.Connection, entry_id: int) -> dict[str, dict]:
    cur = conn.execute(
        "SELECT name, value, unit FROM metrics WHERE entry_id = ? ORDER BY name",
        (entry_id,),
    )
    return {r["name"]: {"value": r["value"], "unit": r["unit"]} for r in cur.fetchall()}


def metric_history(name: str, limit: int | None = None) -> list[dict]:
    """Historique d'une metrique dans le temps, pour tracer une evolution."""
    name = name.strip().lower()
    query = """
        SELECT m.value, m.unit, COALESCE(e.date, e.created_at) AS when_
        FROM metrics m
        JOIN entries e ON e.id = m.entry_id
        WHERE m.name = ?
        ORDER BY when_ ASC
    """
    with get_connection() as conn:
        rows = conn.execute(query, (name,)).fetchall()
    data = [dict(r) for r in rows]
    if limit:
        data = data[-limit:]
    return data


# --------------------------------------------------------------------------
# CRUD generique sur les entrees
# --------------------------------------------------------------------------

def add_entry(
    type: str,
    title: str | None = None,
    body: str | None = None,
    date: str | None = None,
    tags: Iterable[str] | None = None,
    metrics: dict[str, Any] | None = None,
    parent_id: int | None = None,
    account_id: int | None = None,
    amount: float | None = None,
    priority: int = 0,
) -> int:
    """Cree une entree de n'importe quel type et renvoie son id."""
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO entries(type, title, body, created_at, date,
                                parent_id, account_id, amount, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (type, title, body, now, date, parent_id, account_id, amount,
             1 if priority else 0),
        )
        entry_id = cur.lastrowid
        if tags:
            _attach_tags(conn, entry_id, tags)
        if metrics:
            _attach_metrics(conn, entry_id, metrics)
    return entry_id


def set_done(entry_id: int, done: bool = True) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE entries SET done = ? WHERE id = ?", (1 if done else 0, entry_id)
        )


def delete_entry(entry_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))


def _hydrate(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    """Transforme une ligne en dict complet avec tags et metriques."""
    entry = dict(row)
    entry["tags"] = get_tags_for_entry(conn, row["id"])
    entry["metrics"] = get_metrics_for_entry(conn, row["id"])
    return entry


def list_entries(
    type: str | None = None,
    tag: str | None = None,
    done: bool | None = None,
    parent_id: int | None = None,
    since: str | None = None,
    until: str | None = None,
    order: str = "date",
) -> list[dict]:
    """Liste filtrable d'entrees, chacune hydratee avec ses tags/metriques."""
    clauses: list[str] = []
    params: list[Any] = []

    if type:
        clauses.append("e.type = ?")
        params.append(type)
    if done is not None:
        clauses.append("e.done = ?")
        params.append(1 if done else 0)
    if parent_id is not None:
        clauses.append("e.parent_id = ?")
        params.append(parent_id)
    if since:
        clauses.append("COALESCE(e.date, e.created_at) >= ?")
        params.append(since)
    if until:
        clauses.append("COALESCE(e.date, e.created_at) <= ?")
        params.append(until)
    if tag:
        clauses.append(
            "e.id IN (SELECT et.entry_id FROM entry_tags et "
            "JOIN tags t ON t.id = et.tag_id WHERE t.name = ?)"
        )
        params.append(tag.strip().lstrip("#").lower())

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    order_col = {
        "date": "COALESCE(e.date, e.created_at)",
        "created": "e.created_at",
        "id": "e.id",
    }.get(order, "COALESCE(e.date, e.created_at)")

    query = f"SELECT e.* FROM entries e {where} ORDER BY {order_col} ASC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [_hydrate(conn, r) for r in rows]


def get_entry(entry_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
        return _hydrate(conn, row) if row else None


def all_tags() -> list[tuple[str, int]]:
    """Tous les tags avec le nombre d'entrees associees."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT t.name, COUNT(et.entry_id) AS n
            FROM tags t
            LEFT JOIN entry_tags et ON et.tag_id = t.id
            GROUP BY t.id
            ORDER BY n DESC, t.name ASC
            """
        ).fetchall()
    return [(r["name"], r["n"]) for r in rows]


def entries_in_month(year: int, month: int) -> dict[str, list[dict]]:
    """
    Renvoie les entrees ayant une date dans le mois donne, regroupees par
    jour ISO (YYYY-MM-DD). Pratique pour colorer un calendrier.
    """
    prefix = f"{year:04d}-{month:02d}"
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM entries WHERE date LIKE ? ORDER BY date",
            (f"{prefix}%",),
        ).fetchall()
        grouped: dict[str, list[dict]] = {}
        for r in rows:
            entry = _hydrate(conn, r)
            day = (entry["date"] or "")[:10]
            grouped.setdefault(day, []).append(entry)
    return grouped


def entries_on_day(day_iso: str) -> list[dict]:
    """Toutes les entrees dont la date metier est ce jour-la."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM entries WHERE date = ? ORDER BY type, id",
            (day_iso,),
        ).fetchall()
        return [_hydrate(conn, r) for r in rows]


def activity_counts(since: str, until: str,
                    type: str | None = None) -> dict[str, int]:
    """
    Compte le nombre d'entrees par jour (date metier) entre since et until.
    Optionnellement filtre par type (task, sport, journal, food, budget...).
    Renvoie {jour_iso: nombre}. Une seule requete SQL, donc rapide meme sur
    une annee entiere.
    """
    clauses = ["date IS NOT NULL", "date >= ?", "date <= ?"]
    params: list[Any] = [since, until]
    if type:
        clauses.append("type = ?")
        params.append(type)
    where = " AND ".join(clauses)
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT substr(date,1,10) AS d, COUNT(*) AS n "
            f"FROM entries WHERE {where} GROUP BY d",
            params,
        ).fetchall()
    return {r["d"]: r["n"] for r in rows}


def export_json() -> str:
    """Exporte toute la base en JSON (utile pour sauvegarde / futur IA)."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM entries ORDER BY id").fetchall()
        data = [_hydrate(conn, r) for r in rows]
    return json.dumps(data, indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------
# Modification d'une entree existante
# --------------------------------------------------------------------------

def update_entry(
    entry_id: int,
    title: str | None = None,
    body: str | None = None,
    date: str | None = None,
    tags: Iterable[str] | None = None,
    metrics: dict[str, Any] | None = None,
    priority: int | None = None,
) -> bool:
    """
    Met a jour les champs fournis (les autres restent inchanges).
    - tags : si fourni, REMPLACE l'ensemble des tags de l'entree.
    - metrics : si fourni, ajoute/met a jour ces metriques (par nom).
    - priority : 0 ou 1 (None = inchange).
    Renvoie False si l'entree n'existe pas.
    """
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM entries WHERE id = ?", (entry_id,)).fetchone()
        if not row:
            return False

        sets, params = [], []
        if title is not None:
            sets.append("title = ?"); params.append(title)
        if body is not None:
            sets.append("body = ?"); params.append(body)
        if date is not None:
            sets.append("date = ?"); params.append(date)
        if priority is not None:
            sets.append("priority = ?"); params.append(1 if priority else 0)
        if sets:
            params.append(entry_id)
            conn.execute(f"UPDATE entries SET {', '.join(sets)} WHERE id = ?", params)

        if tags is not None:
            conn.execute("DELETE FROM entry_tags WHERE entry_id = ?", (entry_id,))
            _attach_tags(conn, entry_id, tags)

        if metrics:
            for name in metrics:
                conn.execute(
                    "DELETE FROM metrics WHERE entry_id = ? AND name = ?",
                    (entry_id, name.strip().lower()),
                )
            _attach_metrics(conn, entry_id, metrics)
    return True


def replace_metrics(entry_id: int, metrics: dict[str, Any] | None) -> bool:
    """
    Remplace COMPLETEMENT le jeu de metriques d'une entree par celui fourni :
    toutes les metriques absentes du dict sont supprimees. Utile quand le
    formulaire envoie l'etat final voulu (et qu'on veut donc effacer celles
    que l'utilisateur a retirees). Contrairement a update_entry(metrics=...)
    qui ne fait qu'ajouter/mettre a jour sans rien supprimer.
    """
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM entries WHERE id = ?",
                           (entry_id,)).fetchone()
        if not row:
            return False
        conn.execute("DELETE FROM metrics WHERE entry_id = ?", (entry_id,))
        if metrics:
            _attach_metrics(conn, entry_id, metrics)
    return True


# --------------------------------------------------------------------------
# Recurrences
# --------------------------------------------------------------------------

def add_recurrence(
    title: str,
    freq: str,
    interval: int = 1,
    start: str | None = None,
    until: str | None = None,
    tags: Iterable[str] | None = None,
    gen_type: str = "task",
    account_id: int | None = None,
    amount: float | None = None,
) -> int:
    from datetime import date as _date
    start = start or _date.today().isoformat()
    tags_json = json.dumps(list(tags)) if tags else None
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO recurrences(gen_type, title, tags_json, freq, interval,
                                    start, until, last_run, active,
                                    account_id, amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 1, ?, ?)
            """,
            (gen_type, title, tags_json, freq, interval, start, until,
             account_id, amount),
        )
        return cur.lastrowid


def list_recurrences(active_only: bool = True) -> list[dict]:
    query = "SELECT * FROM recurrences"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY id"
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["tags"] = json.loads(d["tags_json"]) if d["tags_json"] else []
        out.append(d)
    return out


def delete_recurrence(rec_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM recurrences WHERE id = ?", (rec_id,))


def set_recurrence_active(rec_id: int, active: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE recurrences SET active = ? WHERE id = ?",
            (1 if active else 0, rec_id),
        )


def _occurrences(start_iso: str, freq: str, interval: int,
                 from_iso: str, to_iso: str) -> list[str]:
    """Liste des dates (ISO) ou la regle tombe, entre from_iso et to_iso inclus."""
    from datetime import date as _date, timedelta

    def parse(s): return _date.fromisoformat(s[:10])

    cur = parse(start_iso)
    end = parse(to_iso)
    lo = parse(from_iso)
    interval = max(1, interval)
    dates: list[str] = []
    guard = 0
    while cur <= end and guard < 10000:
        guard += 1
        if cur >= lo:
            dates.append(cur.isoformat())
        if freq == "daily":
            cur += timedelta(days=interval)
        elif freq == "weekly":
            cur += timedelta(weeks=interval)
        elif freq == "monthly":
            # avance de `interval` mois en gerant le debordement d'annee
            m = cur.month - 1 + interval
            y = cur.year + m // 12
            m = m % 12 + 1
            day = min(cur.day, [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
                                else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
            cur = _date(y, m, day)
        else:
            break
    return dates


def run_recurrences(until_iso: str | None = None) -> list[dict]:
    """
    Genere les entrees dues pour chaque recurrence active, jusqu'a until_iso
    (defaut: aujourd'hui). Idempotent : ne regenere pas ce qui l'a deja ete
    (on s'appuie sur last_run). Renvoie la liste des entrees creees.
    """
    from datetime import date as _date

    until_iso = until_iso or _date.today().isoformat()
    created: list[dict] = []

    for rec in list_recurrences(active_only=True):
        horizon = rec["until"] or until_iso
        effective_until = min(horizon, until_iso)
        # on part du lendemain du dernier run, sinon de la date de debut
        if rec["last_run"]:
            from datetime import timedelta
            start_from = (_date.fromisoformat(rec["last_run"][:10])
                          + timedelta(days=1)).isoformat()
        else:
            start_from = rec["start"]

        if start_from > effective_until:
            continue

        dates = _occurrences(rec["start"], rec["freq"], rec["interval"],
                             start_from, effective_until)
        for d in dates:
            eid = add_entry(
                type=rec["gen_type"],
                title=rec["title"],
                date=d,
                tags=rec["tags"] or None,
                account_id=rec["account_id"],
                amount=rec["amount"],
            )
            created.append({"id": eid, "title": rec["title"], "date": d,
                            "recurrence_id": rec["id"]})

        if dates:
            with get_connection() as conn:
                conn.execute(
                    "UPDATE recurrences SET last_run = ? WHERE id = ?",
                    (max(dates), rec["id"]),
                )
    return created


# --------------------------------------------------------------------------
# Recherche transversale (texte, tag, metrique, date)
# --------------------------------------------------------------------------

def search(term: str) -> list[dict]:
    """
    Cherche `term` partout et renvoie les entrees correspondantes, hydratees,
    avec un champ 'match' indiquant ou la correspondance a ete trouvee.

    Le terme peut etre :
      - une date ISO (2026-06-10) ou un fragment -> recherche par date
      - un #tag                                   -> recherche par tag
      - un nom de metrique (poids, humeur...)     -> entrees ayant cette metrique
      - n'importe quel mot                        -> titre + corps
    """
    term = term.strip()
    low = term.lstrip("#").lower()
    like = f"%{low}%"
    found: dict[int, dict] = {}

    def add(row_id: int, where: str):
        if row_id in found:
            if where not in found[row_id]["match"]:
                found[row_id]["match"].append(where)
            return
        entry = get_entry(row_id)
        if entry:
            entry["match"] = [where]
            found[row_id] = entry

    with get_connection() as conn:
        # titre + corps
        for r in conn.execute(
            "SELECT id FROM entries WHERE LOWER(title) LIKE ? OR LOWER(body) LIKE ?",
            (like, like),
        ).fetchall():
            add(r["id"], "texte")

        # date (sur date metier OU date de creation)
        for r in conn.execute(
            "SELECT id FROM entries WHERE date LIKE ? OR created_at LIKE ?",
            (like, like),
        ).fetchall():
            add(r["id"], "date")

        # tag
        for r in conn.execute(
            """
            SELECT et.entry_id AS id FROM entry_tags et
            JOIN tags t ON t.id = et.tag_id
            WHERE t.name LIKE ?
            """,
            (like,),
        ).fetchall():
            add(r["id"], "tag")

        # metrique (par nom)
        for r in conn.execute(
            "SELECT DISTINCT entry_id AS id FROM metrics WHERE name LIKE ?",
            (like,),
        ).fetchall():
            add(r["id"], "métrique")

    return sorted(found.values(),
                  key=lambda e: (e.get("date") or e["created_at"]), reverse=True)


# --------------------------------------------------------------------------
# Comptes bancaires
# --------------------------------------------------------------------------

def add_account(name: str, initial_balance: float = 0.0,
                opened_on: str | None = None) -> int:
    """Cree un compte avec un solde initial a une date donnee."""
    from datetime import date as _date
    now = datetime.now().isoformat(timespec="seconds")
    opened_on = opened_on or _date.today().isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO accounts(name, initial_balance, opened_on, created_at)
               VALUES (?, ?, ?, ?)""",
            (name.strip(), float(initial_balance), opened_on, now),
        )
        return cur.lastrowid


def get_account(account_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM accounts WHERE id = ?",
                           (account_id,)).fetchone()
        return dict(row) if row else None


def get_account_by_name(name: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM accounts WHERE name = ?",
                           (name.strip(),)).fetchone()
        return dict(row) if row else None


def resolve_account(ref: str) -> dict | None:
    """Accepte un id numerique ou un nom de compte."""
    if ref is None:
        return None
    ref = str(ref).strip()
    if ref.isdigit():
        return get_account(int(ref))
    return get_account_by_name(ref)


def list_accounts() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM accounts ORDER BY name").fetchall()
        return [dict(r) for r in rows]


def update_account(account_id: int, name: str | None = None,
                   initial_balance: float | None = None,
                   opened_on: str | None = None) -> bool:
    sets, params = [], []
    if name is not None:
        sets.append("name = ?"); params.append(name.strip())
    if initial_balance is not None:
        sets.append("initial_balance = ?"); params.append(float(initial_balance))
    if opened_on is not None:
        sets.append("opened_on = ?"); params.append(opened_on)
    if not sets:
        return False
    params.append(account_id)
    with get_connection() as conn:
        cur = conn.execute(
            f"UPDATE accounts SET {', '.join(sets)} WHERE id = ?", params)
        return cur.rowcount > 0


def delete_account(account_id: int) -> None:
    """Supprime le compte ET ses operations (cascade)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))


# --------------------------------------------------------------------------
# Operations budget
# --------------------------------------------------------------------------

def add_budget_entry(account_id: int, amount: float, title: str,
                     date: str | None = None,
                     tags: Iterable[str] | None = None) -> int:
    """
    Ajoute une operation budget. amount negatif = depense, positif = revenu.
    La categorie passe par les tags (ex: ['alimentation']).
    """
    from datetime import date as _date
    return add_entry(
        type="budget",
        title=title,
        date=date or _date.today().isoformat(),
        tags=tags,
        account_id=account_id,
        amount=float(amount),
    )


def set_reconciled(entry_id: int, reconciled: bool) -> bool:
    """Marque une operation budget comme rapprochee (ou non) avec la banque."""
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE entries SET reconciled = ? WHERE id = ? AND type = 'budget'",
            (1 if reconciled else 0, int(entry_id)))
        return cur.rowcount > 0


def add_transfer(from_account_id: int, to_account_id: int, amount: float,
                 title: str | None = None, date: str | None = None,
                 tags: Iterable[str] | None = None) -> tuple[int, int]:
    """
    Cree un virement = deux operations liees :
      - une depense (-amount) sur le compte source
      - un revenu  (+amount) sur le compte destination
    Les deux sont reliees par parent_id pour pouvoir les retrouver ensemble.
    amount doit etre positif (c'est le montant transfere).
    """
    from datetime import date as _date
    amount = abs(float(amount))
    d = date or _date.today().isoformat()
    src = get_account(from_account_id)
    dst = get_account(to_account_id)
    src_name = src["name"] if src else str(from_account_id)
    dst_name = dst["name"] if dst else str(to_account_id)
    base = title or f"Virement {src_name} → {dst_name}"
    tag_list = list(tags) if tags else []
    if "virement" not in tag_list:
        tag_list.append("virement")

    out_id = add_entry(type="budget", title=f"{base} (sortant)", date=d,
                       tags=tag_list, account_id=from_account_id, amount=-amount)
    in_id = add_entry(type="budget", title=f"{base} (entrant)", date=d,
                      tags=tag_list, account_id=to_account_id, amount=amount,
                      parent_id=out_id)
    return out_id, in_id


def list_budget_entries(account_id: int | None = None,
                        since: str | None = None,
                        until: str | None = None,
                        tag: str | None = None) -> list[dict]:
    """Operations budget, filtrables par compte / periode / categorie(tag)."""
    clauses = ["e.type = 'budget'"]
    params: list[Any] = []
    if account_id is not None:
        clauses.append("e.account_id = ?"); params.append(account_id)
    if since:
        clauses.append("e.date >= ?"); params.append(since)
    if until:
        clauses.append("e.date <= ?"); params.append(until)
    if tag:
        clauses.append(
            "e.id IN (SELECT et.entry_id FROM entry_tags et "
            "JOIN tags t ON t.id = et.tag_id WHERE t.name = ?)")
        params.append(tag.strip().lstrip("#").lower())
    where = "WHERE " + " AND ".join(clauses)
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT e.* FROM entries e {where} ORDER BY e.date, e.id", params
        ).fetchall()
        return [_hydrate(conn, r) for r in rows]


# --------------------------------------------------------------------------
# Calcul des soldes (la source de verite, c'est la somme des operations)
# --------------------------------------------------------------------------

def balance_at(account_id: int, as_of: str | None = None) -> float:
    """
    Solde du compte a la date as_of (incluse) :
      solde initial + somme des operations entre opened_on et as_of.
    Si as_of est None, solde a aujourd'hui. Fonctionne aussi pour des
    dates futures (projection).
    """
    from datetime import date as _date
    acc = get_account(account_id)
    if not acc:
        return 0.0
    as_of = as_of or _date.today().isoformat()
    opened = acc["opened_on"] or "0000-01-01"
    with get_connection() as conn:
        row = conn.execute(
            """SELECT COALESCE(SUM(amount), 0) AS s FROM entries
               WHERE type='budget' AND account_id=? AND date>=? AND date<=?""",
            (account_id, opened, as_of),
        ).fetchone()
    return round(acc["initial_balance"] + (row["s"] or 0.0), 2)


def balance_series(account_id: int, since: str | None = None,
                   until: str | None = None) -> list[dict]:
    """
    Solde jour par jour entre since et until, uniquement aux dates ou il y a
    au moins une operation (plus le solde courant). Pratique pour un historique.
    Renvoie [{date, balance, delta}].
    """
    acc = get_account(account_id)
    if not acc:
        return []
    ops = list_budget_entries(account_id=account_id, since=since, until=until)
    # regroupe par jour
    by_day: dict[str, float] = {}
    for op in ops:
        d = (op["date"] or "")[:10]
        by_day[d] = by_day.get(d, 0.0) + (op["amount"] or 0.0)
    running = balance_at(account_id, since) - sum(
        v for k, v in by_day.items() if since and k == since[:10]
    ) if since else acc["initial_balance"]
    # plus simple et robuste : recalcul cumulatif depuis le debut
    series = []
    for day in sorted(by_day.keys()):
        bal = balance_at(account_id, day)
        series.append({"date": day, "balance": bal, "delta": round(by_day[day], 2)})
    return series


def category_breakdown(account_id: int | None = None,
                       since: str | None = None,
                       until: str | None = None) -> list[dict]:
    """
    Repartition des operations par categorie (tag), sur la periode.
    Renvoie [{category, total, count}] trie par total croissant
    (depenses les plus negatives en tete).
    """
    ops = list_budget_entries(account_id=account_id, since=since, until=until)
    buckets: dict[str, dict] = {}
    for op in ops:
        amt = op["amount"] or 0.0
        cats = [t for t in op["tags"] if t != "virement"] or ["(sans catégorie)"]
        for cat in cats:
            b = buckets.setdefault(cat, {"category": cat, "total": 0.0, "count": 0})
            b["total"] = round(b["total"] + amt, 2)
            b["count"] += 1
    return sorted(buckets.values(), key=lambda x: x["total"])


def recalculate() -> dict:
    """
    'Recalcule' les soldes. Comme les soldes sont toujours derives des
    operations (jamais stockes), il n'y a rien a reparer : cette fonction
    renvoie simplement le solde recalcule de chaque compte, ce qui sert de
    verification de coherence et repond au besoin d'une commande explicite.
    """
    result = {}
    for acc in list_accounts():
        result[acc["name"]] = balance_at(acc["id"])
    return result


# --------------------------------------------------------------------------
# Modification / suppression d'operations budget
# --------------------------------------------------------------------------

def get_budget_entry(entry_id: int) -> dict | None:
    """Recupere une operation budget (ou None si ce n'en est pas une)."""
    entry = get_entry(entry_id)
    if not entry or entry["type"] != "budget":
        return None
    return entry


def _transfer_legs(entry_id: int) -> list[int]:
    """
    Si l'entree fait partie d'un virement, renvoie les ids des DEUX jambes.
    La jambe entrante a parent_id = id de la jambe sortante.
    Sinon renvoie [entry_id] seul.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, parent_id FROM entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if not row:
            return []
        # cette entree est-elle une jambe entrante ? (a un parent budget)
        if row["parent_id"]:
            parent = conn.execute(
                "SELECT id, type FROM entries WHERE id = ?", (row["parent_id"],)
            ).fetchone()
            if parent and parent["type"] == "budget":
                return [parent["id"], entry_id]
        # ou est-elle une jambe sortante ? (un enfant budget pointe sur elle)
        child = conn.execute(
            "SELECT id FROM entries WHERE parent_id = ? AND type = 'budget'",
            (entry_id,),
        ).fetchone()
        if child:
            return [entry_id, child["id"]]
    return [entry_id]


def is_transfer(entry_id: int) -> bool:
    return len(_transfer_legs(entry_id)) > 1


def update_budget_entry(entry_id: int, amount: float | None = None,
                        title: str | None = None, date: str | None = None,
                        account_id: int | None = None,
                        tags: Iterable[str] | None = None) -> bool:
    """
    Modifie une operation budget simple. Pour une operation faisant partie
    d'un virement, utiliser update_transfer (sinon on casse l'equilibre).
    Renvoie False si l'entree n'existe pas ou n'est pas un budget simple.
    """
    entry = get_budget_entry(entry_id)
    if not entry:
        return False
    if is_transfer(entry_id):
        raise ValueError(
            "Cette opération fait partie d'un virement. "
            "Utilise 'budget transfer-edit' ou supprime puis recrée le virement."
        )
    # met a jour les champs simples via SQL direct (amount/account ne passent
    # pas par update_entry qui ne gere que title/body/date/tags/metrics)
    sets, params = [], []
    if amount is not None:
        sets.append("amount = ?"); params.append(float(amount))
    if title is not None:
        sets.append("title = ?"); params.append(title)
    if date is not None:
        sets.append("date = ?"); params.append(date)
    if account_id is not None:
        sets.append("account_id = ?"); params.append(account_id)
    with get_connection() as conn:
        if sets:
            params.append(entry_id)
            conn.execute(f"UPDATE entries SET {', '.join(sets)} WHERE id = ?",
                         params)
        if tags is not None:
            conn.execute("DELETE FROM entry_tags WHERE entry_id = ?", (entry_id,))
            _attach_tags(conn, entry_id, tags)
    return True


def update_transfer(entry_id: int, amount: float | None = None,
                    date: str | None = None) -> bool:
    """
    Modifie un virement en gardant les deux jambes equilibrees.
    On ne change que le montant (applique en -/+ sur les deux jambes) et/ou
    la date (sur les deux). Renvoie False si ce n'est pas un virement.
    """
    legs = _transfer_legs(entry_id)
    if len(legs) < 2:
        return False
    out_id, in_id = legs[0], legs[1]
    with get_connection() as conn:
        if amount is not None:
            amount = abs(float(amount))
            conn.execute("UPDATE entries SET amount = ? WHERE id = ?",
                         (-amount, out_id))
            conn.execute("UPDATE entries SET amount = ? WHERE id = ?",
                         (amount, in_id))
        if date is not None:
            conn.execute("UPDATE entries SET date = ? WHERE id IN (?, ?)",
                         (date, out_id, in_id))
    return True


def delete_budget_entry(entry_id: int) -> tuple[bool, bool]:
    """
    Supprime une operation budget. Si elle fait partie d'un virement,
    supprime AUSSI l'autre jambe pour garder les soldes coherents.
    Renvoie (supprimee, etait_un_virement).
    """
    entry = get_budget_entry(entry_id)
    if not entry:
        return (False, False)
    legs = _transfer_legs(entry_id)
    was_transfer = len(legs) > 1
    with get_connection() as conn:
        for leg in legs:
            conn.execute("DELETE FROM entries WHERE id = ?", (leg,))
    return (True, was_transfer)


# --------------------------------------------------------------------------
# Sport / activites physiques
# --------------------------------------------------------------------------

# Activites qui ont une distance (donc une allure calculable).
DISTANCE_ACTIVITIES = ("marche", "course", "velo", "vélo", "natation", "rando",
                       "randonnee", "randonnée")

# Libelles normalises -> affichage. Permet d'accepter des variantes.
ACTIVITY_ALIASES = {
    "run": "course", "running": "course", "cap": "course",
    "bike": "velo", "cyclisme": "velo", "vtt": "velo",
    "walk": "marche", "walking": "marche",
    "muscu": "musculation", "renfo": "musculation", "gym": "musculation",
    "swim": "natation", "nage": "natation",
    "hike": "randonnee", "rando": "randonnee", "randonnée": "randonnee",
}


def normalize_activity(name: str) -> str:
    n = name.strip().lower()
    return ACTIVITY_ALIASES.get(n, n)


def activity_has_distance(activity: str) -> bool:
    return normalize_activity(activity) in (
        normalize_activity(a) for a in DISTANCE_ACTIVITIES
    )


def add_sport(activity: str, duration_min: float | None = None,
              distance_km: float | None = None, calories: float | None = None,
              hr_avg: float | None = None, effort: float | None = None,
              date: str | None = None, body: str | None = None,
              tags: Iterable[str] | None = None) -> int:
    """
    Enregistre une activite sportive. Les valeurs chiffrees sont stockees
    comme metriques (donc requetables comme le poids ou l'humeur).
      duration_min : minutes
      distance_km  : kilometres (pour marche/course/velo/...)
      calories     : kcal brulees
      hr_avg       : frequence cardiaque moyenne (bpm)
      effort       : ressenti d'effort, echelle libre (ex: 1-10)
    L'allure et la vitesse ne sont PAS stockees : calculees a l'affichage.
    """
    from datetime import date as _date
    activity = normalize_activity(activity)
    metrics: dict[str, Any] = {}
    if duration_min is not None:
        metrics["duree"] = (float(duration_min), "min")
    if distance_km is not None:
        metrics["distance"] = (float(distance_km), "km")
    if calories is not None:
        metrics["calories"] = (float(calories), "kcal")
    if hr_avg is not None:
        metrics["fc_moy"] = (float(hr_avg), "bpm")
    if effort is not None:
        metrics["effort"] = float(effort)
    return add_entry(
        type="sport",
        title=activity,
        body=body,
        date=date or _date.today().isoformat(),
        tags=tags,
        metrics=metrics or None,
    )


def _sport_view(entry: dict) -> dict:
    """
    Enrichit une entree sport avec les valeurs derivees (allure, vitesse).
    Renvoie un dict pret a afficher.
    """
    m = entry.get("metrics", {})
    duration = m.get("duree", {}).get("value")
    distance = m.get("distance", {}).get("value")
    view = {
        "id": entry["id"],
        "date": entry.get("date"),
        "activity": entry.get("title") or "",
        "duration": duration,
        "distance": distance,
        "calories": m.get("calories", {}).get("value"),
        "hr_avg": m.get("fc_moy", {}).get("value"),
        "effort": m.get("effort", {}).get("value"),
        "tags": entry.get("tags", []),
        "body": entry.get("body"),
        "pace": None,       # min/km (texte mm:ss)
        "pace_seconds": None,
        "speed": None,      # km/h
    }
    if duration and distance and distance > 0:
        pace_min_per_km = duration / distance
        total_seconds = int(round(pace_min_per_km * 60))
        mm, ss = divmod(total_seconds, 60)
        view["pace"] = f"{mm}:{ss:02d}"
        view["pace_seconds"] = total_seconds
        view["speed"] = round(distance / (duration / 60.0), 2)
    return view


def get_sport(entry_id: int) -> dict | None:
    entry = get_entry(entry_id)
    if not entry or entry["type"] != "sport":
        return None
    return _sport_view(entry)


def list_sport(activity: str | None = None, since: str | None = None,
               until: str | None = None, tag: str | None = None) -> list[dict]:
    """Liste des activites, enrichies avec allure/vitesse, triees par date."""
    entries = list_entries(type="sport", tag=tag, since=since, until=until)
    views = [_sport_view(e) for e in entries]
    if activity:
        act = normalize_activity(activity)
        views = [v for v in views if normalize_activity(v["activity"]) == act]
    return views


def update_sport(entry_id: int, activity: str | None = None,
                 duration_min: float | None = None,
                 distance_km: float | None = None, calories: float | None = None,
                 hr_avg: float | None = None, effort: float | None = None,
                 date: str | None = None, tags: Iterable[str] | None = None,
                 body: str | None = None) -> bool:
    """Modifie une activite. Seuls les champs fournis sont touches."""
    entry = get_entry(entry_id)
    if not entry or entry["type"] != "sport":
        return False
    metrics: dict[str, Any] = {}
    if duration_min is not None:
        metrics["duree"] = (float(duration_min), "min")
    if distance_km is not None:
        metrics["distance"] = (float(distance_km), "km")
    if calories is not None:
        metrics["calories"] = (float(calories), "kcal")
    if hr_avg is not None:
        metrics["fc_moy"] = (float(hr_avg), "bpm")
    if effort is not None:
        metrics["effort"] = float(effort)
    return update_entry(
        entry_id,
        title=normalize_activity(activity) if activity else None,
        body=body,
        date=date,
        tags=tags,
        metrics=metrics or None,
    )


def delete_sport(entry_id: int) -> bool:
    entry = get_entry(entry_id)
    if not entry or entry["type"] != "sport":
        return False
    delete_entry(entry_id)
    return True


def sport_summary(since: str | None = None, until: str | None = None) -> dict:
    """
    Bilan agrege par type d'activite sur la periode :
      {activite: {count, total_duration, total_distance, total_calories,
                  avg_pace_seconds}}.
    """
    views = list_sport(since=since, until=until)
    summary: dict[str, dict] = {}
    for v in views:
        act = normalize_activity(v["activity"])
        s = summary.setdefault(act, {
            "count": 0, "total_duration": 0.0, "total_distance": 0.0,
            "total_calories": 0.0, "_pace_secs": [],
        })
        s["count"] += 1
        s["total_duration"] += v["duration"] or 0.0
        s["total_distance"] += v["distance"] or 0.0
        s["total_calories"] += v["calories"] or 0.0
        if v["pace_seconds"]:
            s["_pace_secs"].append(v["pace_seconds"])
    # moyenne d'allure
    for s in summary.values():
        secs = s.pop("_pace_secs")
        if secs:
            avg = int(round(sum(secs) / len(secs)))
            mm, ss = divmod(avg, 60)
            s["avg_pace"] = f"{mm}:{ss:02d}"
        else:
            s["avg_pace"] = None
        s["total_duration"] = round(s["total_duration"], 1)
        s["total_distance"] = round(s["total_distance"], 2)
        s["total_calories"] = round(s["total_calories"], 0)
    return summary


# --------------------------------------------------------------------------
# Nourriture : saisie directe (pas de bibliotheque)
# --------------------------------------------------------------------------
# On enregistre directement ce qu'on mange avec ses valeurs nutritionnelles
# deja totalisees. La quantite (--qte) est purement DESCRIPTIVE : elle est
# notee pour memoire mais n'entre dans aucun calcul. L'app additionne
# simplement les valeurs saisies pour donner le total du jour.

# Les nutriments suivis. Cle interne -> (libelle, unite).
NUTRIENTS = {
    "kcal": ("Calories", "kcal"),
    "protein": ("Protéines", "g"),
    "carbs": ("Glucides", "g"),
    "fat_sat": ("Lipides saturés", "g"),
    "fat_unsat": ("Lipides insaturés", "g"),
    "fiber": ("Fibres", "g"),
}


def add_food(label: str | None = None, qty: str | None = None,
             kcal: float | None = None, protein: float | None = None,
             carbs: float | None = None, fat_sat: float | None = None,
             fat_unsat: float | None = None, fiber: float | None = None,
             date: str | None = None, meal: str | None = None,
             tags: Iterable[str] | None = None) -> int:
    """
    Enregistre une consommation en saisie directe.
      label : nom libre de l'aliment (optionnel)
      qty   : quantite DESCRIPTIVE (texte libre, ex: "150 g", "1 bol") - non calculee
      les nutriments sont les totaux reels de ce qui a ete mange.
    Toutes les valeurs nutritionnelles sont optionnelles.
    """
    from datetime import date as _date
    metrics: dict[str, Any] = {}
    for key, val in (("kcal", kcal), ("protein", protein), ("carbs", carbs),
                     ("fat_sat", fat_sat), ("fat_unsat", fat_unsat),
                     ("fiber", fiber)):
        if val is not None:
            metrics[key] = float(val)
    tag_list = list(tags) if tags else []
    if meal:
        tag_list.append(meal.strip().lower())
    return add_entry(
        type="food",
        title=label,
        body=qty,           # la quantite descriptive vit dans body
        date=date or _date.today().isoformat(),
        tags=tag_list or None,
        metrics=metrics or None,
    )


def _food_view(entry: dict) -> dict:
    """Vue d'une consommation : valeurs telles que saisies (aucun calcul)."""
    m = entry.get("metrics", {})
    nutrients = {k: m.get(k, {}).get("value", 0) for k in NUTRIENTS}
    return {
        "id": entry["id"],
        "date": entry.get("date"),
        "label": entry.get("title") or "",
        "qty": entry.get("body") or "",
        "nutrients": nutrients,
        "tags": entry.get("tags", []),
    }


def list_food_log(date: str | None = None, since: str | None = None,
                  until: str | None = None, tag: str | None = None) -> list[dict]:
    """Journal alimentaire (valeurs telles que saisies)."""
    if date:
        since = until = date
    entries = list_entries(type="food", tag=tag, since=since, until=until)
    return [_food_view(e) for e in entries]


def food_day_totals(date: str) -> dict:
    """Totaux nutritionnels d'une journee : somme simple des valeurs saisies."""
    logs = list_food_log(date=date)
    totals = {k: 0.0 for k in NUTRIENTS}
    for log in logs:
        for k in NUTRIENTS:
            totals[k] += log["nutrients"].get(k, 0)
    return {k: round(v, 1) for k, v in totals.items()}


def update_food(entry_id: int, label: str | None = None, qty: str | None = None,
                kcal: float | None = None, protein: float | None = None,
                carbs: float | None = None, fat_sat: float | None = None,
                fat_unsat: float | None = None, fiber: float | None = None,
                date: str | None = None, tags: Iterable[str] | None = None) -> bool:
    entry = get_entry(entry_id)
    if not entry or entry["type"] != "food":
        return False
    metrics: dict[str, Any] = {}
    for key, val in (("kcal", kcal), ("protein", protein), ("carbs", carbs),
                     ("fat_sat", fat_sat), ("fat_unsat", fat_unsat),
                     ("fiber", fiber)):
        if val is not None:
            metrics[key] = float(val)
    return update_entry(entry_id, title=label, body=qty, date=date,
                        tags=tags, metrics=metrics or None)


def delete_food(entry_id: int) -> bool:
    entry = get_entry(entry_id)
    if not entry or entry["type"] != "food":
        return False
    delete_entry(entry_id)
    return True


# ==========================================================================
# Module Depenses : codes de taxe, categories, depenses
# ==========================================================================

def seed_default_tax_codes() -> None:
    """Cree le code Quebec (TPS 5% + TVQ 9.975%) par defaut s'il n'existe rien."""
    with get_connection() as conn:
        n = conn.execute("SELECT COUNT(*) AS c FROM tax_codes").fetchone()["c"]
        if n:
            return
    qc = add_tax_code("Québec", [("TPS", 5.0), ("TVQ", 9.975)], is_default=True)


# ---- Codes de taxe -------------------------------------------------------

def add_tax_code(name: str, lines: list[tuple] | None = None,
                 is_default: bool = False) -> int:
    """
    Cree un code de taxe. lines = [(nom, taux), ...] en pourcentage.
    Si is_default, retire le defaut des autres codes.
    """
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        if is_default:
            conn.execute("UPDATE tax_codes SET is_default = 0")
        cur = conn.execute(
            "INSERT INTO tax_codes(name, is_default, created_at) VALUES (?, ?, ?)",
            (name.strip(), 1 if is_default else 0, now))
        code_id = cur.lastrowid
        for i, (lname, rate) in enumerate(lines or []):
            conn.execute(
                "INSERT INTO tax_lines(tax_code_id, name, rate, position) "
                "VALUES (?, ?, ?, ?)", (code_id, lname.strip(), float(rate), i))
    return code_id


def update_tax_code(code_id: int, name: str | None = None,
                    lines: list[tuple] | None = None,
                    is_default: bool | None = None) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM tax_codes WHERE id = ?",
                           (code_id,)).fetchone()
        if not row:
            return False
        if name is not None:
            conn.execute("UPDATE tax_codes SET name = ? WHERE id = ?",
                         (name.strip(), code_id))
        if is_default is not None:
            if is_default:
                conn.execute("UPDATE tax_codes SET is_default = 0")
            conn.execute("UPDATE tax_codes SET is_default = ? WHERE id = ?",
                         (1 if is_default else 0, code_id))
        if lines is not None:
            conn.execute("DELETE FROM tax_lines WHERE tax_code_id = ?", (code_id,))
            for i, (lname, rate) in enumerate(lines):
                conn.execute(
                    "INSERT INTO tax_lines(tax_code_id, name, rate, position) "
                    "VALUES (?, ?, ?, ?)", (code_id, lname.strip(), float(rate), i))
    return True


def delete_tax_code(code_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM tax_codes WHERE id = ?", (code_id,))


def get_tax_code(code_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tax_codes WHERE id = ?",
                           (code_id,)).fetchone()
        if not row:
            return None
        code = dict(row)
        lines = conn.execute(
            "SELECT name, rate FROM tax_lines WHERE tax_code_id = ? "
            "ORDER BY position", (code_id,)).fetchall()
        code["lines"] = [{"name": l["name"], "rate": l["rate"]} for l in lines]
        return code


def list_tax_codes() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM tax_codes ORDER BY name").fetchall()
    return [get_tax_code(r["id"]) for r in rows]


def default_tax_code() -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM tax_codes WHERE is_default = 1 LIMIT 1").fetchone()
        if not row:
            row = conn.execute("SELECT id FROM tax_codes LIMIT 1").fetchone()
    return get_tax_code(row["id"]) if row else None


# ---- Categories de depenses ---------------------------------------------

def add_expense_category(name: str) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO expense_categories(name, created_at) VALUES (?, ?)",
                (name.strip(), now))
            return cur.lastrowid
        except sqlite3.IntegrityError:
            row = conn.execute("SELECT id FROM expense_categories WHERE name = ?",
                               (name.strip(),)).fetchone()
            return row["id"]


def list_expense_categories() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM expense_categories ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def update_expense_category(cat_id: int, name: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute("UPDATE expense_categories SET name = ? WHERE id = ?",
                           (name.strip(), cat_id))
        return cur.rowcount > 0


def delete_expense_category(cat_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM expense_categories WHERE id = ?", (cat_id,))


# ---- Calcul des taxes (bidirectionnel) ----------------------------------

def compute_taxes(amount_ht: float | None, amount_ttc: float | None,
                  tax_code: dict | None, no_tax: bool = False,
                  last_edited: str = "ht") -> dict:
    """
    Calcule HT, TTC, total taxes et le detail par taxe.
      - last_edited='ht'  : on part du HT et on calcule TTC.
      - last_edited='ttc' : on part du TTC et on remonte au HT.
    no_tax=True : taxes nulles, HT=TTC.
    Renvoie {amount_ht, amount_ttc, tax_total, detail:{nom:montant}}.
    """
    lines = [] if (no_tax or not tax_code) else tax_code.get("lines", [])
    rate_sum = sum(l["rate"] for l in lines) / 100.0  # ex: 0.14975

    def from_ht(ht):
        ht = round(float(ht), 2)
        detail = {l["name"]: round(ht * l["rate"] / 100.0, 2) for l in lines}
        tax_total = round(sum(detail.values()), 2)
        return ht, round(ht + tax_total, 2), tax_total, detail

    def from_ttc(ttc):
        ttc = round(float(ttc), 2)
        ht = round(ttc / (1.0 + rate_sum), 2) if rate_sum else ttc
        detail = {l["name"]: round(ht * l["rate"] / 100.0, 2) for l in lines}
        tax_total = round(sum(detail.values()), 2)
        # ajuste pour que ht + taxes == ttc exactement (arrondi)
        return ht, ttc, tax_total, detail

    if no_tax:
        base = amount_ht if last_edited == "ht" else amount_ttc
        base = round(float(base or 0), 2)
        return {"amount_ht": base, "amount_ttc": base, "tax_total": 0.0,
                "detail": {}}

    if last_edited == "ttc" and amount_ttc not in (None, ""):
        ht, ttc, tt, det = from_ttc(amount_ttc)
    else:
        ht, ttc, tt, det = from_ht(amount_ht or 0)
    return {"amount_ht": ht, "amount_ttc": ttc, "tax_total": tt, "detail": det}


# ---- Depenses ------------------------------------------------------------

def add_expense(date: str, label: str | None, category_id: int | None,
                tax_code_id: int | None, no_tax: bool,
                amount_ht: float, amount_ttc: float, tax_total: float,
                tax_detail: dict, tip: float = 0.0, currency: str = "CAD",
                amount_currency: float | None = None,
                is_personal: bool = True, op_type: str = "expense",
                third_party: str | None = None) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO expenses(date, label, category_id, tax_code_id, no_tax,
               amount_ht, amount_ttc, tax_total, tax_detail_json, tip, currency,
               amount_currency, is_personal, op_type, third_party, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (date, label, category_id, tax_code_id, 1 if no_tax else 0,
             amount_ht, amount_ttc, tax_total, json.dumps(tax_detail), tip,
             currency, amount_currency, 1 if is_personal else 0,
             op_type if op_type in ("expense", "income") else "expense",
             third_party, now))
        return cur.lastrowid


def update_expense(expense_id: int, **fields) -> bool:
    allowed = {"date", "label", "category_id", "tax_code_id", "no_tax",
               "amount_ht", "amount_ttc", "tax_total", "tip", "currency",
               "amount_currency", "is_personal", "op_type", "third_party"}
    bool_cols = {"no_tax", "is_personal"}
    sets, params = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k} = ?")
            params.append((1 if v else 0) if k in bool_cols else v)
        elif k == "tax_detail":
            sets.append("tax_detail_json = ?")
            params.append(json.dumps(v))
    if not sets:
        return False
    params.append(expense_id)
    with get_connection() as conn:
        cur = conn.execute(
            f"UPDATE expenses SET {', '.join(sets)} WHERE id = ?", params)
        return cur.rowcount > 0


def delete_expense(expense_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))


def _expense_view(row: dict) -> dict:
    d = dict(row)
    d["tax_detail"] = json.loads(d.pop("tax_detail_json") or "{}")
    d["no_tax"] = bool(d["no_tax"])
    d["is_personal"] = bool(d.get("is_personal", 1))
    d["op_type"] = d.get("op_type") or "expense"
    d["third_party"] = d.get("third_party") or ""
    return d


def get_expense(expense_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM expenses WHERE id = ?",
                           (expense_id,)).fetchone()
        return _expense_view(row) if row else None


def list_expenses(since: str | None = None, until: str | None = None,
                  category_id: int | None = None,
                  op_type: str | None = None) -> list[dict]:
    clauses, params = [], []
    if since:
        clauses.append("date >= ?"); params.append(since)
    if until:
        clauses.append("date <= ?"); params.append(until)
    if category_id is not None:
        clauses.append("category_id = ?"); params.append(category_id)
    if op_type in ("expense", "income"):
        clauses.append("op_type = ?"); params.append(op_type)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM expenses {where} ORDER BY date DESC, id DESC",
            params).fetchall()
    return [_expense_view(r) for r in rows]
