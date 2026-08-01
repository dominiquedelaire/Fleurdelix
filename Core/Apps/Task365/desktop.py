"""
Interface desktop de task365 (DearPyGui).

Premiere version : tableau de bord du JOUR. Navigation par date, avec
panneaux taches / journal / sport / alimentation / soldes de comptes.

Toute la logique vient de db.py — cette fenetre ne fait qu'afficher et
appeler les memes fonctions que le CLI et la TUI. Aucune duplication.

Lancement : task365 gui   (ou : python -m task365.desktop)

Dependance : pip install dearpygui
"""

from __future__ import annotations

from datetime import date, timedelta

try:
    import dearpygui.dearpygui as dpg
except ImportError as exc:
    raise SystemExit(
        "L'interface desktop nécessite DearPyGui.\n"
        "Installe-le avec : pip install dearpygui\n"
        f"(détail : {exc})"
    )

from . import db


# Etat applicatif minimal : la date affichee.
STATE = {"day": date.today()}

# Couleurs (thème sombre épuré)
COL_GREEN = (120, 200, 140)
COL_RED = (220, 120, 120)
COL_YELLOW = (220, 200, 120)
COL_CYAN = (120, 190, 210)
COL_MUTED = (140, 140, 150)


def _day_iso() -> str:
    return STATE["day"].isoformat()


# --------------------------------------------------------------------------
# Rafraichissement des panneaux
# --------------------------------------------------------------------------

def refresh_all() -> None:
    db.run_recurrences()  # genere les entrees recurrentes dues
    _set_date_label()
    _refresh_tasks()
    _refresh_journal()
    _refresh_sport()
    _refresh_food()
    _refresh_accounts()


def _set_date_label() -> None:
    d = STATE["day"]
    human = d.strftime("%A %d %B %Y")
    suffix = "  (aujourd'hui)" if d == date.today() else ""
    dpg.set_value("date_label", human + suffix)


def _clear(container: str) -> None:
    """Vide un conteneur de ses enfants."""
    for child in dpg.get_item_children(container, slot=1) or []:
        dpg.delete_item(child)


def _refresh_tasks() -> None:
    _clear("tasks_box")
    tasks = [e for e in db.entries_on_day(_day_iso()) if e["type"] == "task"]
    if not tasks:
        dpg.add_text("Aucune tâche.", parent="tasks_box", color=COL_MUTED)
        return
    for t in tasks:
        with dpg.group(horizontal=True, parent="tasks_box"):
            dpg.add_checkbox(
                default_value=bool(t["done"]),
                callback=_make_toggle(t["id"]),
            )
            label = t.get("title") or ""
            tags = "  " + " ".join(f"#{x}" for x in t["tags"]) if t["tags"] else ""
            dpg.add_text(label + tags,
                         color=COL_MUTED if t["done"] else (230, 230, 235))


def _make_toggle(task_id: int):
    def _cb(sender, value):
        db.set_done(task_id, value)
    return _cb


def _refresh_journal() -> None:
    _clear("journal_box")
    entries = [e for e in db.entries_on_day(_day_iso()) if e["type"] == "journal"]
    if not entries:
        dpg.add_text("Aucune entrée de journal.", parent="journal_box",
                     color=COL_MUTED)
        return
    for e in entries:
        mood = e["metrics"].get("humeur", {}).get("value")
        if mood is not None:
            dpg.add_text(f"Humeur : {mood:g}/10", parent="journal_box",
                         color=COL_GREEN)
        metrics = "   ".join(
            f"{n} {i['value']:g}" for n, i in e["metrics"].items() if n != "humeur"
        )
        if metrics:
            dpg.add_text(metrics, parent="journal_box", color=COL_CYAN)
        dpg.add_text(e.get("body") or "", parent="journal_box", wrap=420)
        if e["tags"]:
            dpg.add_text(" ".join(f"#{x}" for x in e["tags"]),
                         parent="journal_box", color=COL_MUTED)
        dpg.add_separator(parent="journal_box")


def _refresh_sport() -> None:
    _clear("sport_box")
    acts = db.list_sport(since=_day_iso(), until=_day_iso())
    if not acts:
        dpg.add_text("Aucune activité.", parent="sport_box", color=COL_MUTED)
        return
    for a in acts:
        parts = [a["activity"]]
        if a["duration"]:
            parts.append(f"{a['duration']:g} min")
        if a["distance"]:
            parts.append(f"{a['distance']:g} km")
        if a["pace"]:
            parts.append(f"{a['pace']}/km")
        if a["calories"]:
            parts.append(f"{a['calories']:g} kcal")
        dpg.add_text("  ·  ".join(parts), parent="sport_box")


