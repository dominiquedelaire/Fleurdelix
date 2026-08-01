"""
Couche d'affichage basee sur Rich.
On garde tout le "beau rendu" ici pour que la logique reste neutre.
"""

from __future__ import annotations

from datetime import datetime, date

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()

# Echelle d'humeur -> petite jauge visuelle simple.
MOOD_FACES = {
    range(0, 3): ("😞", "red"),
    range(3, 5): ("😕", "yellow"),
    range(5, 7): ("😐", "white"),
    range(7, 9): ("🙂", "green"),
    range(9, 11): ("😄", "bright_green"),
}


def _mood_label(value: float | None) -> Text:
    if value is None:
        return Text("—", style="dim")
    for rng, (face, color) in MOOD_FACES.items():
        if int(value) in rng:
            return Text(f"{face} {value:g}/10", style=color)
    return Text(f"{value:g}/10")


def _fmt_tags(tags: list[str]) -> Text:
    if not tags:
        return Text("")
    t = Text()
    for i, tag in enumerate(tags):
        if i:
            t.append(" ")
        t.append(f"#{tag}", style="cyan")
    return t


def _fmt_metrics(metrics: dict) -> Text:
    t = Text()
    for i, (name, info) in enumerate(metrics.items()):
        if name == "humeur":
            continue
        if i:
            t.append("  ")
        unit = info.get("unit") or ""
        t.append(f"{name}: ", style="dim")
        t.append(f"{info['value']:g}{unit}", style="magenta")
    return t


