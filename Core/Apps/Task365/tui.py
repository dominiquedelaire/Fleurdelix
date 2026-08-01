"""
Interface interactive de task365 (Textual).

Vue mixte : calendrier mensuel a gauche, details du jour selectionne a droite
(taches + journal de cette date). Navigation entierement au clavier.

Lancement : task365 tui

Cette interface ne fait que LIRE et AFFICHER via db.py ; elle ne duplique
aucune logique metier. Marquer une tache comme faite passe par db.set_done.

Touches :
  ←/→ ou h/l : jour precedent / suivant
  ↑/↓ ou k/j : semaine precedente / suivante
  PgUp/PgDn  : mois precedent / suivant
  t          : revenir a aujourd'hui
  n / p      : tache suivante / precedente (curseur dans la liste du jour)
  espace     : cocher/decocher la tache selectionnee du jour
  r          : rafraichir (relance les recurrences dues)
  q          : quitter
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta

try:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.widgets import Static, Header, Footer
    from textual.reactive import reactive
    from rich.text import Text
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
except ImportError as exc:  # message clair si Textual n'est pas installe
    raise SystemExit(
        "Le mode interactif nécessite Textual.\n"
        "Installe-le avec : pip install textual\n"
        f"(détail : {exc})"
    )

from . import db


FR_MONTHS = ["", "janvier", "février", "mars", "avril", "mai", "juin",
             "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
FR_DAYS = ["lu", "ma", "me", "je", "ve", "sa", "di"]


class CalendarPanel(Static):
    """Calendrier mensuel ; met en evidence aujourd'hui, le jour selectionne
    et les jours qui contiennent des entrees."""

    def __init__(self, app_ref: "Task365TUI") -> None:
        super().__init__()
        self.app_ref = app_ref

    def render(self):
        sel = self.app_ref.selected
        today = date.today()
        marked = self.app_ref.month_entries  # set de jours (str ISO) avec entrees

        table = Table.grid(padding=(0, 1))
        for _ in range(7):
            table.add_column(justify="center", width=3)
        table.add_row(*[Text(d, style="bold dim") for d in FR_DAYS])

        cal = calendar.Calendar(firstweekday=0)  # lundi
        week: list = []
        for day in cal.itermonthdates(sel.year, sel.month):
            if day.month != sel.month:
                week.append(Text(""))
            else:
                iso = day.isoformat()
                label = str(day.day)
                style = "white"
                if day == sel:
                    style = "bold black on cyan"
                elif day == today:
                    style = "bold yellow"
                elif iso in marked:
                    style = "bold green"
                cell = Text(label, style=style)
                if iso in marked and day != sel:
                    cell.append("•", style="green")
                week.append(cell)
            if len(week) == 7:
                table.add_row(*week)
                week = []
        if week:
            while len(week) < 7:
                week.append(Text(""))
            table.add_row(*week)

        title = Text(f"{FR_MONTHS[sel.month].capitalize()} {sel.year}",
                     style="bold")
        legend = Text("\n● aujourd'hui  ", style="yellow")
        legend.append("● jour sélectionné  ", style="cyan")
        legend.append("•vert = entrées", style="green")
        return Panel(table, title=title, subtitle=legend,
                     border_style="blue", box=box.ROUNDED)


class DayPanel(VerticalScroll):
    """Details du jour selectionne : taches puis journal."""

    def __init__(self, app_ref: "Task365TUI") -> None:
        super().__init__()
        self.app_ref = app_ref
        self.body = Static()

    def compose(self) -> ComposeResult:
        yield self.body

    def refresh_day(self) -> None:
        sel = self.app_ref.selected
        entries = db.entries_on_day(sel.isoformat())
        tasks = [e for e in entries if e["type"] == "task"]
        journals = [e for e in entries if e["type"] == "journal"]
        budgets = [e for e in entries if e["type"] == "budget"]
        sports = [e for e in entries if e["type"] == "sport"]
        foods = [e for e in entries if e["type"] == "food"]
        others = [e for e in entries
                  if e["type"] not in ("task", "journal", "budget", "sport", "food")]
        self.app_ref.day_tasks = tasks  # pour le toggle "espace"

        out = Text()
        human = sel.strftime("%A %d %B %Y")
        out.append(f"{human}\n", style="bold")
        if sel == date.today():
            out.append("(aujourd'hui)\n", style="yellow")
        out.append("\n")

        if not entries:
            out.append("Aucune entrée ce jour-là.\n", style="dim")

        if tasks:
            out.append("Tâches", style="bold underline")
            if len(tasks) > 1:
                out.append("   (n/p : changer · espace : cocher)", style="dim")
            out.append("\n")
            for i, t in enumerate(tasks):
                cursor = "›" if i == self.app_ref.task_cursor else " "
                check = "[x]" if t["done"] else "[ ]"
                style = "dim strike" if t["done"] else ""
                # surligne la ligne du curseur pour qu'elle soit bien visible
                prefix_style = "bold cyan" if i == self.app_ref.task_cursor else "cyan"
                line = Text(f"{cursor} {check} ", style=prefix_style)
                title_style = style
                if i == self.app_ref.task_cursor and not t["done"]:
                    title_style = "bold"
                line.append(t.get("title") or "", style=title_style)
                if t["tags"]:
                    line.append("  " + " ".join(f"#{tg}" for tg in t["tags"]),
                                style="cyan dim")
                out.append_text(line)
                out.append("\n")
            out.append("\n")

        if journals:
            out.append("Journal\n", style="bold underline")
            for j in journals:
                mood = j["metrics"].get("humeur", {}).get("value")
                if mood is not None:
                    out.append(f"humeur {mood:g}/10  ", style="green")
                metrics = " ".join(
                    f"{n}={i['value']:g}" for n, i in j["metrics"].items()
                    if n != "humeur"
                )
                if metrics:
                    out.append(metrics + "  ", style="magenta")
                out.append("\n")
                out.append((j.get("body") or "") + "\n", style="white")
                if j["tags"]:
                    out.append(" ".join(f"#{tg}" for tg in j["tags"]) + "\n",
                               style="cyan dim")
                out.append("\n")

        if budgets:
            out.append("Budget\n", style="bold underline")
            for b in budgets:
                amt = b["amount"] or 0.0
                color = "green" if amt > 0 else "red"
                sign = "+" if amt > 0 else ""
                line = Text(f"  {sign}{amt:.2f}  ", style=color)
                line.append(b.get("title") or "", style="white")
                cats = [t for t in b["tags"] if t != "virement"]
                if cats:
                    line.append("  " + " ".join(f"#{t}" for t in cats),
                                style="cyan dim")
                out.append_text(line)
                out.append("\n")
            out.append("\n")

        if sports:
            out.append("Sport\n", style="bold underline")
            for sp in sports:
                m = sp["metrics"]
                dur = m.get("duree", {}).get("value")
                dist = m.get("distance", {}).get("value")
                line = Text("  ")
                line.append(sp.get("title") or "", style="bold green")
                parts = []
                if dur:
                    parts.append(f"{dur:g} min")
                if dist:
                    parts.append(f"{dist:g} km")
                    if dur and dist > 0:
                        total = int(round((dur / dist) * 60))
                        mm, ss = divmod(total, 60)
                        parts.append(f"{mm}:{ss:02d}/km")
                if parts:
                    line.append("  " + " · ".join(parts), style="white")
                out.append_text(line)
                out.append("\n")
            out.append("\n")

        if foods:
            from . import db as _db
            out.append("Alimentation\n", style="bold underline")
            for f in foods:
                view = _db._food_view(f)
                n = view["nutrients"]
                line = Text("  ")
                line.append(view["label"] or "(sans nom)", style="white")
                if view["qty"]:
                    line.append(f"  {view['qty']}", style="dim")
                line.append(f"  {n['kcal']:g} kcal", style="yellow")
                out.append_text(line)
                out.append("\n")
            # total complet du jour (somme de tous les nutriments saisis)
            totals = _db.food_day_totals(sel.isoformat())
            out.append("  ── Total du jour ──\n", style="bold")
            tline = Text("  ")
            tline.append(f"{totals['kcal']:g} kcal", style="bold yellow")
            tline.append("   ")
            tline.append(f"P {totals['protein']:g} g", style="green")
            tline.append("   ")
            tline.append(f"G {totals['carbs']:g} g", style="cyan")
            tline.append("   ")
            tline.append(f"F {totals['fiber']:g} g", style="magenta")
            out.append_text(tline)
            out.append("\n")
            lline = Text("  ")
            lline.append(f"Lip. sat. {totals['fat_sat']:g} g", style="red")
            lline.append("   ")
            lline.append(f"Lip. insat. {totals['fat_unsat']:g} g", style="white")
            out.append_text(lline)
            out.append("\n\n")

        if others:
            out.append("Autres\n", style="bold underline")
            for o in others:
                out.append(f"[{o['type']}] {o.get('title') or o.get('body') or ''}\n")

        self.body.update(out)


class AccountsPanel(Static):
    """Soldes des comptes a la date selectionnee (projection si futur)."""

    def __init__(self, app_ref: "Task365TUI") -> None:
        super().__init__()
        self.app_ref = app_ref

    def render(self):
        sel = self.app_ref.selected
        accounts = db.list_accounts()
        if not accounts:
            return Panel(Text("Aucun compte.\ntask365 account add",
                              style="dim"),
                         title="Comptes", border_style="magenta", box=box.ROUNDED)
        table = Table.grid(padding=(0, 1))
        table.add_column(justify="left")
        table.add_column(justify="right")
        total = 0.0
        for a in accounts:
            bal = db.balance_at(a["id"], sel.isoformat())
            total += bal
            color = "green" if bal > 0 else ("red" if bal < 0 else "white")
            table.add_row(Text(a["name"], style="white"),
                          Text(f"{bal:.2f}", style=color))
        table.add_row(Text("─" * 10, style="dim"), Text("─" * 8, style="dim"))
        tcolor = "green" if total > 0 else ("red" if total < 0 else "white")
        table.add_row(Text("Total", style="bold"),
                      Text(f"{round(total,2):.2f}", style=f"bold {tcolor}"))
        when = "aujourd'hui" if sel == date.today() else sel.isoformat()
        return Panel(table, title="Comptes & soldes",
                     subtitle=Text(f"au {when}", style="dim"),
                     border_style="magenta", box=box.ROUNDED)


class Task365TUI(App):
    CSS = """
    Screen { layout: horizontal; }
    #left  { width: 38; }
    #right { width: 1fr; }
    """

    BINDINGS = [
        ("q", "quit", "Quitter"),
        ("left,h", "prev_day", "Jour -"),
        ("right,l", "next_day", "Jour +"),
        ("up,k", "prev_week", "Semaine -"),
        ("down,j", "next_week", "Semaine +"),
        ("pageup", "prev_month", "Mois -"),
        ("pagedown", "next_month", "Mois +"),
        ("t", "today", "Aujourd'hui"),
        ("space", "toggle_task", "Cocher tâche"),
        ("n", "next_task", "Tâche suiv."),
        ("p", "prev_task", "Tâche préc."),
        ("r", "refresh_all", "Rafraîchir"),
    ]

    selected: reactive[date] = reactive(date.today())

    def __init__(self) -> None:
        super().__init__()
        self.month_entries: set[str] = set()
        self.day_tasks: list = []
        self.task_cursor: int = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        self.cal_panel = CalendarPanel(self)
        self.acct_panel = AccountsPanel(self)
        self.day_panel = DayPanel(self)
        with Horizontal():
            with Vertical(id="left"):
                yield self.cal_panel
                yield self.acct_panel
            with Vertical(id="right"):
                yield self.day_panel
        yield Footer()

    def on_mount(self) -> None:
        db.run_recurrences()  # genere les entrees dues a l'ouverture
        self._reload_month()
        self._refresh_detail()

    # -- helpers --------------------------------------------------------
    def _refresh_detail(self) -> None:
        """Rafraichit le panneau du jour ET les soldes (toujours ensemble)."""
        self.day_panel.refresh_day()
        self.acct_panel.refresh()

    def _reload_month(self) -> None:
        g = db.entries_in_month(self.selected.year, self.selected.month)
        self.month_entries = set(g.keys())
        self.cal_panel.refresh()

    def _move(self, days: int) -> None:
        old_month = self.selected.month
        self.selected = self.selected + timedelta(days=days)
        self.task_cursor = 0
        if self.selected.month != old_month:
            self._reload_month()
        self.cal_panel.refresh()
        self._refresh_detail()

    # -- actions --------------------------------------------------------
    def action_prev_day(self) -> None: self._move(-1)
    def action_next_day(self) -> None: self._move(1)
    def action_prev_week(self) -> None: self._move(-7)
    def action_next_week(self) -> None: self._move(7)

    def action_prev_month(self) -> None:
        m, y = self.selected.month - 1, self.selected.year
        if m < 1:
            m, y = 12, y - 1
        day = min(self.selected.day, calendar.monthrange(y, m)[1])
        self.selected = date(y, m, day)
        self.task_cursor = 0
        self._reload_month()
        self._refresh_detail()

    def action_next_month(self) -> None:
        m, y = self.selected.month + 1, self.selected.year
        if m > 12:
            m, y = 1, y + 1
        day = min(self.selected.day, calendar.monthrange(y, m)[1])
        self.selected = date(y, m, day)
        self.task_cursor = 0
        self._reload_month()
        self._refresh_detail()

    def action_today(self) -> None:
        self.selected = date.today()
        self.task_cursor = 0
        self._reload_month()
        self._refresh_detail()

    def action_next_task(self) -> None:
        if self.day_tasks:
            self.task_cursor = (self.task_cursor + 1) % len(self.day_tasks)
            self._refresh_detail()

    def action_prev_task(self) -> None:
        if self.day_tasks:
            self.task_cursor = (self.task_cursor - 1) % len(self.day_tasks)
            self._refresh_detail()

    def action_toggle_task(self) -> None:
        if self.day_tasks and 0 <= self.task_cursor < len(self.day_tasks):
            t = self.day_tasks[self.task_cursor]
            db.set_done(t["id"], not t["done"])
            self._refresh_detail()

    def action_refresh_all(self) -> None:
        db.run_recurrences()
        self._reload_month()
        self._refresh_detail()


def run() -> None:
    db.init_db()
    Task365TUI().run()