def _refresh_food() -> None:
    _clear("food_box")
    logs = db.list_food_log(date=_day_iso())
    if not logs:
        dpg.add_text("Rien de consommé.", parent="food_box", color=COL_MUTED)
        return
    for l in logs:
        n = l["nutrients"]
        label = l["label"] or "(sans nom)"
        qty = f"  {l['qty']}" if l["qty"] else ""
        dpg.add_text(f"{label}{qty}   {n['kcal']:g} kcal", parent="food_box")
    # total du jour, tous nutriments
    t = db.food_day_totals(_day_iso())
    dpg.add_separator(parent="food_box")
    dpg.add_text(
        f"Total : {t['kcal']:g} kcal   P {t['protein']:g}g   "
        f"G {t['carbs']:g}g   F {t['fiber']:g}g",
        parent="food_box", color=COL_YELLOW,
    )
    dpg.add_text(
        f"Lipides — saturés {t['fat_sat']:g}g · insaturés {t['fat_unsat']:g}g",
        parent="food_box", color=COL_MUTED,
    )


def _refresh_accounts() -> None:
    _clear("accounts_box")
    accounts = db.list_accounts()
    if not accounts:
        dpg.add_text("Aucun compte.", parent="accounts_box", color=COL_MUTED)
        return
    total = 0.0
    for a in accounts:
        bal = db.balance_at(a["id"], _day_iso())
        total += bal
        with dpg.group(horizontal=True, parent="accounts_box"):
            dpg.add_text(f"{a['name']} :")
            dpg.add_text(f"{bal:.2f}",
                         color=COL_GREEN if bal >= 0 else COL_RED)
    dpg.add_separator(parent="accounts_box")
    with dpg.group(horizontal=True, parent="accounts_box"):
        dpg.add_text("Total :")
        dpg.add_text(f"{round(total,2):.2f}",
                     color=COL_GREEN if total >= 0 else COL_RED)


# --------------------------------------------------------------------------
# Navigation de date
# --------------------------------------------------------------------------

def _shift_day(days: int):
    def _cb():
        STATE["day"] = STATE["day"] + timedelta(days=days)
        refresh_all()
    return _cb


def _go_today():
    STATE["day"] = date.today()
    refresh_all()


# --------------------------------------------------------------------------
# Construction de l'interface
# --------------------------------------------------------------------------

def build() -> None:
    dpg.create_context()

    with dpg.window(tag="root"):
        # Barre de navigation de date
        with dpg.group(horizontal=True):
            dpg.add_button(label="<< -7j", callback=_shift_day(-7))
            dpg.add_button(label="< -1j", callback=_shift_day(-1))
            dpg.add_button(label="Aujourd'hui", callback=lambda: _go_today())
            dpg.add_button(label="+1j >", callback=_shift_day(1))
            dpg.add_button(label="+7j >>", callback=_shift_day(7))
            dpg.add_button(label="Rafraîchir", callback=lambda: refresh_all())
        dpg.add_text("", tag="date_label", color=COL_CYAN)
        dpg.add_separator()

        # Deux colonnes : gauche (tâches/journal/sport/food), droite (soldes)
        with dpg.group(horizontal=True):
            with dpg.child_window(width=470, autosize_y=True):
                dpg.add_text("Tâches", color=COL_YELLOW)
                with dpg.group(tag="tasks_box"):
                    pass
                dpg.add_spacer(height=8)
                dpg.add_text("Journal", color=COL_YELLOW)
                with dpg.group(tag="journal_box"):
                    pass
                dpg.add_spacer(height=8)
                dpg.add_text("Sport", color=COL_YELLOW)
                with dpg.group(tag="sport_box"):
                    pass
                dpg.add_spacer(height=8)
                dpg.add_text("Alimentation", color=COL_YELLOW)
                with dpg.group(tag="food_box"):
                    pass
            with dpg.child_window(width=260, autosize_y=True):
                dpg.add_text("Comptes & soldes", color=COL_YELLOW)
                dpg.add_text("(à la date affichée)", color=COL_MUTED)
                with dpg.group(tag="accounts_box"):
                    pass

    dpg.create_viewport(title="task365", width=780, height=640)
    dpg.setup_dearpygui()
    dpg.set_primary_window("root", True)
    refresh_all()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()


def run() -> None:
    db.init_db()
    build()


if __name__ == "__main__":
    run()