def _days_until(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        d = datetime.fromisoformat(iso).date() if "T" in iso else date.fromisoformat(iso[:10])
    except ValueError:
        return iso
    delta = (d - date.today()).days
    if delta == 0:
        return "aujourd'hui"
    if delta == 1:
        return "demain"
    if delta == -1:
        return "hier"
    if delta < 0:
        return f"il y a {abs(delta)} j"
    return f"dans {delta} j"


def render_tasks(tasks: list[dict], title: str = "Tâches") -> None:
    if not tasks:
        console.print(f"[dim]Aucune tâche.[/dim]")
        return
    table = Table(title=title, box=box.ROUNDED, title_style="bold")
    table.add_column("#", style="dim", justify="right")
    table.add_column("", width=2)  # statut
    table.add_column("Tâche")
    table.add_column("Échéance")
    table.add_column("Tags")
    for t in tasks:
        check = "[green]✓[/green]" if t["done"] else "[yellow]○[/yellow]"
        due = t.get("date") or ""
        due_txt = f"{due}  [dim]({_days_until(due)})[/dim]" if due else "[dim]—[/dim]"
        style = "dim strike" if t["done"] else ""
        table.add_row(
            str(t["id"]), check,
            Text(t.get("title") or "", style=style),
            due_txt, _fmt_tags(t["tags"]),
        )
    console.print(table)


def render_journal(entries: list[dict], title: str = "Journal de bord") -> None:
    if not entries:
        console.print("[dim]Aucune entrée de journal.[/dim]")
        return
    for e in reversed(entries):  # plus recent en haut
        when = e.get("date") or e["created_at"][:10]
        mood = e["metrics"].get("humeur", {}).get("value")
        header = Text()
        header.append(f"#{e['id']}  ", style="dim")
        header.append(when, style="bold")
        header.append("   ")
        header.append_text(_mood_label(mood))
        body = Text(e.get("body") or "", style="white")
        footer = Text()
        footer.append_text(_fmt_metrics(e["metrics"]))
        if e["tags"]:
            footer.append("   ")
            footer.append_text(_fmt_tags(e["tags"]))
        content = Text()
        content.append_text(body)
        if str(footer):
            content.append("\n\n")
            content.append_text(footer)
        console.print(Panel(content, title=header, title_align="left",
                            box=box.ROUNDED, border_style="blue"))


def render_contacts(contacts: list[dict]) -> None:
    if not contacts:
        console.print("[dim]Aucun contact.[/dim]")
        return
    table = Table(title="Contacts", box=box.ROUNDED, title_style="bold")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Nom", style="bold")
    table.add_column("Infos")
    table.add_column("Tags")
    for c in contacts:
        table.add_row(str(c["id"]), c.get("title") or "",
                      c.get("body") or "", _fmt_tags(c["tags"]))
    console.print(table)


def render_contact_detail(contact: dict, notes: list[dict]) -> None:
    head = Text()
    head.append(contact.get("title") or "", style="bold")
    if contact["tags"]:
        head.append("  ")
        head.append_text(_fmt_tags(contact["tags"]))
    console.print(Panel(contact.get("body") or "[dim]—[/dim]",
                        title=head, title_align="left", border_style="green"))
    if notes:
        console.print("[bold]Notes :[/bold]")
        for n in notes:
            when = n.get("date") or n["created_at"][:10]
            console.print(f"  [dim]{when} (#{n['id']})[/dim]  {n.get('body') or ''}")
    else:
        console.print("[dim]Aucune note pour ce contact.[/dim]")


def render_dashboard(upcoming: list[dict], recent_journal: list[dict],
                     weight_hist: list[dict], tag_counts: list[tuple]) -> None:
    console.rule("[bold]task365 — tableau de bord[/bold]")

    # Prochaines activites
    if upcoming:
        table = Table(title="Prochaines activités", box=box.SIMPLE, title_style="bold")
        table.add_column("Quand")
        table.add_column("Tâche")
        table.add_column("Tags")
        for t in upcoming:
            due = t.get("date") or ""
            table.add_row(f"{due} [dim]({_days_until(due)})[/dim]",
                          t.get("title") or "", _fmt_tags(t["tags"]))
        console.print(table)
    else:
        console.print("[dim]Aucune activité à venir.[/dim]")

    # Sparkline poids
    if len(weight_hist) >= 2:
        vals = [h["value"] for h in weight_hist]
        spark = _sparkline(vals)
        first, last = vals[0], vals[-1]
        trend = "▲" if last > first else ("▼" if last < first else "▬")
        color = "red" if last > first else "green" if last < first else "white"
        console.print(Panel(
            f"{spark}\n[dim]{vals[0]:g} → {vals[-1]:g}[/dim]  "
            f"[{color}]{trend} {last - first:+.1f}[/{color}]",
            title="Poids (évolution)", title_align="left",
            border_style="magenta", box=box.ROUNDED))

    # Derniere humeur
    if recent_journal:
        last = recent_journal[-1]
        mood = last["metrics"].get("humeur", {}).get("value")
        console.print(Text("Dernière humeur : ").append_text(_mood_label(mood)))

    # Tags
    if tag_counts:
        top = "  ".join(f"[cyan]#{n}[/cyan][dim]×{c}[/dim]" for n, c in tag_counts[:8])
        console.print(f"[bold]Tags :[/bold] {top}")


def render_search_results(results: list[dict], term: str) -> None:
    if not results:
        console.print(f"[dim]Aucun résultat pour « {term} ».[/dim]")
        return
    type_labels = {"task": "Tâche", "journal": "Journal", "contact": "Contact",
                   "note": "Note", "recurrence": "Récurrence"}
    type_colors = {"task": "yellow", "journal": "blue", "contact": "green",
                   "note": "white", "recurrence": "magenta"}
    table = Table(title=f"Résultats pour « {term} »", box=box.ROUNDED,
                  title_style="bold")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Type")
    table.add_column("Contenu")
    table.add_column("Date")
    table.add_column("Trouvé via", style="dim")
    for e in results:
        label = type_labels.get(e["type"], e["type"])
        color = type_colors.get(e["type"], "white")
        content = e.get("title") or e.get("body") or ""
        if len(content) > 50:
            content = content[:47] + "…"
        when = e.get("date") or e["created_at"][:10]
        if e["metrics"]:
            mtxt = " ".join(f"{n}={i['value']:g}" for n, i in e["metrics"].items())
            content = f"{content}  [magenta dim]{mtxt}[/magenta dim]"
        table.add_row(str(e["id"]), f"[{color}]{label}[/{color}]",
                      content, when, ", ".join(e["match"]))
    console.print(table)


def render_recurrences(recs: list[dict]) -> None:
    if not recs:
        console.print("[dim]Aucune récurrence définie.[/dim]")
        return
    freq_fr = {"daily": "quotidien", "weekly": "hebdo", "monthly": "mensuel"}
    table = Table(title="Récurrences", box=box.ROUNDED, title_style="bold")
    table.add_column("#", style="dim", justify="right")
    table.add_column("", width=2)
    table.add_column("Intitulé")
    table.add_column("Fréquence")
    table.add_column("Depuis")
    table.add_column("Dernière génération")
    table.add_column("Tags")
    for r in recs:
        active = "[green]●[/green]" if r["active"] else "[dim]○[/dim]"
        freq = freq_fr.get(r["freq"], r["freq"])
        if r["interval"] > 1:
            freq = f"tous les {r['interval']} ({freq})"
        table.add_row(str(r["id"]), active, r["title"], freq,
                      r["start"], r.get("last_run") or "[dim]jamais[/dim]",
                      _fmt_tags(r["tags"]))
    console.print(table)


def _sparkline(values: list[float]) -> str:
    """Mini graphe ASCII avec les blocs unicode."""
    blocks = "▁▂▃▄▅▆▇█"
    lo, hi = min(values), max(values)
    if hi == lo:
        return blocks[3] * len(values)
    out = []
    for v in values:
        idx = round((v - lo) / (hi - lo) * (len(blocks) - 1))
        out.append(blocks[idx])
    return "".join(out)


def _money(value: float) -> Text:
    """Montant colore : vert si positif, rouge si negatif."""
    color = "green" if value > 0 else ("red" if value < 0 else "white")
    sign = "+" if value > 0 else ""
    return Text(f"{sign}{value:.2f}", style=color)


def render_accounts(accounts: list[dict], balances: dict[int, float]) -> None:
    if not accounts:
        console.print("[dim]Aucun compte. Crée-en un avec : task365 account add[/dim]")
        return
    table = Table(title="Comptes", box=box.ROUNDED, title_style="bold")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Compte", style="bold")
    table.add_column("Solde initial", justify="right")
    table.add_column("Depuis")
    table.add_column("Solde actuel", justify="right")
    total = 0.0
    for a in accounts:
        bal = balances.get(a["id"], 0.0)
        total += bal
        table.add_row(str(a["id"]), a["name"],
                      f"{a['initial_balance']:.2f}", a.get("opened_on") or "",
                      _money(bal))
    table.add_section()
    table.add_row("", "[bold]Total[/bold]", "", "", _money(round(total, 2)))
    console.print(table)


def render_budget(ops: list[dict], title: str = "Opérations") -> None:
    if not ops:
        console.print("[dim]Aucune opération.[/dim]")
        return
    table = Table(title=title, box=box.ROUNDED, title_style="bold")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Date")
    table.add_column("Libellé")
    table.add_column("Catégorie", style="cyan")
    table.add_column("Montant", justify="right")
    total = 0.0
    for op in ops:
        amt = op["amount"] or 0.0
        total += amt
        cats = " ".join(f"#{t}" for t in op["tags"]) or "[dim]—[/dim]"
        table.add_row(str(op["id"]), (op["date"] or "")[:10],
                      op.get("title") or "", cats, _money(amt))
    table.add_section()
    table.add_row("", "", "", "[bold]Solde des opérations[/bold]",
                  _money(round(total, 2)))
    console.print(table)


def render_balance_series(name: str, series: list[dict]) -> None:
    if not series:
        console.print(f"[dim]Aucune opération pour « {name} ».[/dim]")
        return
    vals = [s["balance"] for s in series]
    table = Table(title=f"Évolution du solde — {name}", box=box.ROUNDED,
                  title_style="bold")
    table.add_column("Date")
    table.add_column("Mouvement", justify="right")
    table.add_column("Solde", justify="right")
    for s in series:
        table.add_row(s["date"], _money(s["delta"]),
                      Text(f"{s['balance']:.2f}", style="bold"))
    console.print(table)
    if len(vals) >= 2:
        console.print(f"[dim]{_sparkline(vals)}[/dim]")


def render_category_breakdown(rows: list[dict], title: str = "Par catégorie") -> None:
    if not rows:
        console.print("[dim]Aucune donnée.[/dim]")
        return
    table = Table(title=title, box=box.ROUNDED, title_style="bold")
    table.add_column("Catégorie", style="cyan")
    table.add_column("Opérations", justify="right", style="dim")
    table.add_column("Total", justify="right")
    depenses, revenus = 0.0, 0.0
    for r in rows:
        if r["total"] < 0:
            depenses += r["total"]
        else:
            revenus += r["total"]
        table.add_row(r["category"], str(r["count"]), _money(r["total"]))
    table.add_section()
    table.add_row("[bold]Dépenses[/bold]", "", _money(round(depenses, 2)))
    table.add_row("[bold]Revenus[/bold]", "", _money(round(revenus, 2)))
    table.add_row("[bold]Net[/bold]", "", _money(round(depenses + revenus, 2)))
    console.print(table)


# --- Sport ---------------------------------------------------------------

_ACTIVITY_ICONS = {
    "course": "🏃", "marche": "🚶", "velo": "🚴", "musculation": "🏋️",
    "natation": "🏊", "randonnee": "🥾",
}


def render_sport(activities: list[dict], title: str = "Activités sportives") -> None:
    if not activities:
        console.print("[dim]Aucune activité enregistrée.[/dim]")
        return
    table = Table(title=title, box=box.ROUNDED, title_style="bold")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Date")
    table.add_column("Activité")
    table.add_column("Durée", justify="right")
    table.add_column("Distance", justify="right")
    table.add_column("Allure", justify="right")
    table.add_column("Vitesse", justify="right")
    table.add_column("Cal", justify="right")
    table.add_column("FC", justify="right")
    table.add_column("Effort", justify="right")
    for a in activities:
        icon = _ACTIVITY_ICONS.get(a["activity"], "")
        dur = f"{a['duration']:g} min" if a["duration"] is not None else "—"
        dist = f"{a['distance']:g} km" if a["distance"] is not None else "—"
        pace = f"{a['pace']} /km" if a["pace"] else "—"
        speed = f"{a['speed']:g} km/h" if a["speed"] is not None else "—"
        cal = f"{a['calories']:g}" if a["calories"] is not None else "—"
        hr = f"{a['hr_avg']:g}" if a["hr_avg"] is not None else "—"
        eff = f"{a['effort']:g}/10" if a["effort"] is not None else "—"
        table.add_row(str(a["id"]), (a["date"] or "")[:10],
                      f"{icon} {a['activity']}".strip(),
                      dur, dist, pace, speed, cal, hr, eff)
    console.print(table)


def render_sport_summary(summary: dict, title: str = "Bilan sportif") -> None:
    if not summary:
        console.print("[dim]Aucune activité sur la période.[/dim]")
        return
    table = Table(title=title, box=box.ROUNDED, title_style="bold")
    table.add_column("Activité")
    table.add_column("Séances", justify="right")
    table.add_column("Durée totale", justify="right")
    table.add_column("Distance totale", justify="right")
    table.add_column("Calories", justify="right")
    table.add_column("Allure moy.", justify="right")
    tot_dur = tot_dist = tot_cal = 0.0
    for act, s in summary.items():
        icon = _ACTIVITY_ICONS.get(act, "")
        tot_dur += s["total_duration"]; tot_dist += s["total_distance"]
        tot_cal += s["total_calories"]
        dist = f"{s['total_distance']:g} km" if s["total_distance"] else "—"
        pace = f"{s['avg_pace']} /km" if s["avg_pace"] else "—"
        table.add_row(f"{icon} {act}".strip(), str(s["count"]),
                      f"{s['total_duration']:g} min", dist,
                      f"{s['total_calories']:g}", pace)
    table.add_section()
    table.add_row("[bold]Total[/bold]", "",
                  f"[bold]{round(tot_dur,1):g} min[/bold]",
                  f"[bold]{round(tot_dist,2):g} km[/bold]",
                  f"[bold]{round(tot_cal):g}[/bold]", "")
    console.print(table)


# --- Nourriture ----------------------------------------------------------



def render_food_day(date: str, logs: list[dict], totals: dict) -> None:
    if not logs:
        console.print(f"[dim]Rien de consommé le {date}.[/dim]")
        return
    table = Table(title=f"Journal alimentaire — {date}", box=box.ROUNDED,
                  title_style="bold")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Aliment", style="bold")
    table.add_column("Quantité", justify="right")
    table.add_column("kcal", justify="right")
    table.add_column("Prot", justify="right")
    table.add_column("Gluc", justify="right")
    table.add_column("Sat", justify="right")
    table.add_column("Insat", justify="right")
    table.add_column("Fibres", justify="right")
    table.add_column("Repas", style="cyan")
    for l in logs:
        n = l["nutrients"]
        meals = " ".join(f"#{t}" for t in l["tags"]) or ""
        table.add_row(
            str(l["id"]), l["label"] or "[dim]—[/dim]", l["qty"] or "—",
            f"{n['kcal']:g}", f"{n['protein']:g}", f"{n['carbs']:g}",
            f"{n['fat_sat']:g}", f"{n['fat_unsat']:g}", f"{n['fiber']:g}", meals)
    table.add_section()
    table.add_row("", "[bold]TOTAL[/bold]", "",
                  f"[bold]{totals['kcal']:g}[/bold]",
                  f"[bold]{totals['protein']:g}[/bold]",
                  f"[bold]{totals['carbs']:g}[/bold]",
                  f"[bold]{totals['fat_sat']:g}[/bold]",
                  f"[bold]{totals['fat_unsat']:g}[/bold]",
                  f"[bold]{totals['fiber']:g}[/bold]", "")
    console.print(table)
