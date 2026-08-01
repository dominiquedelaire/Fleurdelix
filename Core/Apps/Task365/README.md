# Task365

**Auteur :** Dominique Delaire   
**Date de création initiale :** 30 juin 2025   
  

**Assistant personnel local et hors-ligne** : tâches, journal de bord, budget
multi-comptes, contacts, et un module pour travailleurs autonomes avec calcul de
taxes. Tout est stocké dans une base SQLite sur votre machine — **aucune donnée
ne quitte votre ordinateur**.

Task365 propose plusieurs interfaces qui partagent exactement la même logique et
la même base de données :

- **`task365 web`** — interface graphique de bureau dans une fenêtre (recommandée) ;
- **`task365`** — interface en ligne de commande (terminal) ;
- **`task365 tui`** — interface interactive dans le terminal ;
- **`task365 gui`** — interface graphique alternative (DearPyGui).

---

## Fonctionnalités

- **Jour** — vue quotidienne avec tâches, journal, sport et alimentation.
- **Tâches** — avec drapeau *prioritaire* (les prioritaires remontent, les tâches
  faites descendent en bas), tags, et navigation jour par jour.
- **Récurrences** — de tâches **ou** d'opérations de budget (loyer, salaire…),
  quotidiennes / hebdomadaires / mensuelles, avec génération à l'avance jusqu'à
  une date choisie.
- **Récapitulatif année** — graphe d'activité facon « contributions », plus des
  courbes de suivi du **poids** et du **sommeil**.
- **Budget personnel** — comptes multiples, opérations, virements, soldes à une
  date donnée, et répartition par catégorie avec total net (revenus − dépenses).
- **Contacts et notes** — carnet simple relié par tags.
- **Module Travailleur autonome** :
  - saisie de **revenus et dépenses** avec tiers (client / fournisseur),
  - **calcul des taxes** bidirectionnel (HT ⇄ TTC), codes de taxe configurables
    (Québec TPS/TVQ par défaut),
  - distinction **compte perso / entreprise**,
  - récapitulatif des **taxes perçues vs payées** et du **net à remettre**,
  - **duplication** d'une opération pour une saisie rapide,
  - **export** en Excel (`.xlsx`) ou CSV.

Toutes les données sont reliées par des **tags** transversaux.

---

## Installation

Task365 requiert **Python 3.10 ou plus**. La méthode recommandée est
[`pipx`](https://pipx.pypa.io/), qui installe l'application dans un
environnement isolé tout en rendant la commande `task365` disponible partout.

### Installation de base (terminal + TUI)

```bash
pipx install .
```

### Avec l'interface de bureau (recommandé)

L'interface `task365 web` nécessite des dépendances supplémentaires (fenêtre
native via Qt). Installez-les avec l'extra `web` :

```bash
pipx install ".[web]"
```

### Avec l'export Excel

L'export `.xlsx` nécessite `openpyxl` (l'export CSV, lui, ne demande rien) :

```bash
pipx install ".[web,export]"
```

### Tout installer

```bash
pipx install ".[all]"
```

> **Note pipx** : si vous avez déjà installé Task365 et souhaitez ajouter une
> dépendance après coup, vous pouvez aussi faire par exemple :
> `pipx inject task365 pywebview qtpy pyside6 openpyxl`

### Alternative : environnement virtuel classique

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -e ".[web,export]"
```

---

## Utilisation

Une fois installé, lancez l'interface de bureau :

```bash
task365 web
```

Ou l'interface terminal :

```bash
task365 task add "Appeler le notaire" --due tomorrow --tags admin
task365 task list
task365 dashboard
```

Lancez `task365 --help` pour la liste complète des commandes.

---

## Où sont stockées les données ?

Toutes vos données vivent dans une base SQLite unique, en local :

```
~/.task365/task365.db
```

Rien n'est envoyé sur Internet. Pour **sauvegarder** ou **transférer** vos
données, il suffit de copier ce fichier. Pour **repartir de zéro**, supprimez-le
(il sera recréé au prochain lancement).

> **Migration depuis une ancienne version** : si une base issue d'une version
> précédente existe (`~/.shellbots/shellbots.db`), Task365 la reprend
> automatiquement au premier lancement, sans perte de données.

---

## Arborescence du dépôt

```
task365/
├── task365/                 # le package Python
│   ├── __init__.py
│   ├── __main__.py          # permet « python -m task365 »
│   ├── cli.py               # interface ligne de commande + routage des sous-interfaces
│   ├── db.py                # TOUTE la logique métier + accès SQLite (source unique de vérité)
│   ├── display.py           # rendu terminal (Rich)
│   ├── tui.py               # interface interactive terminal (Textual)
│   ├── desktop.py           # interface bureau alternative (DearPyGui)
│   ├── webview_app.py       # interface bureau principale (fenêtre web) + HTML/CSS/JS embarqués
│   └── utils.py             # utilitaires (dates, tags…)
├── pyproject.toml           # métadonnées, dépendances, extras (web/export/gui/all)
├── README.md
├── LICENSE                  # MIT
└── .gitignore
```

**Principe de conception** : toute la logique métier est centralisée dans
`db.py`. Les interfaces (CLI, TUI, DearPyGui, fenêtre web) ne font qu'appeler ces
mêmes fonctions — aucune duplication de logique. C'est ce qui permet d'ajouter
une interface (par exemple un serveur web pour y accéder depuis une tablette)
sans réécrire le cœur.

---

## Contribuer

Les contributions sont bienvenues. Le point d'entrée pour comprendre le projet
est `db.py` (le modèle de données et toutes les opérations). Chaque interface est
une couche mince au-dessus.

---

## Licence

Distribué sous licence **MIT**. Voir le fichier [LICENSE](LICENSE).
