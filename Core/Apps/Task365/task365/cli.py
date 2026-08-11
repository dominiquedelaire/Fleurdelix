#!/usr/bin/env python3
"""
task365 — assistant personnel de données dans le terminal.

Usage rapide :
    task365 task add "Appeler le notaire" --due tomorrow --tags admin
    task365 task list
    task365 task done 3

    task365 journal add "Bonne journée, gros run ce matin" \\
        --mood 8 --metric poids=78.2 --metric sommeil=7:h --tags sport

    task365 journal list --tag sport

    task365 contact add "Marie Dupont" --info "Comptable, dispo le matin" --tags pro
    task365 contact note 4 "A relancé pour la facture de mai"
    task365 contact show 4

    task365 dashboard
    task365 tags
    task365 metric poids

La structure est volontairement decouplee : la CLI ne fait que parser
les arguments et appeler db + display. C'est ce qui permettra plus tard
de brancher une IA (qui appellera les memes fonctions de db) ou une
interface Textual sans rien reecrire.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

from . import db
from . import display
from .display import console
from .utils import parse_date, parse_tags, parse_metrics, extract_hashtags


# --------------------------------------------------------------------------
# Commandes : tâches
# --------------------------------------------------------------------------

def cmd_task_add(args) -> None:
    tags = parse_tags(args.tags) + extract_hashtags(args.title)
    metrics = parse_metrics(args.metric)
    entry_id = db.add_entry(
        type="task",
        title=args.title,
        date=parse_date(args.due),
        tags=tags or None,
        metrics=metrics or None,
    )
    console.print(f"[green]✓[/green] Tâche #{entry_id} créée.")


def cmd_task_list(args) -> None:
    done = None
    if args.done:
        done = True
    elif args.todo:
        done = False
    tasks = db.list_entries(type="task", tag=args.tag, done=done)
    display.render_tasks(tasks)


def cmd_task_done(args) -> None:
    db.set_done(args.id, True)
    console.print(f"[green]✓[/green] Tâche #{args.id} marquée comme faite.")


def cmd_task_edit(args) -> None:
    entry = db.get_entry(args.id)
    if not entry or entry["type"] != "task":
        console.print(f"[red]Aucune tâche #{args.id}.[/red]")
        return
    tags = parse_tags(args.tags) if args.tags is not None else None
    ok = db.update_entry(
        args.id,
        title=args.title,
        date=parse_date(args.due) if args.due else None,
        tags=tags,
    )
    if not ok:
        console.print(f"[red]Impossible de modifier la tâche #{args.id}.[/red]")
        return
    # gestion optionnelle du statut
    if args.done:
        db.set_done(args.id, True)
    elif args.todo:
        db.set_done(args.id, False)
    console.print(f"[green]✓[/green] Tâche #{args.id} modifiée.")


def cmd_task_rm(args) -> None:
    db.delete_entry(args.id)
    console.print(f"[red]✗[/red] Entrée #{args.id} supprimée.")


# --------------------------------------------------------------------------
# Commandes : journal
# --------------------------------------------------------------------------

def cmd_journal_add(args) -> None:
    tags = parse_tags(args.tags) + extract_hashtags(args.text)
    metrics = parse_metrics(args.metric)
    if args.mood is not None:
        metrics["humeur"] = float(args.mood)
    entry_id = db.add_entry(
        type="journal",
        body=args.text,
        date=parse_date(args.date) or date.today().isoformat(),
        tags=tags or None,
        metrics=metrics or None,
    )
    console.print(f"[green]✓[/green] Entrée de journal #{entry_id} enregistrée.")


def cmd_journal_list(args) -> None:
    entries = db.list_entries(type="journal", tag=args.tag)
    if args.limit:
        entries = entries[-args.limit:]
    display.render_journal(entries)


def cmd_journal_edit(args) -> None:
    entry = db.get_entry(args.id)
    if not entry or entry["type"] != "journal":
        console.print(f"[red]Aucune entrée de journal #{args.id}.[/red]")
        return
    metrics = parse_metrics(args.metric)
    if args.mood is not None:
        metrics["humeur"] = float(args.mood)
    tags = parse_tags(args.tags) if args.tags is not None else None
    db.update_entry(
        args.id,
        body=args.text,
        date=parse_date(args.date) if args.date else None,
        tags=tags,
        metrics=metrics or None,
    )
    console.print(f"[green]✓[/green] Entrée #{args.id} modifiée.")


def cmd_entry_rm(args) -> None:
    db.delete_entry(args.id)
    console.print(f"[red]✗[/red] Entrée #{args.id} supprimée.")


# --------------------------------------------------------------------------
# Commandes : récurrences
# --------------------------------------------------------------------------

def cmd_recur_add(args) -> None:
    tags = parse_tags(args.tags)
    account_id, amount = None, None
    if args.account:
        acc = db.resolve_account(args.account)
        if not acc:
            console.print(f"[red]Compte introuvable : {args.account}[/red]")
            return
        account_id = acc["id"]
        amount = args.amount
        if args.type == "task":
            args.type = "budget"  # un montant implique une récurrence budget
    rid = db.add_recurrence(
        title=args.title,
        freq=args.freq,
        interval=args.interval,
        start=parse_date(args.start),
        until=parse_date(args.until),
        tags=tags or None,
        gen_type=args.type,
        account_id=account_id,
        amount=amount,
    )
    console.print(
        f"[green]✓[/green] Récurrence #{rid} créée "
        f"({args.freq}, tous les {args.interval}). "
        f"Lance [bold]task365 recur run[/bold] pour générer les entrées dues."
    )


def cmd_recur_list(args) -> None:
    display.render_recurrences(db.list_recurrences(active_only=not args.all))


def cmd_recur_run(args) -> None:
    created = db.run_recurrences(until_iso=parse_date(args.until))
    if not created:
        console.print("[dim]Rien à générer : tout est à jour.[/dim]")
        return
    console.print(f"[green]✓[/green] {len(created)} entrée(s) générée(s) :")
    for c in created:
        console.print(f"  [dim]{c['date']}[/dim]  {c['title']}")


def cmd_recur_rm(args) -> None:
    db.delete_recurrence(args.id)
    console.print(f"[red]✗[/red] Récurrence #{args.id} supprimée.")


def cmd_recur_toggle(args) -> None:
    db.set_recurrence_active(args.id, args.active == "on")
    state = "activée" if args.active == "on" else "désactivée"
    console.print(f"[green]✓[/green] Récurrence #{args.id} {state}.")


# --------------------------------------------------------------------------
# Commande : recherche transversale
# --------------------------------------------------------------------------

def cmd_search(args) -> None:
    results = db.search(args.term)
    display.render_search_results(results, args.term)


def cmd_tui(args) -> None:
    from . import tui
    tui.run()


def cmd_gui(args) -> None:
    from . import desktop
    desktop.run()


def cmd_web(args) -> None:
    from . import webview_app
    webview_app.run()


# --------------------------------------------------------------------------
# Commandes : nourriture (saisie directe)
# --------------------------------------------------------------------------

def cmd_food_add(args) -> None:
    eid = db.add_food(
        label=args.label, qty=args.qte,
        kcal=args.kcal, protein=args.prot, carbs=args.gluc,
        fat_sat=args.sat, fat_unsat=args.insat, fiber=args.fibres,
        date=parse_date(args.date), meal=args.meal,
        tags=parse_tags(args.tags) or None,
    )
    console.print(f"[green]✓[/green] Consommation #{eid} enregistrée.")


def cmd_food_day(args) -> None:
    day = parse_date(args.date) or _today_iso()
    logs = db.list_food_log(date=day)
    totals = db.food_day_totals(day)
    display.render_food_day(day, logs, totals)


def cmd_food_edit(args) -> None:
    ok = db.update_food(
        args.id, label=args.label, qty=args.qte,
        kcal=args.kcal, protein=args.prot, carbs=args.gluc,
        fat_sat=args.sat, fat_unsat=args.insat, fiber=args.fibres,
        date=parse_date(args.date) if args.date else None,
        tags=parse_tags(args.tags) if args.tags is not None else None,
    )
    if not ok:
        console.print(f"[red]Aucune consommation #{args.id}.[/red]")
        return
    console.print(f"[green]✓[/green] Consommation #{args.id} modifiée.")


def cmd_food_rm(args) -> None:
    if db.delete_food(args.id):
        console.print(f"[red]✗[/red] Consommation #{args.id} supprimée.")
    else:
        console.print(f"[red]Aucune consommation #{args.id}.[/red]")


def _today_iso() -> str:
    from datetime import date as _date
    return _date.today().isoformat()


# --------------------------------------------------------------------------
# Commandes : sport
# --------------------------------------------------------------------------

def cmd_sport_add(args) -> None:
    sid = db.add_sport(
        activity=args.activity,
        duration_min=args.duration,
        distance_km=args.distance,
        calories=args.calories,
        hr_avg=args.hr,
        effort=args.effort,
        date=parse_date(args.date),
        body=args.note,
        tags=parse_tags(args.tags) or None,
    )
    v = db.get_sport(sid)
    msg = f"[green]✓[/green] Activité #{sid} ({v['activity']}) enregistrée."
    if v["pace"]:
        msg += f" Allure {v['pace']}/km, vitesse {v['speed']} km/h."
    console.print(msg)


def cmd_sport_list(args) -> None:
    acts = db.list_sport(activity=args.activity, since=parse_date(args.since),
                         until=parse_date(args.until), tag=args.tag)
    if args.limit:
        acts = acts[-args.limit:]
    display.render_sport(acts)


def cmd_sport_summary(args) -> None:
    summary = db.sport_summary(since=parse_date(args.since),
                               until=parse_date(args.until))
    display.render_sport_summary(summary)


def cmd_sport_edit(args) -> None:
    ok = db.update_sport(
        args.id, activity=args.activity, duration_min=args.duration,
        distance_km=args.distance, calories=args.calories, hr_avg=args.hr,
        effort=args.effort, date=parse_date(args.date) if args.date else None,
        tags=parse_tags(args.tags) if args.tags is not None else None,
        body=args.note,
    )
    if not ok:
        console.print(f"[red]Aucune activité #{args.id}.[/red]")
        return
    console.print(f"[green]✓[/green] Activité #{args.id} modifiée.")


def cmd_sport_rm(args) -> None:
    if db.delete_sport(args.id):
        console.print(f"[red]✗[/red] Activité #{args.id} supprimée.")
    else:
        console.print(f"[red]Aucune activité #{args.id}.[/red]")


# --------------------------------------------------------------------------
# Commandes : comptes
# --------------------------------------------------------------------------

def cmd_account_add(args) -> None:
    aid = db.add_account(args.name, initial_balance=args.balance,
                         opened_on=parse_date(args.opened))
    console.print(f"[green]✓[/green] Compte #{aid} « {args.name} » créé "
                  f"(solde initial {args.balance:.2f}).")


def cmd_account_list(args) -> None:
    accounts = db.list_accounts()
    balances = {a["id"]: db.balance_at(a["id"], parse_date(args.date))
                for a in accounts}
    display.render_accounts(accounts, balances)


def cmd_account_rm(args) -> None:
    acc = db.resolve_account(args.account)
    if not acc:
        console.print(f"[red]Compte introuvable : {args.account}[/red]")
        return
    db.delete_account(acc["id"])
    console.print(f"[red]✗[/red] Compte « {acc['name']} » et ses opérations supprimés.")


def cmd_account_edit(args) -> None:
    acc = db.resolve_account(args.account)
    if not acc:
        console.print(f"[red]Compte introuvable : {args.account}[/red]")
        return
    db.update_account(acc["id"], name=args.name,
                      initial_balance=args.balance,
                      opened_on=parse_date(args.opened) if args.opened else None)
    console.print(f"[green]✓[/green] Compte #{acc['id']} mis à jour.")


# --------------------------------------------------------------------------
# Commandes : budget
# --------------------------------------------------------------------------

def _need_account(ref) -> dict | None:
    acc = db.resolve_account(ref)
    if not acc:
        console.print(f"[red]Compte introuvable : {ref}[/red]")
        console.print("[dim]Comptes disponibles :[/dim]")
        for a in db.list_accounts():
            console.print(f"  #{a['id']} {a['name']}")
    return acc


def cmd_budget_add(args) -> None:
    acc = _need_account(args.account)
    if not acc:
        return
    amount = args.amount
    if args.expense and amount > 0:
        amount = -amount  # --expense force le signe negatif
    eid = db.add_budget_entry(acc["id"], amount, args.label,
                              date=parse_date(args.date),
                              tags=parse_tags(args.tags) or None)
    new_bal = db.balance_at(acc["id"])
    console.print(f"[green]✓[/green] Opération #{eid} sur « {acc['name'] }». "
                  f"Solde actuel : {new_bal:.2f}.")


def cmd_budget_transfer(args) -> None:
    src = _need_account(args.from_account)
    if not src:
        return
    dst = _need_account(args.to_account)
    if not dst:
        return
    out_id, in_id = db.add_transfer(src["id"], dst["id"], args.amount,
                                    title=args.label, date=parse_date(args.date),
                                    tags=parse_tags(args.tags) or None)
    console.print(
        f"[green]✓[/green] Virement de {abs(args.amount):.2f} : "
        f"« {src['name']} » → « {dst['name']} ».")
    console.print(f"  {src['name']} : {db.balance_at(src['id']):.2f}   "
                  f"{dst['name']} : {db.balance_at(dst['id']):.2f}")


def cmd_budget_list(args) -> None:
    acc = db.resolve_account(args.account) if args.account else None
    ops = db.list_budget_entries(
        account_id=acc["id"] if acc else None,
        since=parse_date(args.since), until=parse_date(args.until),
        tag=args.tag)
    title = f"Opérations — {acc['name']}" if acc else "Opérations (tous comptes)"
    display.render_budget(ops, title)


def cmd_budget_balance(args) -> None:
    acc = _need_account(args.account)
    if not acc:
        return
    as_of = parse_date(args.date)
    bal = db.balance_at(acc["id"], as_of)
    when = as_of or "aujourd'hui"
    console.print(f"Solde de « {acc['name']} » au {when} : "
                  f"[bold]{bal:.2f}[/bold]")
    if args.history:
        series = db.balance_series(acc["id"], since=parse_date(args.since),
                                   until=as_of)
        display.render_balance_series(acc["name"], series)


def cmd_budget_categories(args) -> None:
    acc = db.resolve_account(args.account) if args.account else None
    rows = db.category_breakdown(
        account_id=acc["id"] if acc else None,
        since=parse_date(args.since), until=parse_date(args.until))
    scope = f"— {acc['name']}" if acc else "— tous comptes"
    display.render_category_breakdown(rows, f"Par catégorie {scope}")


def cmd_budget_recalc(args) -> None:
    result = db.recalculate()
    if not result:
        console.print("[dim]Aucun compte.[/dim]")
        return
    console.print("[green]✓[/green] Soldes recalculés :")
    for name, bal in result.items():
        console.print(f"  {name} : [bold]{bal:.2f}[/bold]")


def cmd_budget_edit(args) -> None:
    entry = db.get_budget_entry(args.id)
    if not entry:
        console.print(f"[red]Aucune opération budget #{args.id}.[/red]")
        return
    # cas virement : on ne modifie que montant et/ou date, des deux jambes
    if db.is_transfer(args.id):
        if args.account or args.tags:
            console.print("[yellow]C'est un virement.[/yellow] On ne peut modifier "
                          "que le montant (--amount) et la date (--date) ; le compte "
                          "et les tags ne sont pas modifiables ainsi.")
        if args.amount is None and args.date is None:
            console.print("[dim]Rien à modifier. Précise --amount et/ou --date.[/dim]")
            return
        db.update_transfer(args.id, amount=args.amount,
                           date=parse_date(args.date) if args.date else None)
        console.print(f"[green]✓[/green] Virement #{args.id} mis à jour (deux jambes).")
        return
    # operation simple
    acc_id = None
    if args.account:
        acc = db.resolve_account(args.account)
        if not acc:
            console.print(f"[red]Compte introuvable : {args.account}[/red]")
            return
        acc_id = acc["id"]
    amount = args.amount
    if amount is not None and args.expense and amount > 0:
        amount = -amount
    db.update_budget_entry(
        args.id, amount=amount, title=args.label,
        date=parse_date(args.date) if args.date else None,
        account_id=acc_id,
        tags=parse_tags(args.tags) if args.tags is not None else None,
    )
    console.print(f"[green]✓[/green] Opération #{args.id} modifiée.")


def cmd_budget_rm(args) -> None:
    entry = db.get_budget_entry(args.id)
    if not entry:
        console.print(f"[red]Aucune opération budget #{args.id}.[/red]")
        return
    ok, was_transfer = db.delete_budget_entry(args.id)
    if was_transfer:
        console.print(f"[red]✗[/red] Virement #{args.id} supprimé "
                      f"(les deux jambes, pour garder les soldes justes).")
    else:
        console.print(f"[red]✗[/red] Opération #{args.id} supprimée.")


# --------------------------------------------------------------------------
# Commandes : contacts
# --------------------------------------------------------------------------

def cmd_contact_add(args) -> None:
    tags = parse_tags(args.tags)
    entry_id = db.add_entry(
        type="contact",
        title=args.name,
        body=args.info,
        tags=tags or None,
    )
    console.print(f"[green]✓[/green] Contact #{entry_id} ajouté.")


def cmd_contact_list(args) -> None:
    display.render_contacts(db.list_entries(type="contact", tag=args.tag))


def cmd_contact_note(args) -> None:
    contact = db.get_entry(args.id)
    if not contact or contact["type"] != "contact":
        console.print(f"[red]Aucun contact #{args.id}.[/red]")
        return
    note_id = db.add_entry(
        type="note",
        body=args.text,
        date=date.today().isoformat(),
        parent_id=args.id,
    )
    console.print(f"[green]✓[/green] Note #{note_id} ajoutée à {contact['title']}.")


def cmd_contact_show(args) -> None:
    contact = db.get_entry(args.id)
    if not contact or contact["type"] != "contact":
        console.print(f"[red]Aucun contact #{args.id}.[/red]")
        return
    notes = db.list_entries(type="note", parent_id=args.id)
    display.render_contact_detail(contact, notes)


# --------------------------------------------------------------------------
# Commandes : transverses
# --------------------------------------------------------------------------

def cmd_dashboard(args) -> None:
    # genere d'abord les entrees recurrentes dues, pour qu'elles apparaissent
    db.run_recurrences()
    today = date.today().isoformat()
    horizon = (date.today() + timedelta(days=args.days)).isoformat()
    upcoming = db.list_entries(
        type="task", done=False, since=today, until=horizon, order="date"
    )
    recent_journal = db.list_entries(type="journal")[-args.days:]
    weight = db.metric_history("poids")
    tags = db.all_tags()
    display.render_dashboard(upcoming, recent_journal, weight, tags)


def cmd_tags(args) -> None:
    rows = db.all_tags()
    if not rows:
        console.print("[dim]Aucun tag.[/dim]")
        return
    for name, n in rows:
        console.print(f"  [cyan]#{name}[/cyan]  [dim]({n})[/dim]")


def cmd_metric(args) -> None:
    hist = db.metric_history(args.name)
    if not hist:
        console.print(f"[dim]Aucune donnée pour la métrique « {args.name} ».[/dim]")
        return
    from .display import _sparkline
    vals = [h["value"] for h in hist]
    console.print(f"[bold]{args.name}[/bold]  {_sparkline(vals)}")
    for h in hist[-args.limit:]:
        unit = h.get("unit") or ""
        console.print(f"  [dim]{h['when_'][:10]}[/dim]  [magenta]{h['value']:g}{unit}[/magenta]")


def cmd_export(args) -> None:
    print(db.export_json())


# --------------------------------------------------------------------------
# Parseur
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="task365", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    # task
    task = sub.add_parser("task", help="Gérer les tâches").add_subparsers(dest="sub", required=True)
    t_add = task.add_parser("add", help="Ajouter une tâche")
    t_add.add_argument("title")
    t_add.add_argument("--due", "-d", help="échéance : today, tomorrow, +3, 2026-06-10…")
    t_add.add_argument("--tags", "-t", help="tags séparés par des virgules")
    t_add.add_argument("--metric", "-m", action="append", help="ex: budget=200")
    t_add.set_defaults(func=cmd_task_add)
    t_list = task.add_parser("list", help="Lister les tâches")
    t_list.add_argument("--tag", "-t")
    t_list.add_argument("--done", action="store_true", help="seulement faites")
    t_list.add_argument("--todo", action="store_true", help="seulement à faire")
    t_list.set_defaults(func=cmd_task_list)
    t_done = task.add_parser("done", help="Marquer une tâche comme faite")
    t_done.add_argument("id", type=int)
    t_done.set_defaults(func=cmd_task_done)
    t_edit = task.add_parser("edit", help="Modifier une tâche (date, titre, tags)")
    t_edit.add_argument("id", type=int)
    t_edit.add_argument("--due", "-d", help="nouvelle échéance : today, +3, 2026-06-10…")
    t_edit.add_argument("--title", help="nouveau titre")
    t_edit.add_argument("--tags", "-t", help="REMPLACE les tags")
    t_edit.add_argument("--done", action="store_true", help="marquer faite")
    t_edit.add_argument("--todo", action="store_true", help="marquer à faire")
    t_edit.set_defaults(func=cmd_task_edit)
    t_rm = task.add_parser("rm", help="Supprimer une entrée")
    t_rm.add_argument("id", type=int)
    t_rm.set_defaults(func=cmd_task_rm)

    # journal
    jour = sub.add_parser("journal", help="Journal de bord").add_subparsers(dest="sub", required=True)
    j_add = jour.add_parser("add", help="Ajouter une entrée")
    j_add.add_argument("text")
    j_add.add_argument("--mood", type=float, help="humeur 0-10")
    j_add.add_argument("--date", "-d", help="date de l'entrée (défaut: aujourd'hui)")
    j_add.add_argument("--tags", "-t")
    j_add.add_argument("--metric", "-m", action="append",
                       help="ex: poids=78.5  sommeil=7:h  tension=12")
    j_add.set_defaults(func=cmd_journal_add)
    j_list = jour.add_parser("list", help="Lister les entrées")
    j_list.add_argument("--tag", "-t")
    j_list.add_argument("--limit", "-n", type=int, default=10)
    j_list.set_defaults(func=cmd_journal_list)
    j_edit = jour.add_parser("edit", help="Modifier une entrée de journal")
    j_edit.add_argument("id", type=int)
    j_edit.add_argument("--text", help="nouveau texte")
    j_edit.add_argument("--mood", type=float, help="nouvelle humeur 0-10")
    j_edit.add_argument("--date", "-d", help="nouvelle date")
    j_edit.add_argument("--tags", "-t", help="REMPLACE les tags")
    j_edit.add_argument("--metric", "-m", action="append",
                        help="ajoute/maj une métrique, ex: poids=77.8")
    j_edit.set_defaults(func=cmd_journal_edit)
    j_rm = jour.add_parser("rm", help="Supprimer une entrée de journal")
    j_rm.add_argument("id", type=int)
    j_rm.set_defaults(func=cmd_entry_rm)

    # contact
    cont = sub.add_parser("contact", help="Carnet de contacts").add_subparsers(dest="sub", required=True)
    c_add = cont.add_parser("add", help="Ajouter un contact")
    c_add.add_argument("name")
    c_add.add_argument("--info", "-i", help="infos libres")
    c_add.add_argument("--tags", "-t")
    c_add.set_defaults(func=cmd_contact_add)
    c_list = cont.add_parser("list", help="Lister les contacts")
    c_list.add_argument("--tag", "-t")
    c_list.set_defaults(func=cmd_contact_list)
    c_note = cont.add_parser("note", help="Ajouter une note à un contact")
    c_note.add_argument("id", type=int)
    c_note.add_argument("text")
    c_note.set_defaults(func=cmd_contact_note)
    c_show = cont.add_parser("show", help="Afficher un contact et ses notes")
    c_show.add_argument("id", type=int)
    c_show.set_defaults(func=cmd_contact_show)

    # récurrences
    recur = sub.add_parser("recur", help="Récurrences (génération auto d'entrées)").add_subparsers(dest="sub", required=True)
    r_add = recur.add_parser("add", help="Créer une récurrence")
    r_add.add_argument("title")
    r_add.add_argument("--freq", "-f", required=True,
                       choices=["daily", "weekly", "monthly"], help="fréquence")
    r_add.add_argument("--interval", "-i", type=int, default=1,
                       help="tous les N (défaut 1)")
    r_add.add_argument("--start", "-s", help="date de début (défaut: aujourd'hui)")
    r_add.add_argument("--until", "-u", help="date de fin optionnelle")
    r_add.add_argument("--tags", "-t")
    r_add.add_argument("--type", default="task",
                       help="type d'entrée à générer (défaut: task)")
    r_add.add_argument("--account", help="compte (pour une récurrence budget)")
    r_add.add_argument("--amount", type=float,
                       help="montant signé (négatif=dépense) si récurrence budget")
    r_add.set_defaults(func=cmd_recur_add)
    r_list = recur.add_parser("list", help="Lister les récurrences")
    r_list.add_argument("--all", "-a", action="store_true",
                        help="inclure les désactivées")
    r_list.set_defaults(func=cmd_recur_list)
    r_run = recur.add_parser("run", help="Générer les entrées dues")
    r_run.add_argument("--until", "-u", help="générer jusqu'à cette date")
    r_run.set_defaults(func=cmd_recur_run)
    r_rm = recur.add_parser("rm", help="Supprimer une récurrence")
    r_rm.add_argument("id", type=int)
    r_rm.set_defaults(func=cmd_recur_rm)
    r_tog = recur.add_parser("toggle", help="Activer/désactiver une récurrence")
    r_tog.add_argument("id", type=int)
    r_tog.add_argument("active", choices=["on", "off"])
    r_tog.set_defaults(func=cmd_recur_toggle)

    # recherche
    srch = sub.add_parser("search", help="Rechercher partout (texte, tag, date, métrique)")
    srch.add_argument("term", help="terme, #tag, date ou nom de métrique")
    srch.set_defaults(func=cmd_search)

    # comptes
    acct = sub.add_parser("account", help="Comptes bancaires").add_subparsers(dest="sub", required=True)
    a_add = acct.add_parser("add", help="Créer un compte")
    a_add.add_argument("name")
    a_add.add_argument("--balance", "-b", type=float, default=0.0,
                       help="solde initial")
    a_add.add_argument("--opened", "-o", help="date du solde initial (défaut: aujourd'hui)")
    a_add.set_defaults(func=cmd_account_add)
    a_list = acct.add_parser("list", help="Lister les comptes et soldes")
    a_list.add_argument("--date", "-d", help="soldes à cette date (défaut: aujourd'hui)")
    a_list.set_defaults(func=cmd_account_list)
    a_edit = acct.add_parser("edit", help="Modifier un compte")
    a_edit.add_argument("account", help="id ou nom du compte")
    a_edit.add_argument("--name")
    a_edit.add_argument("--balance", "-b", type=float)
    a_edit.add_argument("--opened", "-o")
    a_edit.set_defaults(func=cmd_account_edit)
    a_rm = acct.add_parser("rm", help="Supprimer un compte (et ses opérations)")
    a_rm.add_argument("account", help="id ou nom du compte")
    a_rm.set_defaults(func=cmd_account_rm)

    # budget
    bud = sub.add_parser("budget", help="Opérations, soldes, catégories").add_subparsers(dest="sub", required=True)
    b_add = bud.add_parser("add", help="Ajouter une opération (montant négatif = dépense)")
    b_add.add_argument("account", help="id ou nom du compte")
    b_add.add_argument("amount", type=float, help="montant signé (-45.50 = dépense)")
    b_add.add_argument("label", help="libellé de l'opération")
    b_add.add_argument("--date", "-d", help="date (défaut: aujourd'hui)")
    b_add.add_argument("--tags", "-t", help="catégorie(s), ex: alimentation")
    b_add.add_argument("--expense", "-e", action="store_true",
                       help="force le montant en dépense (négatif)")
    b_add.set_defaults(func=cmd_budget_add)
    b_tr = bud.add_parser("transfer", help="Virement entre deux comptes")
    b_tr.add_argument("from_account", help="compte source (id ou nom)")
    b_tr.add_argument("to_account", help="compte destination (id ou nom)")
    b_tr.add_argument("amount", type=float, help="montant transféré (positif)")
    b_tr.add_argument("--label", "-l", help="libellé du virement")
    b_tr.add_argument("--date", "-d")
    b_tr.add_argument("--tags", "-t")
    b_tr.set_defaults(func=cmd_budget_transfer)
    b_list = bud.add_parser("list", help="Lister les opérations")
    b_list.add_argument("--account", "-a", help="filtrer par compte")
    b_list.add_argument("--since", "-s", help="depuis cette date")
    b_list.add_argument("--until", "-u", help="jusqu'à cette date")
    b_list.add_argument("--tag", "-t", help="filtrer par catégorie")
    b_list.set_defaults(func=cmd_budget_list)
    b_bal = bud.add_parser("balance", help="Solde d'un compte à une date")
    b_bal.add_argument("account", help="id ou nom du compte")
    b_bal.add_argument("--date", "-d", help="date du solde (défaut: aujourd'hui)")
    b_bal.add_argument("--history", "-H", action="store_true",
                       help="afficher aussi l'historique des soldes")
    b_bal.add_argument("--since", "-s", help="début de l'historique")
    b_bal.set_defaults(func=cmd_budget_balance)
    b_cat = bud.add_parser("categories", help="Répartition par catégorie")
    b_cat.add_argument("--account", "-a")
    b_cat.add_argument("--since", "-s")
    b_cat.add_argument("--until", "-u")
    b_cat.set_defaults(func=cmd_budget_categories)
    b_rec = bud.add_parser("recalc", help="Recalculer les soldes de tous les comptes")
    b_rec.set_defaults(func=cmd_budget_recalc)
    b_edit = bud.add_parser("edit", help="Modifier une opération")
    b_edit.add_argument("id", type=int)
    b_edit.add_argument("--amount", "-m", type=float, help="nouveau montant signé")
    b_edit.add_argument("--label", "-l", help="nouveau libellé")
    b_edit.add_argument("--date", "-d", help="nouvelle date")
    b_edit.add_argument("--account", "-a", help="nouveau compte (op. simple)")
    b_edit.add_argument("--tags", "-t", help="REMPLACE les catégories (op. simple)")
    b_edit.add_argument("--expense", "-e", action="store_true",
                        help="force le montant en dépense")
    b_edit.set_defaults(func=cmd_budget_edit)
    b_rm = bud.add_parser("rm", help="Supprimer une opération (les 2 jambes si virement)")
    b_rm.add_argument("id", type=int)
    b_rm.set_defaults(func=cmd_budget_rm)

    # sport
    sport = sub.add_parser("sport", help="Activités sportives").add_subparsers(dest="sub", required=True)
    s_add = sport.add_parser("add", help="Enregistrer une activité")
    s_add.add_argument("activity", help="course, marche, velo, musculation, natation…")
    s_add.add_argument("--duration", "-D", type=float, help="durée en minutes")
    s_add.add_argument("--distance", "-k", type=float, help="distance en km")
    s_add.add_argument("--calories", "-c", type=float, help="calories brûlées")
    s_add.add_argument("--hr", type=float, help="fréquence cardiaque moyenne (bpm)")
    s_add.add_argument("--effort", "-e", type=float, help="ressenti d'effort 1-10")
    s_add.add_argument("--date", "-d", help="date (défaut: aujourd'hui)")
    s_add.add_argument("--note", "-n", help="note libre")
    s_add.add_argument("--tags", "-t")
    s_add.set_defaults(func=cmd_sport_add)
    s_list = sport.add_parser("list", help="Lister les activités")
    s_list.add_argument("--activity", "-A", help="filtrer par type")
    s_list.add_argument("--since", "-s")
    s_list.add_argument("--until", "-u")
    s_list.add_argument("--tag", "-t")
    s_list.add_argument("--limit", "-N", type=int, default=20)
    s_list.set_defaults(func=cmd_sport_list)
    s_sum = sport.add_parser("summary", help="Bilan par type d'activité")
    s_sum.add_argument("--since", "-s")
    s_sum.add_argument("--until", "-u")
    s_sum.set_defaults(func=cmd_sport_summary)
    s_edit = sport.add_parser("edit", help="Modifier une activité")
    s_edit.add_argument("id", type=int)
    s_edit.add_argument("--activity", "-A")
    s_edit.add_argument("--duration", "-D", type=float)
    s_edit.add_argument("--distance", "-k", type=float)
    s_edit.add_argument("--calories", "-c", type=float)
    s_edit.add_argument("--hr", type=float)
    s_edit.add_argument("--effort", "-e", type=float)
    s_edit.add_argument("--date", "-d")
    s_edit.add_argument("--note", "-n")
    s_edit.add_argument("--tags", "-t")
    s_edit.set_defaults(func=cmd_sport_edit)
    s_rm = sport.add_parser("rm", help="Supprimer une activité")
    s_rm.add_argument("id", type=int)
    s_rm.set_defaults(func=cmd_sport_rm)

    # nourriture (saisie directe)
    food = sub.add_parser("food", help="Nutrition : saisie directe et bilan du jour").add_subparsers(dest="sub", required=True)
    f_add = food.add_parser("add", help="Enregistrer une consommation (valeurs déjà totalisées)")
    f_add.add_argument("label", nargs="?", help="nom de l'aliment (optionnel)")
    f_add.add_argument("--qte", "-q", help="quantité descriptive, ex: '150 g', '1 bol' (non calculée)")
    f_add.add_argument("--kcal", type=float, help="calories")
    f_add.add_argument("--prot", type=float, help="protéines (g)")
    f_add.add_argument("--gluc", type=float, help="glucides (g)")
    f_add.add_argument("--sat", type=float, help="lipides saturés (g)")
    f_add.add_argument("--insat", type=float, help="lipides insaturés (g)")
    f_add.add_argument("--fibres", type=float, help="fibres (g)")
    f_add.add_argument("--date", "-d", help="date (défaut: aujourd'hui)")
    f_add.add_argument("--meal", "-M", help="repas: petit-dej, midi, soir, collation")
    f_add.add_argument("--tags", "-t")
    f_add.set_defaults(func=cmd_food_add)
    f_day = food.add_parser("day", help="Bilan nutritionnel d'une journée")
    f_day.add_argument("date", nargs="?", help="date (défaut: aujourd'hui)")
    f_day.set_defaults(func=cmd_food_day)
    f_edit = food.add_parser("edit", help="Modifier une consommation")
    f_edit.add_argument("id", type=int)
    f_edit.add_argument("--label", "-l")
    f_edit.add_argument("--qte", "-q")
    f_edit.add_argument("--kcal", type=float)
    f_edit.add_argument("--prot", type=float)
    f_edit.add_argument("--gluc", type=float)
    f_edit.add_argument("--sat", type=float)
    f_edit.add_argument("--insat", type=float)
    f_edit.add_argument("--fibres", type=float)
    f_edit.add_argument("--date", "-d")
    f_edit.add_argument("--tags", "-t")
    f_edit.set_defaults(func=cmd_food_edit)
    f_rm = food.add_parser("rm", help="Supprimer une consommation")
    f_rm.add_argument("id", type=int)
    f_rm.set_defaults(func=cmd_food_rm)

    # interface interactive
    tui_p = sub.add_parser("tui", help="Interface interactive (calendrier + détails)")
    tui_p.set_defaults(func=cmd_tui)

    # interface desktop graphique
    gui_p = sub.add_parser("gui", help="Interface desktop (DearPyGui)")
    gui_p.set_defaults(func=cmd_gui)

    # interface desktop web (pywebview)
    web_p = sub.add_parser("web", help="Interface desktop web (pywebview, HTML/CSS)")
    web_p.set_defaults(func=cmd_web)

    # transverses
    dash = sub.add_parser("dashboard", help="Tableau de bord")
    dash.add_argument("--days", "-d", type=int, default=7, help="horizon en jours")
    dash.set_defaults(func=cmd_dashboard)

    tags = sub.add_parser("tags", help="Lister tous les tags")
    tags.set_defaults(func=cmd_tags)

    met = sub.add_parser("metric", help="Historique d'une métrique")
    met.add_argument("name", help="ex: poids, humeur, sommeil")
    met.add_argument("--limit", "-n", type=int, default=15)
    met.set_defaults(func=cmd_metric)

    exp = sub.add_parser("export", help="Exporter toute la base en JSON")
    exp.set_defaults(func=cmd_export)

    return p


def main(argv: list[str] | None = None) -> int:
    db.init_db()
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
